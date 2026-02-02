from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from config.settings import settings

class VectorStoreService:
    def __init__(self):
        # Initialize Pinecone
        pc = Pinecone(api_key=settings.pinecone_api_key)
        
        # Create index if doesn't exist
        index_name = settings.pinecone_index
        if index_name not in pc.list_indexes().names():
            pc.create_index(
                name=index_name,
                dimension=1536,  # text-embedding-3-small
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model
        )
        
        # Initialize vector store
        self.vectorstore = PineconeVectorStore(
            index_name=index_name,
            embedding=self.embeddings
        )
    
    def add_documents(self, documents: list, metadata: list):
        """Add documents to vector store"""
        self.vectorstore.add_texts(
            texts=documents,
            metadatas=metadata
        )
    
    def search(self, query: str, top_k: int = 5, filters: dict = None):
        """Semantic search"""
        results = self.vectorstore.similarity_search_with_score(
            query=query,
            k=top_k,
            filter=filters
        )
        return results