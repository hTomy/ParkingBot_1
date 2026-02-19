import os
from typing import Any

import weaviate

from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.weaviate import WeaviateVectorStore
from utils import config

def build_llamaindex_retriever():
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

    client = weaviate.connect_to_local()
    vector_store = WeaviateVectorStore(
        weaviate_client=client,
        index_name=config.WEAVIATE_COLLECTION,
        text_key=config.WEAVIATE_TEXT_KEY,
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)
    retriever = index.as_retriever(similarity_top_k=4)

    return client, retriever


def parking_kb_retrieve(query: str) -> str:
    """Retrieve relevant parking knowledge base passages (hours, location, policies, booking process, pricing rules)."""
    wclient, retriever = build_llamaindex_retriever()

    nodes = retriever.retrieve(query)
    if not nodes:
        return "No relevant passages found."

    out = []
    for i, n in enumerate(nodes, start=1):
        out.append(f"[Passage {i}]\n{n.get_content()}")

    wclient.close()
    return "\n\n---\n\n".join(out)
