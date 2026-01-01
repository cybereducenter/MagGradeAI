"""Feedback Graph V2: Orchestrates Micro-Agents for code feedback."""

from typing import Dict, List, TypedDict, Any
from langgraph.graph import START, END, StateGraph
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from .feedback_agents.state import FeedbackState
from .feedback_agents.schemas import AgentOutput, AgentInput
from .feedback_agents.aggregator import aggregate_feedback
from .feedback_agents.validators.structure_validator import StructureValidator

# Agents
from .feedback_agents.agents.flow_structure import FlowStructureAgent
from .feedback_agents.agents.function_division import FunctionDivisionAgent
from .feedback_agents.agents.programming_errors import ProgrammingErrorsAgent
from .feedback_agents.agents.conventions import ConventionsAgent
from .feedback_agents.agents.debug_tasks import DebugTasksAgent

# Initialize Agents
agents = [
    FlowStructureAgent(),
    FunctionDivisionAgent(),
    ProgrammingErrorsAgent(),
    ConventionsAgent(),
    DebugTasksAgent()
]
validator = StructureValidator()

def make_agent_node(agent):
    """Factory to create a graph node for an agent."""
    def node_func(state: FeedbackState):
        inp = {
            "code": state["code"], 
            "exercise_description": state["exercise_description"],
            "previous_feedback": [], # simplified for now
            "metadata": {}
        }
        agent_input = AgentInput(**inp)
        
        output = agent.invoke(agent_input)
        return {"results": output}
    return node_func

def route_to_agents(state: FeedbackState):
    """Determine which agents to run based on the rubric configuration."""
    config = state.get("rubric_config", {})
    exercise_type = config.get("type", "regular")
    
    # Map subtopic IDs to agent node names
    # Note: rubric uses IDs like 'flow_structure', we map to 'agent_flow_&_structure_agent' -> sanitized
    # Let's verify the node naming convention used below:
    # node_name = f"agent_{agent.name.replace(' ', '_').lower()}"
    # Flow & Structure Agent -> agent_flow_&_structure_agent
    
    # It allows returning a list of nodes to run in parallel
    next_nodes = []
    
    if exercise_type == 'debug':
        # Debug exercises only need the DebugTasksAgent
        next_nodes.append("agent_debug_tasks_agent")
        
    else:
        # Regular exercises: look at subtopics
        subtopics = config.get("subtopics", [])
        
        # Mapping from rubric subtopic ID to agent node name
        # We need to ensure we match the keys in rubric.yaml
        topic_map = {
            "flow_structure": "agent_flow_&_structure_agent",
            "function_decomposition": "agent_function_division_agent",
            "programming_errors": "agent_programming_errors_agent",
            "conventions_docs": "agent_conventions_&_documentation_agent"
        }
        
        for sub in subtopics:
            sid = sub.get("id")
            if sid in topic_map:
                next_nodes.append(topic_map[sid])
                
    # Fallback: if no nodes selected (e.g. config missing), run all or fail safe?
    # For now, if empty, go straight to aggregator (effectively Check-Fail)
    if not next_nodes:
        return "aggregator"
        
    return next_nodes

def build_feedback_graph() -> StateGraph:
    workflow = StateGraph(FeedbackState)
    
    # Register all agent nodes
    for agent in agents:
        node_name = f"agent_{agent.name.replace(' ', '_').lower()}"
        workflow.add_node(node_name, make_agent_node(agent))
        # All agents go to aggregator after finishing
        workflow.add_edge(node_name, "aggregator")
        
    workflow.add_node("aggregator", aggregate_feedback)
    
    # Conditional start
    # We need to list all possible destinations for the conditional edge
    destinations = [
       f"agent_{agent.name.replace(' ', '_').lower()}" for agent in agents
    ] + ["aggregator"]
    
    workflow.add_conditional_edges(
        START,
        route_to_agents,
        destinations
    )
    
    workflow.add_edge("aggregator", END)
    
    return workflow

feedback_graph = build_feedback_graph().compile()

__all__ = ["feedback_graph", "build_feedback_graph"]

