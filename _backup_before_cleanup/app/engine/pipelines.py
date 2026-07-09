from typing import TypedDict, List
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.graph import StateGraph, START, END

from app.engine.generation.llm import get_llm
from app.engine.retrieval.retriever import retrieve_context

class AgentState(TypedDict):
    question: str
    context: str
    sources: List[str]
    response: str

def create_rag_graph(db: AsyncSession):
    """
    Build and compile a LangGraph workflow representing the local RAG pipeline.
    """
    
    async def retrieve_node(state: AgentState):
        """
        Retrieval node: Queries Postgres vector DB using query embedding.
        """
        question = state["question"]
        context, sources = await retrieve_context(question, db, limit=5)
        return {
            "context": context,
            "sources": sources
        }

    async def generate_node(state: AgentState):
        """
        Generation node: Sends context + question to local Ollama.
        """
        llm = get_llm()
        context = state.get("context", "")
        question = state["question"]
        
        prompt = (
            "You are a professional financial assistant. Answer the user's question using the provided context.\n"
            "If the context does not contain the answer, politely state that you do not have sufficient information in the loaded documents to answer.\n"
            "Keep the output professional, detailed, and clear.\n\n"
            f"--- CONTEXT ---\n{context}\n\n"
            f"--- QUESTION ---\n{question}\n\n"
            "Answer:"
        )
        
        response = await llm.ainvoke(prompt)
        return {
            "response": response.content
        }

    # Define StateGraph
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_node)
    
    # Add Edges
    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    
    return workflow.compile()
