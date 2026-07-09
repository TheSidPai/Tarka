import re
import requests
from graph.state import TarkaState
import os

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
OPENALEX_URL = "https://api.openalex.org/works"


def clean_web_text(text):
    if not text: return ""
    # 1. Remove excessive whitespace, newlines, and tabs
    clean = re.sub(r'\s+', ' ', text)
    # 2. Strip out common markdown link syntax [Text](URL) keeping only the Text
    clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)
    # 3. Trim down to the first few sentences or a readable limit (e.g., 500 characters)
    return clean[:500].strip() + "..."

def clean_query(query: str) -> str:
    clean = re.sub(r'[^\w\s]', '', query)
    stop_words = {"can", "what", "is", "the", "are", "on", "whether", "how", "do", "does", "why"}
    words = clean.lower().split()
    keywords = [w for w in words if w not in stop_words]
    return " ".join(keywords) if keywords else query

def reconstruct_abstract(inverted_index: dict) -> str:
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join(w for _, w in word_positions)

def paper_scout_node(state: TarkaState) -> dict:
    query = clean_query(state["query"])
    print(query)
    # params = {
    #     "query": query,
    #     "limit": 5,
    #     "fields": "title,authors,abstract,year,paperId"
    # } this is for Semantic Scholar API

    params = {
        "search": query,
        "per-page": 15,
        "select": "title,authorships,abstract_inverted_index,publication_year,id"
    } # this is for OpenAlex API

    try:
        response = requests.get(OPENALEX_URL, params=params, timeout=40)
        response.raise_for_status()
        data = response.json()

        results = [
            {
                "title": p.get("title", ""),
                # OpenAlex nests the name: authorships -> author -> display_name
                "authors": ", ".join(
                    a.get("author", {}).get("display_name", "Unknown") 
                    for a in p.get("authorships", [])
                ),
                "summary": reconstruct_abstract(p.get("abstract_inverted_index", {})),
                "year": p.get("publication_year"),
                "paper_id": p.get("id", "")
            }
            # OpenAlex stores the list of works in 'results', not 'data'
            for p in data.get("results", [])
        ]
        return {"paper_results": results}

    except Exception as e:
        print(f"OpenAlex unavailable: {e}")
        return {"paper_results": []}