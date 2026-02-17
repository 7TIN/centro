from sqlalchemy.orm import Session
from src.models.database import Conversation, Message
from datetime import datetime, timedelta
import json

class ConversationMemory:
    def __init__(self, db: Session, max_messages: int = 10):
        self.db = db
        self.max_messages = max_messages
    
    def get_history(self, conversation_id: str | None) -> list:
        """Get recent conversation history"""
        if not conversation_id:
            return []
        
        messages = self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.timestamp.desc()).limit(self.max_messages).all()
        
        return [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(messages)
        ]
    
    def save_interaction(
        self, 
        conversation_id: str | None,
        question: str,
        answer: str
    ) -> str:
        """Save Q&A pair"""
        
        # Create conversation if new
        if not conversation_id:
            conv = Conversation(
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow()
            )
            self.db.add(conv)
            self.db.flush()
            conversation_id = str(conv.id)
        
        # Save question
        self.db.add(Message(
            conversation_id=conversation_id,
            role="user",
            content=question,
            timestamp=datetime.utcnow()
        ))
        
        # Save answer
        self.db.add(Message(
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
            timestamp=datetime.utcnow()
        ))
        
        self.db.commit()
        return conversation_id