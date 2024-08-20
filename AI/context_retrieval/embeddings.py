from langchain.docstore.document import Document
from langchain_community.vectorstores import Qdrant
from AI.config.config import embeddings
from langchain_qdrant import Qdrant  # Đảm bảo đã import Qdrant
import qdrant_client  # Đảm bảo đã import qdrant_client
from dotenv import dotenv_values 
from .embeddings import AIModel

from AI.config.prompts import *
class EmbeddingCreator:
    def __init__(self):
        url = os.getenv('QDRANT_URI')
        self.collection_name = os.getenv('QDRANT_COLLECTION')  # Sử dụng os.getenv để lấy tên collection từ biến môi trường
        self.client  = qdrant_client.QdrantClient(url=url)
        
    def get_vector_database(self):
        qdrant = Qdrant(  # Khởi tạo Qdrant
            client=self.client,
            collection_name=self.collection_name,
            embeddings= AIModel.embeddings
        )
        return qdrant

# use class
# embedding_creator = EmbeddingCreator("my_documents_summary", "/tmp/local_qdrant_summary")
# embedding_creator.create_summary_embeddings(summary)