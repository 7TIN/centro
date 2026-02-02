from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage
import operator

# Define state
class AgentState(TypedDict):
    question: str
    conversation_history: list
    context_analysis: dict
    retrieved_docs: list
    draft_response: str
    validation_result: dict
    final_response: str
    metadata: dict

# Initialize LLM
llm = ChatAnthropic(model="claude-sonnet-4-20250514")

# Agent functions
def analyze_context(state: AgentState) -> AgentState:
    """Analyze question intent, urgency, topic"""
    from src.agents.context_analyzer import ContextAnalyzer
    
    analyzer = ContextAnalyzer(llm)
    analysis = analyzer.analyze(
        question=state["question"],
        history=state["conversation_history"]
    )
    
    state["context_analysis"] = analysis
    return state

def retrieve_knowledge(state: AgentState) -> AgentState:
    """Semantic search in vector DB"""
    from src.agents.retrieval_agent import RetrievalAgent
    
    retriever = RetrievalAgent()
    docs = retriever.search(
        query=state["question"],
        filters=state["context_analysis"].get("topics", []),
        top_k=5
    )
    
    state["retrieved_docs"] = docs
    return state

def generate_response(state: AgentState) -> AgentState:
    """Generate response in X's style"""
    from src.agents.response_generator import ResponseGenerator
    
    generator = ResponseGenerator(llm)
    response = generator.generate(
        question=state["question"],
        context=state["retrieved_docs"],
        style=state["metadata"]["person_style"]
    )
    
    state["draft_response"] = response
    return state

def validate_response(state: AgentState) -> AgentState:
    """Check for hallucinations and style"""
    from src.agents.validator import Validator
    
    validator = Validator(llm)
    validation = validator.validate(
        response=state["draft_response"],
        facts=state["retrieved_docs"],
        patterns=state["metadata"]["person_patterns"]
    )
    
    state["validation_result"] = validation
    return state

def should_revise(state: AgentState) -> str:
    """Decide if response needs revision"""
    if not state["validation_result"]["valid"]:
        return "revise"
    if state["validation_result"]["confidence"] < 0.7:
        return "revise"
    return "finalize"

def finalize_response(state: AgentState) -> AgentState:
    """Final response preparation"""
    state["final_response"] = state["draft_response"]
    return state

def revise_response(state: AgentState) -> AgentState:
    """Regenerate with validator feedback"""
    # Re-run generator with issues flagged
    state["metadata"]["revision_notes"] = state["validation_result"]["issues"]
    return generate_response(state)

# Build graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("analyze", analyze_context)
workflow.add_node("retrieve", retrieve_knowledge)
workflow.add_node("generate", generate_response)
workflow.add_node("validate", validate_response)
workflow.add_node("finalize", finalize_response)
workflow.add_node("revise", revise_response)

# Define edges
workflow.set_entry_point("analyze")
workflow.add_edge("analyze", "retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", "validate")

# Conditional routing
workflow.add_conditional_edges(
    "validate",
    should_revise,
    {
        "finalize": "finalize",
        "revise": "revise"
    }
)

workflow.add_edge("revise", "validate")  # Loop back
workflow.add_edge("finalize", END)

# Compile
app = workflow.compile()