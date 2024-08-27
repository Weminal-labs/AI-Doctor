from AI.context_retrieval.embeddings import EmbeddingCreator
from AI.config.prompts import *
import pymongo
import os
from dotenv import load_dotenv

# Return id, link, summary and raw text of retrieval documents

load_dotenv()
class ContextRetriever:
    def __init__(self):
        client = pymongo.MongoClient(os.getenv("MONGODB_URI"))
        db = client.localhost
        document_collection = db['document']
        self.documents = document_collection.find({})
        
        cluster_collection = db['clusters']
        self.clusters = cluster_collection.find({})
        
        self.template_document_xml = '''
        \t<document index= {index} >
            \t<document_content>
              \t{document}
            \t</document_content>
        \t</document>
        '''

    def get_id_related(self, id):
        list_id_cluster = []
        for item in self.clusters:
            list_id_cluster.append(item['index_documents'])
        list_id_related = []
        for item in list_id_cluster:
            if id in item:
                list_id_related.extend(item)
        final_id_related = list(set(list_id_related))
        return final_id_related
    
    def get_context_ids_relevant(self, query):
        qdrant_summary = EmbeddingCreator().get_vector_database()
        search_results = qdrant_summary.similarity_search(query, k=10)
        final_id = self.get_id_related(search_results[0].metadata['id'])
        data_retrieval = []
        for index_document in list(set(final_id)):
            item =  self.documents[int(index_document)]
            data_retrieval.append({"index_document": index_document, "summary":item['summary']})
        return data_retrieval
    
    def get_context(self, context_ids):
        context = ''
        count =  0
        for index_document in context_ids:
            item =  self.documents[int(index_document)]
            document_xml = self.template_document_xml.format(index=count, document=item['text'])
            context += "\n" + document_xml
            count += 1
        return context