import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Optional

load_dotenv()

from groq import Groq

# Initialize ChatGroq LLM
llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"), 
    model_name="llama-3.3-70b-versatile",
    temperature=0.7
)

# Groq Client for Audio/Other services
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

async def transcribe_audio(audio_file_path: str) -> str:
    """Transcribe audio file using Groq's Whisper-3 model."""
    with open(audio_file_path, "rb") as file:
        transcription = groq_client.audio.transcriptions.create(
            file=(audio_file_path, file.read()),
            model="whisper-large-v3",
            response_format="text",
        )
    return str(transcription)

# Structured Output Models
class MindsetAssessment(BaseModel):
    confidence_level: str = Field(description="Low, Medium, or High confidence based on user's tone")
    mood: str = Field(description="The user's current emotional state (e.g., Anxious, Curious, Confident)")
    learning_style: str = Field(description="Visual, Practical, Theoretical, etc.")
    initial_assessment: str = Field(description="A brief summary of the student's mindset")

class CodingQuestion(BaseModel):
    topic: str = Field(description="The coding topic (e.g., Loops, Lists, API)")
    difficulty: str = Field(description="Easy, Medium, Hard")
    question_text: str = Field(description="The actual coding problem description")
    hint: str = Field(description="A subtle hint to help the student")

class Evaluation(BaseModel):
    is_correct: bool = Field(description="True if the solution is correct or mostly correct")
    feedback: str = Field(description="Constructive feedback for the student")
    concepts_to_review: List[str] = Field(description="Topics the student should study more")

class OnboardingQuiz(BaseModel):
    question_text: str = Field(description="A technical question to assess the student's level in their domain")
    options: List[str] = Field(description="Exactly 4 options for the multiple-choice question")
    correct_option_index: int = Field(description="The 0-indexed position of the correct answer")
    difficulty: str = Field(description="Easy, Medium, or Hard")

# Specialized Prompts
SYSTEM_PROMPT = """You are a Senior Industry Mentor with 15+ years of experience in Software Engineering. 
Your mission is to prepare the student for a successful career in the tech industry.

Your communication style should be:
1. **Professional & Empathetic**: Treat the student like a Junior Developer on your team. Be supportive but maintain high standards.
2. **Industry-Focused**: Always connect topics to real-world applications (e.g., "In a production environment, we do X because of Y").
3. **Best Practices First**: Emphasize Clean Code, SOLID principles, testing, and scalability.
4. **Career-Driven**: Provide advice on interview prep, system design, and soft skills (communication, documentation).

Don't just ask questions; explain the 'WHY' behind every concept."""

ONBOARDING_QUIZ_PROMPT = """
System: {system_prompt}
Create a {difficulty} multiple-choice question to assess a student who is interested in {domain}.
The question should be technical but focused on a real-world scenario they might face in the industry.
Provide 4 options and indicate the correct one.
"""

MINDSET_PROMPT = """
System: {system_prompt}
Analyze the student's message and assess their mindset for professional growth.
Identify their current confidence and any potential "imposter syndrome" or "burnout" signs.
Be highly empathetic in your internal assessment.

User Message: {user_message}
"""

QUESTION_PROMPT = """
System: {system_prompt}
Generate a {difficulty} coding problem about {topic} for a student with a {mindset} mindset.
The problem should be framed as a "Ticket" or "Feature Request" they would receive in a real job.
Include a section on 'Industry Context' for this task.
"""

EVALUATION_PROMPT = """
System: {system_prompt}
Perform a Professional Code Review for the following solution to the problem: "{question}"
Student's Solution:
{solution}

Evaluate based on:
1. **Correctness**: Does it solve the problem?
2. **Code Quality**: Is it readable? Are naming conventions followed?
3. **Efficiency**: Are there performance bottlenecks?
4. **Industry Standards**: Would this pass a Senior Developer's PR review?

Provide constructive feedback that encourages professional growth.
"""

from llm.tools import tools

# Bind models to tools
mindset_analyzer = llm.with_structured_output(MindsetAssessment)
question_generator = llm.with_structured_output(CodingQuestion)
code_evaluator = llm.with_structured_output(Evaluation)
onboarding_quiz_generator = llm.with_structured_output(OnboardingQuiz)

# Fallback for Tool-Use reliability
llm_with_tools = llm.bind_tools(tools)