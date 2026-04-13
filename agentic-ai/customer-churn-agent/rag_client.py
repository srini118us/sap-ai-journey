"""
RAG Client with ChromaDB
========================
Part 3 of MEGA LAB: Document Q&A

Uses ChromaDB for vector storage and SAP GenAI Hub for answers.

Author: Srinivasa Dasari
Date: March 2026
"""

import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional
from dotenv import load_dotenv
from genai_client import GenAIHubClient, GenAIConfig

load_dotenv()


# Sample SAP Documents (simulated)
SAP_DOCUMENTS = [
    {
        "id": "doc1",
        "title": "SAP S/4HANA Cloud Overview",
        "content": """SAP S/4HANA Cloud is an intelligent, integrated ERP system that runs on SAP HANA. 
        It provides real-time analytics, AI-powered automation, and industry best practices. 
        Key modules include Finance (FI), Controlling (CO), Sales (SD), Materials Management (MM), 
        and Production Planning (PP). The system supports both public and private cloud deployment options.
        SAP S/4HANA Cloud uses in-memory computing for faster data processing and real-time insights."""
    },
    {
        "id": "doc2", 
        "title": "SAP AI Core Capabilities",
        "content": """SAP AI Core is a service on SAP BTP that provides scalable AI infrastructure.
        It supports training and deploying ML models, accessing foundation models through GenAI Hub,
        and orchestrating AI workflows. Key features include MLOps pipelines, model serving with KServe,
        integration with SAP applications, and the Generative AI Hub for LLM access.
        SAP AI Core uses resource groups to isolate workloads and supports Docker-based model training."""
    },
    {
        "id": "doc3",
        "title": "SAP Joule AI Assistant",
        "content": """SAP Joule is a generative AI assistant embedded across SAP applications.
        It uses natural language processing to help users complete tasks, find information,
        and get insights from SAP data. Joule integrates with SAP SuccessFactors, SAP S/4HANA,
        SAP Ariba, and other SAP solutions. It can answer questions, generate content,
        automate workflows, and provide recommendations based on enterprise data.
        Joule uses SAP's Business AI principles for responsible and relevant AI."""
    },
    {
        "id": "doc4",
        "title": "SAP BTP Integration Suite",
        "content": """SAP Integration Suite is a comprehensive integration platform on SAP BTP.
        It includes API Management, Open Connectors, Integration Advisor, and Cloud Integration.
        The suite enables connecting SAP and non-SAP applications, managing APIs, and building
        integration flows. It supports various protocols including REST, SOAP, OData, and RFC.
        Pre-built integrations are available for common SAP-to-SAP and SAP-to-third-party scenarios."""
    },
    {
        "id": "doc5",
        "title": "SAP HANA Vector Engine",
        "content": """SAP HANA Cloud includes a vector engine for AI and ML workloads.
        It supports storing and querying high-dimensional vectors for similarity search.
        Key use cases include RAG (Retrieval Augmented Generation), recommendation systems,
        and semantic search. The vector engine integrates with SAP AI Core and supports
        cosine similarity, euclidean distance, and dot product similarity measures.
        Vectors can be generated using embedding models from SAP GenAI Hub."""
    }
]


