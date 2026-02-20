import time
from statistics import mean
from tools.vector_db import build_llamaindex_retriever

def precision_at_k(retrieved_ids, relevant_ids, k):
    retrieved_k = retrieved_ids[:k]
    if k == 0:
        return 0.0
    return len(set(retrieved_k) & set(relevant_ids)) / k

def recall_at_k(retrieved_ids, relevant_ids, k):
    if not relevant_ids:
        return 0.0
    retrieved_k = retrieved_ids[:k]
    return len(set(retrieved_k) & set(relevant_ids)) / len(set(relevant_ids))

def eval_retriever(retriever, eval_set, k=5, id_getter=None):
    """
    eval_set: list of dicts like:
      {"query": "...", "relevant_ids": ["doc1", "doc2", ...]}
    id_getter: function(node) -> stable id (doc_id/chunk_id)
    """
    precisions, recalls, latencies = [], [], []

    for ex in eval_set:
        t0 = time.perf_counter()
        nodes = retriever.retrieve(ex["query"])
        latencies.append((time.perf_counter() - t0) * 1000)

        retrieved_ids = [n.node.node_id for n in nodes]

        relevant_ids = ex["relevant_ids"]
        precisions.append(precision_at_k(retrieved_ids, relevant_ids, k))
        recalls.append(recall_at_k(retrieved_ids, relevant_ids, k))

    return {
        "k": k,
        "precision@k": mean(precisions) if precisions else 0.0,
        "recall@k": mean(recalls) if recalls else 0.0,
        "p50_latency_ms": sorted(latencies)[len(latencies)//2] if latencies else 0.0,
        "avg_latency_ms": mean(latencies) if latencies else 0.0,
    }


if __name__ == '__main__':
    wclient, retriever = build_llamaindex_retriever()

    eval_set = [
      {"query_id": "q1", "query": "What are the opening hours of the parking?",
       "relevant_ids": {"afe8dd6d-e031-4281-8795-d264938b21ef", "c36cbc6d-a7ec-445f-beba-e36f2b632b6a"}},
      {"query_id": "q2", "query": "What are the prices?",
       "relevant_ids": {"5b826523-9c42-46b3-aed0-3f1356afde8b", "6795f87f-1b55-4a9e-bb9d-d9e11da1fad7"}},
    ]

    results = eval_retriever(
        retriever,
        eval_set,
        k=2
    )

    wclient.close()
    print(results)
