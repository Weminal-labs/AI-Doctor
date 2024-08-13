from langchain.docstore.document import Document
from langchain_community.vectorstores import Qdrant
from config import embeddings
from .prompts import *
class EmbeddingCreator:
    def __init__(self, collection_name, path):
        self.collection_name = collection_name
        self.path = path

    def create_embeddings(self, docs):
        return Qdrant.from_documents(
            docs,
            embeddings,
            path=self.path,
            collection_name=self.collection_name,
        )

    def create_summary_embeddings(self, summary):
        docs_summary = []
        for count, item in enumerate(summary):
            doc = Document(page_content=item['summary'], metadata={"id": count})
            docs_summary.append(doc)
        
        return self.create_embeddings(docs_summary)

# use class
# embedding_creator = EmbeddingCreator("my_documents_summary", "/tmp/local_qdrant_summary")
# embedding_creator.create_summary_embeddings(summary)