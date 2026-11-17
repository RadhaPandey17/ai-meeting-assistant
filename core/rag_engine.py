import os
from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.retrievers.bm25 import BM25Retriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from core.vector_store import create_vector_store
from core.Summarize import get_llm

RRF_K = 60  # Standard constant for Reciprocal Rank Fusion

class HybridRAG:
    """
    Advanced RAG Engine featuring:
    1. Hybrid Search: BM25 Sparse Keyword Search + Chroma Dense Vector Embeddings
    2. Reciprocal Rank Fusion (RRF) for result re-ranking
    3. Conversational Memory for multi-turn Q&A context
    """
    def __init__(self, transcript_text: str, chunk_size: int = 800, chunk_overlap: int = 150, kind: str = "meeting"):
        self.transcript_text = transcript_text
        self.kind = kind  # "meeting" or "document"
        self.chat_history: List[Dict[str, str]] = []
        
        # 1. Chunk transcript into documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len
        )
        texts = text_splitter.split_text(transcript_text)
        
        # Wrap chunks into Document objects with metadata line numbers/chunk indices
        self.documents = [
            Document(
                page_content=txt,
                metadata={"chunk_id": i, "start_char": i * (chunk_size - chunk_overlap)}
            )
            for i, txt in enumerate(texts)
        ]
        
        print(f"[HybridRAG] Initialized with {len(self.documents)} text chunks.")
        
        # 2. Build BM25 Sparse Keyword Retriever
        self.bm25_retriever = BM25Retriever.from_documents(self.documents)
        self.bm25_retriever.k = 4
        
        # 3. Build Chroma Dense Vector Store Retriever
        self.vector_store = create_vector_store(self.documents)
        self.vector_retriever = self.vector_store.as_retriever(search_kwargs={"k": 4})
        
        # 4. LLM
        self.llm = get_llm()

    def reciprocal_rank_fusion(self, bm25_docs: List[Document], vector_docs: List[Document], top_n: int = 4) -> List[Document]:
        """
        Combines BM25 and Dense Vector search results using Reciprocal Rank Fusion (RRF).
        """
        doc_scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}

        def _add_ranks(docs: List[Document]):
            for rank, doc in enumerate(docs):
                content = doc.page_content
                doc_map[content] = doc
                score = 1.0 / (RRF_K + rank + 1)
                doc_scores[content] = doc_scores.get(content, 0.0) + score

        _add_ranks(bm25_docs)
        _add_ranks(vector_docs)

        # Sort documents by fused RRF score descending
        sorted_contents = sorted(doc_scores.keys(), key=lambda c: doc_scores[c], reverse=True)
        return [doc_map[c] for c in sorted_contents[:top_n]]

    def get_relevant_context(self, query: str, top_n: int = 4) -> str:
        """Runs hybrid search (BM25 + Vector) and returns merged context string."""
        bm25_docs = self.bm25_retriever.invoke(query)
        vector_docs = self.vector_retriever.invoke(query)
        
        fused_docs = self.reciprocal_rank_fusion(bm25_docs, vector_docs, top_n=top_n)
        
        context_blocks = []
        for i, doc in enumerate(fused_docs):
            context_blocks.append(f"--- Context Chunk {i+1} ---\n{doc.page_content}")
            
        return "\n\n".join(context_blocks)

    def format_history_string(self) -> str:
        """Formats conversational memory into string for prompt context."""
        if not self.chat_history:
            return "No previous conversation history."
        
        formatted = []
        for msg in self.chat_history[-6:]:  # Keep last 6 exchanges (12 messages)
            role = "User" if msg["role"] == "user" else "Assistant"
            formatted.append(f"{role}: {msg['content']}")
        return "\n".join(formatted)

    def answer_question(self, question: str) -> str:
        """
        Answers user question using Hybrid RAG context + Conversational Memory.
        """
        # 1. Retrieve hybrid context
        context = self.get_relevant_context(question)
        history_str = self.format_history_string()
        
        # 2. Build prompt template
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an intelligent AI {assistant} with RAG capabilities.\n"
                "Your task is to answer user questions accurately based on the provided {source_name} context and prior conversation history.\n\n"
                "Rules:\n"
                "- Use the provided Context below to answer the user's question.\n"
                "- If the context does not contain the answer, politely state that the information was not found in the {source_name}.\n"
                "- Be concise, direct, and professional.\n"
                "- When the context has [Page N] markers, mention the page number(s) your answer comes from.\n"
                "- Reply in the same language/style as the user's question (English or Hinglish).\n"
                "- Take prior Conversation History into account for follow-up questions.\n\n"
                "=== Conversation History ===\n"
                "{history}\n\n"
                "=== Context ===\n"
                "{context}"
            ),
            ("user", "{question}")
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        
        print(f"[HybridRAG] Querying LLM for question: '{question}'...")
        is_doc = self.kind == "document"
        answer = chain.invoke({
            "assistant": "Document Assistant" if is_doc else "Meeting Assistant",
            "source_name": "document" if is_doc else "meeting transcript",
            "history": history_str,
            "context": context,
            "question": question
        })
        
        # 3. Save to conversational memory
        self.chat_history.append({"role": "user", "content": question})
        self.chat_history.append({"role": "assistant", "content": answer})
        
        return answer

    def clear_memory(self):
        """Clears session chat history."""
        self.chat_history.clear()
        print("[HybridRAG] Conversational memory cleared.")
