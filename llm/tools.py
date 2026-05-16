from googlesearch import search as google_search
import wikipedia
from langchain.tools import Tool

def web_search(query: str) -> str:
    """Useful for searching the internet to answer questions about coding topics, 
    latest technologies, or specific error messages using Google."""
    print(f"Google search query: {query}")
    try:
        results = google_search(query, num_results=3, advanced=True)
        formatted_results = []
        for r in results:
            formatted_results.append(f"Title: {r.title}\nSnippet: {r.description}\nSource: {r.url}")
        
        if not formatted_results:
            return "No results found on Google."
            
        output = "\n\n".join(formatted_results)
        print("Google search results successfully retrieved.")
        return output
    except Exception as e:
        print(f"Google search error: {str(e)}")
        return f"Error performing Google search: {str(e)}"

def wikipedia_search(query: str) -> str:
    """Useful for getting detailed background information on technical terms, 
    programming languages, or computer science concepts."""
    print(f"Wikipedia search query: {query}")
    try:
        # Get the most relevant page
        search_results = wikipedia.search(query)
        if not search_results:
            return "No Wikipedia page found for this topic."
            
        page = wikipedia.page(search_results[0], auto_suggest=False)
        summary = page.summary[:1000] # Limit to 1000 chars
        print("Wikipedia summary successfully retrieved.")
        return f"Source: {page.url}\n\nSummary: {summary}"
    except Exception as e:
        print(f"Wikipedia search error: {str(e)}")
        return f"Error performing Wikipedia search: {str(e)}"

# Define the list of tools available to the agent
tools = [
    Tool(
        name="web_search",
        func=web_search,
        description="Search Google for coding help, documentation, and latest technology updates."
    ),
    Tool(
        name="wikipedia_search",
        func=wikipedia_search,
        description="Search Wikipedia for detailed technical concepts and history of technologies."
    )
]

if __name__ == "__main__":
    # Test the search tools
    print("--- Testing Google ---")
    print(web_search("what is python programming"))
    print("\n--- Testing Wikipedia ---")
    print(wikipedia_search("Python (programming language)"))
