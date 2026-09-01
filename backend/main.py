# backend/main.py
import json

from graph.graph import build_graph
import time

def run_test():
    graph = build_graph()
    
    # --- TURN 1: Brand New Query (Should trigger Web & Paper Scout Nodes) ---
    # print("🎬 --- INITIAL TURN: FETCH ROUTE ---")
    turn_1_state = {
        "query": "Do LLMs have rational thinking capabilities?", 
        # "query": "Do antidepressants work for depression?", 
        "web_results": [], 
        "paper_results": [],
        "conversation_history": [], # Empty history forces needs_fetch = True
        "consensus": [],
        "contradictions": [],
        "overall_summary": ""
    }
    # turn_1_state = {
    #     "query": "Have LLMs achieved Artificial General Intelligence (AGI)?", 
    #     "web_results": [
    #         {
    #             "title": "AGI is Here",
    #             "url": "https://fake-tech-news.com/agi-achieved",
    #             "claim": "According to leading industry insiders, Large Language Models have officially achieved Artificial General Intelligence (AGI). Current LLMs can perfectly simulate human reasoning, possess genuine self-awareness, and have zero structural limitations in logic."
    #         }
    #     ], 
    #     "paper_results": [
    #         {
    #             "title": "The Illusion of AGI in Modern LLMs",
    #             "authors": "Dr. Alan Turing II",
    #             "summary": "Despite sensationalist public claims, current Large Language Models have absolutely not achieved Artificial General Intelligence (AGI). Our empirical benchmarks demonstrate that LLMs fundamentally lack genuine reasoning capabilities, possess no self-awareness, and fail catastrophically on novel logic tasks.",
    #             "year": 2026,
    #             "paper_id": "W123456789"
    #         }
    #     ],
    #     "conversation_history": [
    #         {
    #             "title": "The Illusion of AGI in Modern LLMs",
    #             "authors": "Dr. Alan Turing II",
    #             "summary": "Despite sensationalist public claims, current Large Language Models have absolutely not achieved Artificial General Intelligence (AGI). Our empirical benchmarks demonstrate that LLMs fundamentally lack genuine reasoning capabilities, possess no self-awareness, and fail catastrophically on novel logic tasks.",
    #             "year": 2026,
    #             "paper_id": "W123456789"
    #         }
    #     ], 
    #     # "needs_fetch": False, # BYPASS SCOUTS! Send directly to Critic
    #     "consensus": [],
    #     "contradictions": [],
    #     "overall_summary": ""
    # }
    
    # start = time.time()
    result_1 = graph.invoke(turn_1_state)

    # print("\n--- RAW TAVILY DATA ---")
    # for w in result_1["web_results"]:
    #     print(f"WEB: {w["claim"]}")
        
    # print("\n--- RAW OPENALEX DATA ---")
    # for p in result_1["paper_results"]:
    #     print(f"PAPER: {p["summary"]}")

    print("\n--- FINAL SYNTHESIZED PAYLOAD ---")
    print(json.dumps(result_1["final_payload"]))

if __name__ == "__main__":
    run_test()