from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from src.agents.orchestrator import app as langgraph_app
from src.services.memory import ConversationMemory
from src.models.database import SessionLocal

app = FastAPI(title="Person X AI Assistant")

# Request/Response models
class QueryRequest(BaseModel):
    question: str
    person_id: str
    conversation_id: str | None = None

class QueryResponse(BaseModel):
    answer: str
    confidence: float
    sources: list
    conversation_id: str

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/query", response_model=QueryResponse)
async def query_person_x(request: QueryRequest, db = Depends(get_db)):
    """Main query endpoint"""
    
    try:
        # Load conversation memory
        memory = ConversationMemory(db)
        history = memory.get_history(request.conversation_id)
        
        # Load person profile
        person_profile = load_person_profile(request.person_id)
        
        # Prepare state
        initial_state = {
            "question": request.question,
            "conversation_history": history,
            "metadata": {
                "person_style": person_profile["style"],
                "person_patterns": person_profile["patterns"]
            }
        }
        
        # Run LangGraph workflow
        result = langgraph_app.invoke(initial_state)
        
        # Save to memory
        conv_id = memory.save_interaction(
            conversation_id=request.conversation_id,
            question=request.question,
            answer=result["final_response"]
        )
        
        return QueryResponse(
            answer=result["final_response"],
            confidence=result["validation_result"]["confidence"],
            sources=[doc["source"] for doc in result["retrieved_docs"]],
            conversation_id=conv_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest")
async def ingest_knowledge(person_id: str, documents: list[dict]):
    """Endpoint to add new knowledge"""
    # Implementation for adding documents
    pass

@app.get("/health")
async def health_check():
    return {"status": "healthy"}