class RAGClient:
    """
    Retrieval Augmented Generation client using ChromaDB.
    
    Workflow:
    1. Load documents into ChromaDB (with embeddings)
    2. User asks a question
    3. Find relevant documents via semantic search
    4. Send context + question to LLM
    5. Return grounded answer
    """
    
    def __init__(self, collection_name: str = "sap_docs"):
        # Initialize ChromaDB (in-memory for demo)
        self.chroma_client = chromadb.Client()
        
        # Use default embedding function (all-MiniLM-L6-v2)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # Create or get collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn
        )
        
        # Initialize GenAI Hub client
        config = GenAIConfig.from_env()
        self.llm_client = GenAIHubClient(config)
        
        print("[OK] RAG Client initialized")
        print(f"     Collection: {collection_name}")
        print(f"     Documents: {self.collection.count()}")
    
    def load_documents(self, documents: List[Dict]) -> int:
        """Load documents into ChromaDB."""
        print(f"\n[INFO] Loading {len(documents)} documents...")
        
        ids = [doc["id"] for doc in documents]
        contents = [doc["content"] for doc in documents]
        metadatas = [{"title": doc["title"]} for doc in documents]
        
        self.collection.add(
            ids=ids,
            documents=contents,
            metadatas=metadatas
        )
        
        print(f"[OK] Loaded {len(documents)} documents")
        return len(documents)
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search for relevant documents."""
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        docs = []
        for i in range(len(results["ids"][0])):
            docs.append({
                "id": results["ids"][0][i],
                "title": results["metadatas"][0][i]["title"],
                "content": results["documents"][0][i],
                "distance": results["distances"][0][i] if results["distances"] else None
            })
        
        return docs
    
    def ask(self, question: str, top_k: int = 3) -> Dict:
        """
        Answer a question using RAG.
        
        1. Search for relevant docs
        2. Build context from docs
        3. Ask LLM with context
        """
        print(f"\n[QUESTION] {question}")
        
        # Step 1: Retrieve relevant documents
        print(f"[SEARCH] Finding relevant documents...")
        relevant_docs = self.search(question, top_k)
        
        print(f"[OK] Found {len(relevant_docs)} relevant documents:")
        for doc in relevant_docs:
            print(f"     - {doc['title']}")
        
        # Step 2: Build context
        context = "\n\n".join([
            f"Document: {doc['title']}\n{doc['content']}"
            for doc in relevant_docs
        ])
        
        # Step 3: Ask LLM with context
        print(f"[LLM] Generating answer...")
        
        system_prompt = """You are an SAP expert assistant. Answer questions based ONLY on the provided context.
If the answer is not in the context, say "I don't have information about that in the provided documents."
Be concise but thorough. Cite which document your answer comes from when relevant."""
        
        user_prompt = f"""Context:
{context}

Question: {question}

Answer based on the context above:"""
        
        answer = self.llm_client.chat(
            message=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=500
        )
        
        return {
            "question": question,
            "answer": answer,
            "sources": [doc["title"] for doc in relevant_docs]
        }


def run_demo():
    """Run RAG demo with SAP documents."""
    print("=" * 60)
    print(" RAG DEMO - Document Q&A with ChromaDB")
    print("=" * 60)
    
    # Initialize client
    rag = RAGClient()
    
    # Load SAP documents
    rag.load_documents(SAP_DOCUMENTS)
    
    # Demo questions
    questions = [
        "What is SAP Joule and what can it do?",
        "How does SAP HANA support vector search?",
        "What modules are included in SAP S/4HANA Cloud?"
    ]
    
    print("\n" + "=" * 60)
    print(" RAG Q&A Demo")
    print("=" * 60)
    
    for question in questions:
        result = rag.ask(question)
        
        print(f"\n" + "-" * 60)
        print(f"[ANSWER]")
        print(result["answer"])
        print(f"\n[SOURCES] {', '.join(result['sources'])}")
        print("-" * 60)
        
        input("\nPress Enter for next question...")
    
    # Interactive mode
    print("\n" + "=" * 60)
    print(" Interactive Mode (type 'quit' to exit)")
    print("=" * 60)
    
    while True:
        user_question = input("\n[?] Your question: ").strip()
        if user_question.lower() in ['quit', 'exit', 'q']:
            print("[INFO] Goodbye!")
            break
        if not user_question:
            continue
            
        result = rag.ask(user_question)
        print(f"\n[ANSWER]\n{result['answer']}")
        print(f"\n[SOURCES] {', '.join(result['sources'])}")


if __name__ == "__main__":
    run_demo()