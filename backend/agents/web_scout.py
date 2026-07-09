# backend/agents/web_scout.py
import os
from dotenv import load_dotenv
from tavily import TavilyClient
from graph.state import TarkaState 

load_dotenv()

tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

def web_scout_node(state: TarkaState) -> dict:
    try:
        response = tavily_client.search(
            query=state["query"],
            max_results=15,
            include_raw_content=False
        )
        results = [
            {
                "url": item.get("url"),
                "title": item.get("title"),
                "claim": item.get("content"),
                "date": item.get("published_date", "Unknown")
            }
            for item in response.get("results", [])
        ]
        return {"web_results": results}
    except Exception as e:
        print(f"Tavily unavailable: {e}")
        return {"web_results": []}