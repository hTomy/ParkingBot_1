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
        print(f"query: {ex["query"]}\nRetrieved passages:\n\t-{"\n\t-".join([n.node.text for n in nodes])}\n{'*'*20}\n\n")
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
    k = 2
    wclient, retriever = build_llamaindex_retriever(k=k)

    eval_set = [
      {"query_id": "q1", "query": "What are the opening hours of the parking?",
       "relevant_ids": {"6772c296-22c0-4e08-9809-081b5242d66a", "cc7dfe38-6819-474a-a867-eaef4370c695"}},
      {"query_id": "q2", "query": "What are the prices?",
       "relevant_ids": {"58cce618-938c-44aa-9a0d-26dbf93f0648", "eb397d30-4e4c-4dc0-9468-0070649705a0"}},
      {"query_id": "q2", "query": "What is the location of the parking?",
       "relevant_ids": {"1b51a0e9-e64c-480e-bb09-1c64da2740c7", "2b77119e-537b-41b6-bf53-f792661d2abb"}},
    ]

    results = eval_retriever(
        retriever,
        eval_set,
        k=k
    )

    wclient.close()
    print(results)
