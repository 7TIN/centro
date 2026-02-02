import json
from pathlib import Path
from src.services.vector_store import VectorStoreService
from langchain.text_splitter import RecursiveCharacterTextSplitter

def ingest_person_knowledge(person_id: str, knowledge_dir: str):
    """Ingest all of Person X's knowledge"""
    
    vector_store = VectorStoreService()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    
    knowledge_path = Path(knowledge_dir)
    
    for file_path in knowledge_path.rglob("*.txt"):
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Split into chunks
        chunks = text_splitter.split_text(content)
        
        # Create metadata
        metadata = [
            {
                "person_id": person_id,
                "source": str(file_path),
                "type": "document",
                "timestamp": file_path.stat().st_mtime
            }
            for _ in chunks
        ]
        
        # Add to vector store
        vector_store.add_documents(chunks, metadata)
        print(f"Ingested: {file_path}")

if __name__ == "__main__":
    ingest_person_knowledge(
        person_id="rahul_backend_engineer",
        knowledge_dir="./data/knowledge_base/rahul/"
    )