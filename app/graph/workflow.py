from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    analyze_node,
    diff_node,
    extract_node,
    integrate_node,
    reflect_node,
    report_node,
    visualize_node,
    watch_node,
)
from app.graph.state import AgentState


def route_after_diff(state: AgentState) -> str:
    return "extract" if state.get("is_changed") else "reflect"


def build_workflow():
    g = StateGraph(AgentState)

    g.add_node("watch", watch_node)
    g.add_node("diff", diff_node)
    g.add_node("extract", extract_node)
    g.add_node("integrate", integrate_node)
    g.add_node("analyze", analyze_node)
    g.add_node("visualize", visualize_node)
    g.add_node("report", report_node)
    g.add_node("reflect", reflect_node)

    g.add_edge(START, "watch")
    g.add_edge("watch", "diff")
    g.add_conditional_edges("diff", route_after_diff, {"extract": "extract", "reflect": "reflect"})
    g.add_edge("extract", "integrate")
    g.add_edge("integrate", "analyze")
    g.add_edge("analyze", "visualize")
    g.add_edge("visualize", "report")
    g.add_edge("report", "reflect")
    g.add_edge("reflect", END)

    return g.compile()
