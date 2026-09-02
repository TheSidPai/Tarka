# backend/agents/web_scout.py
import os
from dotenv import load_dotenv
from tavily import TavilyClient
from graph.state import TarkaState 

load_dotenv()

tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

def web_scout_node(state: TarkaState) -> dict:
    try:
        # search_depth="fast" returns multiple relevant snippets per URL instead
        # of a single sentence — ~8x the text per source, which is what lets the
        # Critic cross-examine web claims against full paper abstracts. Costs the
        # same 1 credit as "basic"; "advanced" adds ~2% more text for 2 credits.
        # include_raw_content stays off: full page dumps are ~25x this and the
        # noise defeats the point.
        response = tavily_client.search(
            query=state["query"],
            max_results=15,
            search_depth="fast",
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