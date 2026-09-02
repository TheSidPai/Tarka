import re
import requests
from graph.state import TarkaState

OPENALEX_URL = "https://api.openalex.org/works"


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
        # doi/venue make the results citable (BibTeX, RIS); cited_by_count is a
        # credibility signal the UI shows next to each paper.
        "select": (
            "title,authorships,abstract_inverted_index,publication_year,id,"
            "doi,cited_by_count,primary_location"
        )
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
                "paper_id": p.get("id", ""),
                # OpenAlex returns the DOI as a full URL; strip to a bare DOI
                # so citation formats can use it directly.
                "doi": (p.get("doi") or "").replace("https://doi.org/", ""),
                "cited_by_count": p.get("cited_by_count", 0),
                "venue": (
                    ((p.get("primary_location") or {}).get("source") or {}).get("display_name", "")
                ),
            }
            # OpenAlex stores the list of works in 'results', not 'data'
            for p in data.get("results", [])
        ]
        return {"paper_results": results}

    except Exception as e:
        print(f"OpenAlex unavailable: {e}")
        return {"paper_results": []}