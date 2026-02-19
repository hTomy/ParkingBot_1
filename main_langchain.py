import os
from typing import Any

import weaviate

from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.vector_stores.weaviate import WeaviateVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain.agents import create_agent

from sqlalchemy import create_engine


# --------- CONFIG ---------
POSTGRES_URI = os.getenv("POSTGRES_URI", "postgresql+psycopg2://user:password@localhost:5432/parking_db")
WEAVIATE_COLLECTION = os.getenv("WEAVIATE_COLLECTION", "ParkingDocs")
WEAVIATE_TEXT_KEY = os.getenv("WEAVIATE_TEXT_KEY", "text")

Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

def build_llamaindex_retriever():
    client = weaviate.connect_to_local()
    vector_store = WeaviateVectorStore(
        weaviate_client=client,
        index_name=WEAVIATE_COLLECTION,
        text_key=WEAVIATE_TEXT_KEY,
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)
    retriever = index.as_retriever(similarity_top_k=4)

    return client, retriever

def build_sql_tools(llm):
    engine = create_engine(POSTGRES_URI)
    db = SQLDatabase(engine, include_tables=["parking_bookings"])
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    sql_tools = toolkit.get_tools()

    return sql_tools


def main():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    sql_tools = build_sql_tools(llm)

    wclient, retriever = build_llamaindex_retriever()

    @tool
    def parking_kb_retrieve(query: str) -> str:
        """Retrieve relevant parking knowledge base passages (hours, location, policies, booking process, pricing rules)."""

        nodes = retriever.retrieve(query)
        if not nodes:
            return "No relevant passages found."

        out = []
        for i, n in enumerate(nodes, start=1):
            out.append(f"[Passage {i}]\n{n.get_content()}")
        return "\n\n---\n\n".join(out)

    tools = sql_tools + [parking_kb_retrieve]

    system_prompt = """You are a parking booking assistant.
    Use SQL tools for structured/transactional data (availability, reservations, user bookings, payments).
    Use parking_kb_retrieve for general information (hours, address, entry/exit, policies, booking steps, pricing rules).
    If you use SQL, You MUST only use SELECT queries (read-only). Never use INSERT/UPDATE/DELETE/DROP/TRUNCATE/ALTER.
    When answering, use the retrieved passages if available; if not found, say you couldn't find it in the knowledge base.
    """

    agent: Any = create_agent(llm, tools, system_prompt=system_prompt)

    response = agent.invoke({
        "messages": [
            {"role": "user",
             # "content": "Hello my licence plate is JKL321 what bookings do I have? And how do I enter the parking?"}
             "content": "what are the opening hours of the parking?"}
        ]
    })

    print(response["messages"][-1].content)

    # Cleanup Weaviate client
    wclient.close()


if __name__ == "__main__":
    main()