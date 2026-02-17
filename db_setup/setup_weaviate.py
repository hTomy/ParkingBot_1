import weaviate
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, Settings
from llama_index.vector_stores.weaviate import WeaviateVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core.node_parser import TokenTextSplitter

if __name__ == '__main__':
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
    Settings.llm = OpenAI(model="gpt-4o-mini")

    documents = SimpleDirectoryReader(input_dir="docs").load_data()

    with weaviate.connect_to_local() as client:

        vector_store = WeaviateVectorStore(
            weaviate_client=client,
            index_name="ParkingDocs",
            text_key="text",
        )

        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            transformations=[TokenTextSplitter(chunk_size=80, chunk_overlap=20)], # Sentence splitter was creating 1-2 chunks only
        )

        query_engine = index.as_query_engine(similarity_top_k=3)

        #Testing
        resp = query_engine.query("What are the working hours and how do I enter?")
        print(str(resp))
