from embeddings import EmbeddingCreator
from AI.config.prompts import *
import pymongo
class ContextRetriever:
    def __init__(self):
        client = pymongo.MongoClient("localhost", 27017, maxPoolSize=50)
        db = client.localhost
        summary_collection = db['documents']
        summary= summary_collection.find({})
        
        cluster_collection = db['cluster']
        clusters= cluster_collection.find({})
        
        self.template_document_xml = '''
        \t<document index= {index} >
            \t<document_content>
              \t{document}
            \t</document_content>
        \t</document>
        '''
        self. 

    def get_id_related(self, cluster_list, id):
        list_id_cluster = []
        for item in cluster_list:
            list_id_cluster.append(item['index_documents'])
        for item in cluster_list:
            list_id_cluster.append(item['index_documents'])
        list_id_related = []
        for item in list_id_cluster:
            if id in item:
                list_id_related.extend(item)
        final_id_related = list(set(list_id_related))
        return final_id_related
    
    def get_context(self, query):
        qdrant_summary = EmbeddingCreator().get_vector_database()
        search_results = qdrant_summary.similarity_search(query, k=10)
        final_id = self.get_id_related(search_results[0].metadata['id'])
        print("retrieved documents:  \n", search_results)
        count = 1
        print("final_index:    ", list(set(final_id)))
        document_graph = ''
        for index_document in list(set(final_id)):
            item = self.summary[int(index_document)]
            document_xml = self.template_document_xml.format(index=count, document=item['text'])
            document_graph += "\n" + document_xml
            count += 1
        return document_graph