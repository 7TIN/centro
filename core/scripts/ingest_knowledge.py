from pathlib import Path
from src.services.vector_store import VectorStoreService

def ingest_person_knowledge(person_id: str, knowledge_dir: str):
    """Ingest all of Person X's knowledge"""
    
    vector_store = VectorStoreService()
    
    knowledge_path = Path(knowledge_dir)
    
    for file_path in knowledge_path.rglob("*.txt"):
        with open(file_path, 'r') as f:
            content = f.read()

        indexed = vector_store.upsert_documents(
            person_id=person_id,
            documents=[content],
            source=str(file_path),
            extra_metadata={
                "type": "document",
                "timestamp": file_path.stat().st_mtime,
            },
        )
        print(f"Ingested: {file_path} ({indexed} chunks)")

if __name__ == "__main__":
    ingest_person_knowledge(
        person_id="rahul_backend_engineer",
        knowledge_dir="./data/knowledge_base/rahul/"
    )
