from pinecone import Pinecone, ServerlessSpec
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from config.settings import get_settings

class VectorStoreService:
    def __init__(self):
        settings = get_settings()
        # Initialize Pinecone
        pc = Pinecone(api_key=settings.pinecone_api_key)
        
        # Create index if doesn't exist
        index_name = settings.pinecone_index_name
        if index_name not in pc.list_indexes().names():
            pc.create_index(
                name=index_name,
                dimension=settings.embedding_dimensions,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        
        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model
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
