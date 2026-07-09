from langgraph.graph import StateGraph, START, END
from graph.state import TarkaState
from agents.orchestrator import orchestrator_node
from agents.web_scout import web_scout_node
from agents.paper_scout_open_alex import paper_scout_node
from agents.critic import critic_node  
from agents.critic import critic_node_split  
from agents.critic_twopass import critic_two_pass_node
from agents.synthesizer import synthesizer_node

def route_after_orchestrator(state: TarkaState) -> str:
    if state.get("needs_fetch"):
        return "web_scout"
    return "critic"  # Skip scouts, but still analyze the data!

def build_graph():
    builder = StateGraph(TarkaState)
    
    # 1. Register nodes
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("web_scout", web_scout_node)
    builder.add_node("paper_scout", paper_scout_node)
    builder.add_node("critic", critic_two_pass_node)
    builder.add_node("synthesizer", synthesizer_node)
    
    # 2. Control Edges
    builder.add_edge(START, "orchestrator")
    
    builder.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "web_scout": "web_scout",
            "critic": "critic"
        }
    )
    
    # 3. Sequential Data Pipeline
    builder.add_edge("web_scout", "paper_scout")
    builder.add_edge("paper_scout", "critic")
    builder.add_edge("critic", "synthesizer")
    builder.add_edge("synthesizer", END)

    return builder.compile()