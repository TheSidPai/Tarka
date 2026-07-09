import re
import requests
from graph.state import TarkaState
import os

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")

def clean_query(query: str) -> str:
    clean = re.sub(r'[^\w\s]', '', query)
    stop_words = {"can", "what", "is", "the", "are", "on", "whether", "how", "do", "does", "why"}
    words = clean.lower().split()
    keywords = [w for w in words if w not in stop_words]
    return " ".join(keywords) if keywords else query

def paper_scout_node(state: TarkaState) -> dict:
    query = clean_query(state["query"])
    print(query)

    params = {
        "query": query,
        "limit": 10,
        "fields": "title,authors,abstract,year,paperId"
    }

    headers = {"x-api-key": SEMANTIC_SCHOLAR_API_KEY}


    try:
        response = requests.get(SEMANTIC_SCHOLAR_URL, params=params, headers=headers, timeout=40)

        response.raise_for_status()
        data = response.json()

        results = [
            {
                "title": p.get("title", ""),
                "authors": ", ".join(a.get("name", "") for a in p.get("authors", [])),
                "summary": (p.get("abstract") or "")[:500],
                "year": p.get("year"),
                "paper_id": p.get("paperId", "")
            }
            for p in data.get("data", [])
        ]
        return {"paper_results": results}

    except Exception as e:
        print(f"Semantic Scholar unavailable: {e}")
        return {"paper_results": []}
