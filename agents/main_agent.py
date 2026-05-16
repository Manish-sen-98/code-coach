from llm.llm import (
    mindset_analyzer, 
    question_generator, 
    code_evaluator,
    onboarding_quiz_generator, # Added
    llm_with_tools, 
    MINDSET_PROMPT,
    QUESTION_PROMPT,
    EVALUATION_PROMPT,
    ONBOARDING_QUIZ_PROMPT, # Added
    SYSTEM_PROMPT
)
from llm.tools import tools, web_search, wikipedia_search
from utils.storage import get_user_state, update_user_state, log_interaction
import json
import asyncio

class MentorAgent:
    def __init__(self, user_id):
        self.user_id = str(user_id)
        self.state = get_user_state(self.user_id)
        if not self.state:
            update_user_state(self.user_id)
            self.state = get_user_state(self.user_id)

    async def process_message(self, message: str):
        self.state = get_user_state(self.user_id)
        
        # Check for mode switch keywords
        if "/chat" in message.lower() or "switch to communication" in message.lower():
            update_user_state(self.user_id, current_mode="communication")
            return "🔄 Switched to <b>Communication Mode</b>. Tell me what's on your mind or where you're stuck!"
        
        if "/quiz" in message.lower() or "switch to knowledge" in message.lower():
            update_user_state(self.user_id, current_mode="knowledge")
            return "🔄 Switched to <b>Knowledge Mode</b>. Ready for your next industry task? Let me know the topic!"

        # Onboarding flow
        step = self.state.get("onboarding_step", 0)
        if step < 3: 
            return await self._handle_onboarding(message, step)

        # Handle based on current mode
        current_mode = self.state.get("current_mode", "knowledge")
        
        if current_mode == "communication":
            # In communication mode, we always use the general tool-enabled LLM
            return await self._handle_general_query(message)

        # Knowledge Mode (Original logic)
        if any(keyword in message.lower() for keyword in ["help", "search", "explain", "what is", "how to"]):
            return await self._handle_general_query(message)

        if not self.state.get("mindset"):
            return await self._handle_mindset_check(message)
        
        if not self.state.get("current_topic"):
            return await self._suggest_topics(message)

        history = self.state.get("history", [])
        if history and history[-1].get("status") == "pending":
            return await self._evaluate_solution(message)

        return await self._chat_or_new_question(message)

    async def _handle_onboarding(self, message, step):
        if step == 0:
            # This is the very first interaction after /start
            update_user_state(self.user_id, onboarding_step=1)
            return {
                "text": "Welcome! To personalize your journey, what is your primary domain of interest?",
                "options": ["AI & Machine Learning", "Web Development", "Data Science", "Cybersecurity"]
            }
        
        if step == 1:
            # User selected a domain
            domain = message
            update_user_state(self.user_id, domain=domain, onboarding_step=2)
            
            # Generate a quiz question for this domain
            try:
                quiz = await onboarding_quiz_generator.ainvoke(
                    ONBOARDING_QUIZ_PROMPT.format(system_prompt=SYSTEM_PROMPT, domain=domain, difficulty="Easy")
                )
            except Exception as e:
                print(f"Quiz generation error: {e}")
                # Fallback question if LLM fails to generate structured output
                quiz = type('obj', (object,), {
                    'question_text': f"Since I'm specializing your {domain} path, tell me: What is your favorite tool or library in this field and why?",
                    'options': ["React/Vue", "TensorFlow/PyTorch", "Django/FastAPI", "Other"],
                    'correct_option_index': 0
                })
            
            # Store quiz info in state/history for evaluation
            history = self.state.get("history", [])
            history.append({
                "type": "onboarding_quiz",
                "question": quiz.question_text,
                "options": quiz.options,
                "correct_index": quiz.correct_option_index,
                "status": "pending"
            })
            update_user_state(self.user_id, history=history)
            
            return {
                "text": f"Great choice! Let's see what you know about {domain}.\n\n<b>{quiz.question_text}</b>",
                "options": quiz.options
            }
        
        if step == 2:
            # User answered the quiz
            history = self.state.get("history", [])
            last_quiz = [h for h in history if h.get("type") == "onboarding_quiz"][-1]
            
            selected_option = message
            try:
                selected_index = last_quiz["options"].index(selected_option)
                is_correct = selected_index == last_quiz["correct_index"]
            except ValueError:
                is_correct = False
            
            level = "Intermediate" if is_correct else "Beginner"
            update_user_state(self.user_id, level=level, onboarding_step=3)
            
            response_text = "✅ Correct!" if is_correct else f"❌ Not quite. The correct answer was: {last_quiz['options'][last_quiz['correct_index']]}"
            response_text += f"\n\nI've set your level to <b>{level}</b>. Now, tell me how you're feeling about coding today?"
            
            return response_text

    async def _handle_general_query(self, message: str):
        # Use the tool-enabled LLM
        response = await llm_with_tools.ainvoke(
            [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": message}]
        )
        
        # Tool execution loop
        if response.tool_calls:
            available_tools = {
                "web_search": web_search,
                "wikipedia_search": wikipedia_search
            }
            
            tool_outputs = []
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                if tool_name in available_tools:
                    print(f"Executing tool: {tool_name}")
                    result = available_tools[tool_name](**tool_args)
                    tool_outputs.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result
                    })
            
            if tool_outputs:
                # Get final answer with all tool results
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": None, "tool_calls": response.tool_calls}
                ]
                messages.extend(tool_outputs)
                
                final_response = await llm_with_tools.ainvoke(messages)
                return final_response.content
        
        return response.content

    async def _handle_mindset_check(self, message):
        assessment = await mindset_analyzer.ainvoke(
            MINDSET_PROMPT.format(system_prompt=SYSTEM_PROMPT, user_message=message)
        )
        
        update_user_state(
            self.user_id, 
            mindset=f"{assessment.mood} ({assessment.confidence_level} confidence)",
        )
        
        log_interaction(self.user_id, "mindset_check", assessment.dict())
        
        response = (
            f"I hear you! It sounds like you're approaching this with a <b>{assessment.mood.lower()}</b> mindset. "
            "That's a great starting point for today's session.\n\n"
            "As your mentor, I want to make sure you're not just writing code, but building <i>industry-ready</i> solutions. "
            "What professional domain or specific technology would you like to dive into today? "
            "(e.g., Backend architecture, Data pipeline design, Frontend best practices)"
        )
        return response

    async def _suggest_topics(self, message):
        update_user_state(self.user_id, current_topic=message)
        return await self._generate_question(message)

    async def _generate_question(self, topic):
        self.state = get_user_state(self.user_id)
        difficulty = self.state.get("level", "Beginner")
        
        question = await question_generator.ainvoke(
            QUESTION_PROMPT.format(
                system_prompt=SYSTEM_PROMPT,
                difficulty=difficulty, 
                topic=topic, 
                mindset=self.state['mindset']
            )
        )
        
        # Update history with pending question
        history = self.state.get("history", [])
        history.append({
            "topic": topic,
            "question": question.question_text,
            "status": "pending",
            "timestamp": None
        })
        update_user_state(self.user_id, history=history)
        
        log_interaction(self.user_id, "question_generated", question.dict())
        
        response = (
            f"🏢 <b>Industry Task: {topic}</b>\n\n"
            f"Here is a task you might see in a professional sprint:\n\n"
            f"<b>{question.question_text}</b>\n\n"
            f"💡 <i>Mentor's Advice: {question.hint}</i>\n\n"
            "Submit your code when you're ready for a <b>Professional Code Review</b>!"
        )
        return response

    async def _evaluate_solution(self, solution):
        self.state = get_user_state(self.user_id)
        history = self.state.get("history", [])
        if not history:
            return await self._suggest_topics(solution)
            
        last_q = history[-1]
        
        evaluation = await code_evaluator.ainvoke(
            EVALUATION_PROMPT.format(
                system_prompt=SYSTEM_PROMPT,
                question=last_q['question'],
                solution=solution
            )
        )
        
        # Update history
        last_q["status"] = "solved" if evaluation.is_correct else "failed"
        last_q["feedback"] = evaluation.feedback
        update_user_state(self.user_id, history=history)
        
        log_interaction(self.user_id, "evaluation", evaluation.dict())
        
        status_header = "🚀 <b>PR Approved!</b>" if evaluation.is_correct else "👨‍💻 <b>Revision Required</b>"
        
        response = (
            f"{status_header}\n\n"
            f"<b>Senior Developer Feedback:</b>\n"
            f"{evaluation.feedback}\n\n"
        )
        
        if evaluation.concepts_to_review:
            response += "📚 <b>Recommended Learning for Industry:</b>\n" + \
                        "\n".join([f"- {c}" for c in evaluation.concepts_to_review])
        
        response += "\n\nGreat work. What project topic should we tackle next to further your career?"
        
        # Clear current topic so they can pick a new one
        update_user_state(self.user_id, current_topic=None)
        
        return response

    async def _chat_or_new_question(self, message):
        if "/report" in message.lower():
            return await self.generate_report()
            
        return await self._suggest_topics(message)

    async def generate_report(self):
        self.state = get_user_state(self.user_id)
        history = self.state.get("history", [])
        
        if not history:
            return "We haven't started any tasks yet. Let's get your first industry task assigned!"
            
        solved_count = sum(1 for h in history if h.get("status") == "solved")
        
        report = (
            f"📈 <b>Industry Performance Review</b>\n"
            f"👤 <b>Developer ID:</b> {self.user_id}\n"
            f"🧠 <b>Mindset Assessment:</b> {self.state.get('mindset', 'Not assessed')}\n"
            f"🏅 <b>Career Level:</b> {self.state.get('level', 'Junior Developer')}\n"
            f"✅ <b>Tasks Completed:</b> {solved_count}/{len(history)}\n\n"
            "<b>Professional Log:</b>\n"
        )
        
        for h in history[-3:]: 
            status_emoji = "✅" if h.get("status") == "solved" else "🚧"
            report += f"- {status_emoji} <b>{h.get('topic')}</b>: {h.get('question')[:40]}...\n"
            
        report += "\n<b>Mentor's Summary:</b> You are making progress toward industry standards. Keep focusing on code quality and best practices!"
        return report

    async def reset_state(self):
        update_user_state(self.user_id, mindset="", current_topic="", history=[], domain="", onboarding_step=0)
        return "Your progress has been reset. Let's start fresh! Type anything to begin your onboarding."
