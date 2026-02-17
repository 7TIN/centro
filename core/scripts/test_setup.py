#!/usr/bin/env python3
"""
Quick test script to verify Step 1 setup.
Run with: uv run python scripts/test_setup.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_database_connection():
    """Test database connection."""
    print("Testing database connection...")
    try:
        from src.core.database import check_db_connection
        
        is_healthy = await check_db_connection()
        if is_healthy:
            print("Database connection successful")
            return True
        else:
            print("Database connection failed")
            return False
    except Exception as e:
        print(f"Database connection error: {e}")
        return False


async def test_settings():
    """Test settings loading."""
    print("\nTesting settings...")
    try:
        from config.settings import get_settings
        
        settings = get_settings()
        print(f"Settings loaded successfully")
        print(f"   - Environment: {settings.environment}")
        print(f"   - Debug: {settings.debug}")
        print(f"   - Database URL: {settings.database_url[:30]}...")
        print(f"   - Gemini Model: {settings.gemini_model}")
        print(f"   - Pinecone Index: {settings.pinecone_index_name or 'not configured'}")
        return True
    except Exception as e:
        print(f"Settings error: {e}")
        return False


async def test_models():
    """Test model imports."""
    print("\nTesting models...")
    try:
        from src.models.database import User, Person, KnowledgeEntry, Conversation, Message
        from src.models.schemas import (
            PersonCreate,
            KnowledgeEntryCreate,
            ChatRequest,
            HealthResponse
        )
        
        print("All models imported successfully")
        print(f"   - Database models: User, Person, KnowledgeEntry, Conversation, Message")
        print(f"   - Schema models: PersonCreate, KnowledgeEntryCreate, ChatRequest, HealthResponse")
        return True
    except Exception as e:
        print(f"Model import error: {e}")
        return False


async def test_table_creation():
    """Test if tables exist in database."""
    print("\nTesting database tables...")
    try:
        from sqlalchemy import text
        from src.core.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Check if tables exist
            result = await session.execute(
                text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
            )
            tables = [row[0] for row in result.fetchall()]
            
            expected_tables = ['users', 'persons', 'knowledge_entries', 'conversations', 'messages']
            
            if 'alembic_version' in tables:
                tables.remove('alembic_version')
            
            if set(expected_tables) == set(tables):
                print("All expected tables exist")
                for table in sorted(tables):
                    print(f"   - {table}")
                return True
            else:
                print(f"Table mismatch")
                print(f"   Expected: {sorted(expected_tables)}")
                print(f"   Found: {sorted(tables)}")
                return False
    except Exception as e:
        print(f"Table check error: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("PersonX AI Assistant - Step 1 Setup Verification")
    print("=" * 60)
    
    results = []
    
    # Test settings (doesn't require DB)
    results.append(await test_settings())
    
    # Test models (doesn't require DB)
    results.append(await test_models())
    
    # Test database connection
    results.append(await test_database_connection())
    
    # Test tables (requires migration)
    results.append(await test_table_creation())
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    total = len(results)
    passed = sum(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\nAll tests passed! Step 1 setup is complete.")
        print("\nNext steps:")
        print("1. Start the API: uv run uvicorn src.main:app --reload")
        print("2. Test health endpoint: curl http://localhost:8000/health")
        print("3. View API docs: http://localhost:8000/docs")
        return 0
    else:
        print("\nSome tests failed. Please check the errors above.")
        print("\nCommon fixes:")
        print("- Make sure Docker is running: docker-compose ps")
        print("- Run migrations: uv run alembic upgrade head")
        print("- Check .env file has required variables")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
