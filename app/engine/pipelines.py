import os
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.config import settings
from app.core.logger import logger
from app.engine.generation.llm import get_llm
from app.engine.retrieval.hybrid_retriever import HybridRetriever
from app.engine.retrieval.rank_fusion import FusedResult
from app.engine.retrieval.reranker import CrossEncoderReranker, RerankedResult


class RAGState(TypedDict):
    """
    Typed state representation for the LangGraph RAG orchestration pipeline.
    """

    query: str
    dense_top_k: int
    sparse_top_k: int
    final_top_k: int
    retrieval_results: List[FusedResult]
    reranked_results: List[RerankedResult]
    context: str
    answer: str
    sources: List[Dict[str, Any]]
    error: Optional[str]
    status: str


class RAGPipeline:
    """
    Deterministic LangGraph-based RAG pipeline for financial document question answering.

    Graph Architecture:
        START -> validate_query -> retrieve -> rerank -> build_context -> generate -> validate_grounding -> END
    """

    def __init__(
        self,
        hybrid_retriever: Optional[HybridRetriever] = None,
        reranker: Optional[CrossEncoderReranker] = None,
        llm=None,
    ):
        logger.info("Initializing LangGraph RAGPipeline...")

        self.hybrid_retriever = hybrid_retriever or HybridRetriever()
        self.reranker = reranker or CrossEncoderReranker()
        self.llm = llm or get_llm()

        self.graph = self._build_graph()

        logger.info("RAGPipeline successfully built and compiled.")

    def _build_graph(self):
        """Construct and compile the LangGraph StateGraph."""
        builder = StateGraph(RAGState)

        # Register nodes
        builder.add_node("validate_query", self._node_validate_query)
        builder.add_node("retrieve", self._node_retrieve)
        builder.add_node("rerank", self._node_rerank)
        builder.add_node("build_context", self._node_build_context)
        builder.add_node("generate", self._node_generate)
        builder.add_node("validate_grounding", self._node_validate_grounding)

        # Connect linear sequential edges
        builder.add_edge(START, "validate_query")
        builder.add_edge("validate_query", "retrieve")
        builder.add_edge("retrieve", "rerank")
        builder.add_edge("rerank", "build_context")
        builder.add_edge("build_context", "generate")
        builder.add_edge("generate", "validate_grounding")
        builder.add_edge("validate_grounding", END)

        return builder.compile()

    def _node_validate_query(self, state: RAGState) -> Dict[str, Any]:
        """Node: Validate user search query string."""
        query = state.get("query", "")
        if not query or not query.strip():
            logger.warning("Empty query received in validate_query node.")
            return {
                "error": "Query cannot be empty.",
                "status": "invalid_query",
                "answer": "Please provide a valid financial question.",
                "sources": [],
                "context": "",
            }

        return {
            "status": "query_valid",
            "error": None,
        }

    def _node_retrieve(self, state: RAGState) -> Dict[str, Any]:
        """Node: Execute hybrid (FAISS + BM25 + RRF) candidate retrieval."""
        if state.get("error"):
            return {}

        query = state["query"]
        dense_k = state.get("dense_top_k", settings.TOP_K)
        sparse_k = state.get("sparse_top_k", settings.TOP_K)
        final_k = state.get("final_top_k", settings.TOP_K)

        logger.info(f"LangGraph [retrieve] node running for query: {query!r}")

        results = self.hybrid_retriever.hybrid_search(
            query=query,
            dense_top_k=dense_k,
            sparse_top_k=sparse_k,
            final_top_k=max(dense_k, sparse_k, final_k),
        )

        if not results:
            logger.info("No candidate chunks retrieved by HybridRetriever.")
            return {
                "retrieval_results": [],
                "status": "no_candidates",
            }

        return {
            "retrieval_results": results,
            "status": "retrieved",
        }

    def _node_rerank(self, state: RAGState) -> Dict[str, Any]:
        """Node: Score candidates with Cross-Encoder and sort by precision relevance."""
        if state.get("error"):
            return {}

        candidates = state.get("retrieval_results", [])
        if not candidates:
            return {
                "reranked_results": [],
                "status": "no_candidates_to_rerank",
            }

        query = state["query"]
        final_k = state.get("final_top_k", settings.FINAL_CONTEXT_K)

        logger.info(f"LangGraph [rerank] node reranking {len(candidates)} candidates.")

        reranked = self.reranker.rerank(
            query=query,
            candidates=candidates,
            final_top_k=final_k,
        )

        return {
            "reranked_results": reranked,
            "status": "reranked",
        }

    def _node_build_context(self, state: RAGState) -> Dict[str, Any]:
        """Node: Format reranked chunks into clean structured prompt context and metadata."""
        if state.get("error"):
            return {}

        reranked = state.get("reranked_results", [])
        if not reranked:
            return {
                "context": "",
                "sources": [],
                "status": "no_context",
            }

        context_parts = []
        sources = []

        for r in reranked:
            raw_source = r.document.metadata.get("source", "unknown")
            filename = os.path.basename(raw_source)
            page = r.document.metadata.get("page", 0)
            cid = r.chunk_id

            context_parts.append(
                f"[Source: {filename} | Page: {page} | Chunk ID: {cid}]\n{r.document.page_content}"
            )

            sources.append(
                {
                    "filename": filename,
                    "page": page,
                    "chunk_id": cid,
                    "rerank_score": r.rerank_score,
                    "rrf_score": r.rrf_score,
                    "retrieval_sources": r.retrieval_sources,
                }
            )

        context_str = "\n\n---\n\n".join(context_parts)

        return {
            "context": context_str,
            "sources": sources,
            "status": "context_built",
        }

    def _node_generate(self, state: RAGState) -> Dict[str, Any]:
        """Node: Invoke local Ollama LLM to generate grounded financial answer."""
        if state.get("error"):
            return {}

        context = state.get("context", "")
        if not context:
            logger.info("No context available for generation. Returning fallback answer.")
            return {
                "answer": "The available documents do not contain enough information to answer this question.",
                "status": "no_context_answer",
            }

        query = state["query"]

        prompt = (
            "You are a financial analyst AI assistant analyzing documents.\n"
            "Answer the following question using ONLY the provided financial document context.\n\n"
            "Rules:\n"
            "1. Answer using ONLY the facts directly mentioned in the context below.\n"
            "2. Do not invent or assume any financial metrics, numbers, or facts.\n"
            '3. If the context does not contain enough information to answer the question, explicitly state: "The available documents do not provide enough information to answer this question."\n'
            "4. Be clear, concise, and accurate. When citing evidence, reference the source document and page number from the context.\n\n"
            f"Context:\n{context}\n\n"
            f"Question:\n{query}\n\n"
            "Answer:"
        )

        logger.info("LangGraph [generate] node invoking local Ollama LLM...")
        response = self.llm.invoke(prompt)

        answer_text = response.content.strip() if hasattr(response, "content") else str(response).strip()

        return {
            "answer": answer_text,
            "status": "generated",
        }

    def _node_validate_grounding(self, state: RAGState) -> Dict[str, Any]:
        """Node: Validate generated answer and presence of grounded sources."""
        if state.get("error"):
            return {"status": "completed_with_error"}

        answer = state.get("answer", "").strip()
        context = state.get("context", "")
        sources = state.get("sources", [])

        if not answer:
            logger.warning("Generated answer is empty. Setting fallback.")
            answer = "The available documents do not provide enough information to answer this question."

        if not context or not sources:
            if not answer or answer == "The available documents do not provide enough information to answer this question.":
                logger.info("Safe fallback verified for empty context.")

        return {
            "answer": answer,
            "status": "completed",
        }

    def invoke(
        self,
        query: str,
        dense_top_k: Optional[int] = None,
        sparse_top_k: Optional[int] = None,
        final_top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full RAG pipeline for a given user query.

        Returns:
            State dictionary containing answer, sources, context, and metadata.
        """
        initial_state: RAGState = {
            "query": query,
            "dense_top_k": dense_top_k or settings.TOP_K,
            "sparse_top_k": sparse_top_k or settings.TOP_K,
            "final_top_k": final_top_k or settings.FINAL_CONTEXT_K,
            "retrieval_results": [],
            "reranked_results": [],
            "context": "",
            "answer": "",
            "sources": [],
            "error": None,
            "status": "initialized",
        }

        return self.graph.invoke(initial_state)

    def run(self, query: str, **kwargs) -> Dict[str, Any]:
        """Alias for invoke."""
        return self.invoke(query=query, **kwargs)
