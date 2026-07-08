# scripts/06_hybrid_search.py

import os
import re
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from pinecone import Pinecone
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


load_dotenv()

DATA_FILE = Path("data/arxiv_subset.parquet")

INDEX_NAME = "arxiv-papers"
MODEL_NAME = "allenai/specter2_base"

TOP_K = 5
CANDIDATES_K = 50
RRF_K = 60


def tokenize(text: str):
    text = str(text).lower()
    return re.findall(r"\b\w+\b", text)


def prepare_documents(df):
    texts = (
        df["title"].fillna("").astype(str)
        + " "
        + df["abstract"].fillna("").astype(str)
    )

    tokenized_texts = [tokenize(text) for text in texts]

    return texts.tolist(), tokenized_texts


def build_bm25_index(tokenized_texts):
    return BM25Okapi(tokenized_texts)


def bm25_search(query, bm25, df, top_k=CANDIDATES_K):
    query_tokens = tokenize(query)
    scores = bm25.get_scores(query_tokens)

    ranked_indices = scores.argsort()[::-1][:top_k]

    results = []

    for rank, idx in enumerate(ranked_indices, start=1):
        row = df.iloc[idx]

        results.append(
            {
                # BM25 працює з локальним parquet,
                # тому використовуємо arXiv id як спільний id документа.
                "id": str(row["id"]),
                "rank": rank,
                "score": float(scores[idx]),
                "title": row["title"],
                "category": row["category"],
                "year": row["year"],
                "abstract": row["abstract"],
            }
        )

    return results


def vector_search(query, index, model, top_k=CANDIDATES_K):
    query_embedding = model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    response = index.query(
        vector=query_embedding.tolist(),
        top_k=top_k,
        include_metadata=True,
    )

    results = []

    for rank, match in enumerate(response["matches"], start=1):
        meta = match["metadata"]

        results.append(
            {
                # В Pinecone vector id може бути paper_0, paper_1...
                # Але в metadata ми зберігаємо arxiv_id.
                # Саме його треба використовувати для RRF,
                # щоб BM25 і vector search могли склеїти один і той самий документ.
                "id": str(meta.get("arxiv_id", match["id"])),
                "rank": rank,
                "score": float(match["score"]),
                "title": meta.get("title", ""),
                "category": meta.get("category", ""),
                "year": meta.get("year", ""),
                "abstract": meta.get("abstract", ""),
            }
        )

    return results


def reciprocal_rank_fusion(bm25_results, vector_results, rrf_k=RRF_K):
    combined = {}

    for result_list, source_name in [
        (bm25_results, "bm25"),
        (vector_results, "vector"),
    ]:
        for result in result_list:
            doc_id = result["id"]
            rank = result["rank"]

            if doc_id not in combined:
                combined[doc_id] = {
                    "id": doc_id,
                    "title": result["title"],
                    "category": result["category"],
                    "year": result["year"],
                    "abstract": result["abstract"],
                    "rrf_score": 0.0,
                    "sources": [],
                    "bm25_rank": None,
                    "vector_rank": None,
                }

            combined[doc_id]["rrf_score"] += 1 / (rrf_k + rank)
            combined[doc_id]["sources"].append(source_name)

            if source_name == "bm25":
                combined[doc_id]["bm25_rank"] = rank

            if source_name == "vector":
                combined[doc_id]["vector_rank"] = rank

    ranked = sorted(
        combined.values(),
        key=lambda x: x["rrf_score"],
        reverse=True,
    )

    return ranked


def print_results(title, results, top_k=TOP_K, score_name="Score"):
    print(f"\n=== {title} ===")

    for i, result in enumerate(results[:top_k], start=1):
        print(f"\n#{i}")
        print(f"{score_name}: {result.get('score', result.get('rrf_score')):.4f}")
        print(f"Title: {result['title']}")
        print(f"Category: {result['category']}")
        print(f"Year: {result['year']}")

        if "sources" in result:
            print(f"Sources: {', '.join(result['sources'])}")
            print(f"BM25 rank: {result.get('bm25_rank')}")
            print(f"Vector rank: {result.get('vector_rank')}")

        abstract = str(result.get("abstract", ""))
        print(f"Abstract: {abstract[:300]}...")


def compare_top5(bm25_results, vector_results, hybrid_results):
    bm25_top5 = {result["id"] for result in bm25_results[:TOP_K]}
    vector_top5 = {result["id"] for result in vector_results[:TOP_K]}
    hybrid_top5 = {result["id"] for result in hybrid_results[:TOP_K]}

    only_hybrid = hybrid_top5 - bm25_top5 - vector_top5

    print("\n=== Top-5 comparison ===")
    print(f"BM25 top-5 ids: {sorted(bm25_top5)}")
    print(f"Vector top-5 ids: {sorted(vector_top5)}")
    print(f"Hybrid top-5 ids: {sorted(hybrid_top5)}")

    if only_hybrid:
        print("\nDocuments in hybrid top-5 that are not in BM25 or Vector top-5:")
        for doc_id in sorted(only_hybrid):
            print(f"- {doc_id}")
    else:
        print(
            "\nThere are no documents in hybrid top-5 "
            "that are absent from both BM25 and Vector top-5."
        )


def run_query(query, bm25, df, index, model):
    print("\n" + "=" * 80)
    print(f"Query: {query}")

    bm25_results = bm25_search(query, bm25, df)
    vector_results = vector_search(query, index, model)
    hybrid_results = reciprocal_rank_fusion(
        bm25_results,
        vector_results,
        rrf_k=RRF_K,
    )

    print_results(
        "Top-5 BM25",
        bm25_results,
        score_name="BM25 score",
    )

    print_results(
        "Top-5 Vector search",
        vector_results,
        score_name="Vector score",
    )

    print_results(
        f"Top-5 Hybrid search with RRF, k={RRF_K}",
        hybrid_results,
        score_name="RRF score",
    )

    compare_top5(
        bm25_results=bm25_results,
        vector_results=vector_results,
        hybrid_results=hybrid_results,
    )


def main():
    api_key = os.getenv("PINECONE_API_KEY")

    if not api_key:
        raise ValueError("PINECONE_API_KEY is missing. Add it to your .env file.")

    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset file not found: {DATA_FILE}")

    print(f"Loading dataset from {DATA_FILE}")
    df = pd.read_parquet(DATA_FILE)

    print("Building BM25 index...")
    _, tokenized_texts = prepare_documents(df)
    bm25 = build_bm25_index(tokenized_texts)

    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    pc = Pinecone(api_key=api_key)
    index = pc.Index(INDEX_NAME)

    queries = [
        "BERT fine-tuning",
        "Yann LeCun convolutional networks",
        "making computers understand human emotions from text",
    ]

    for query in queries:
        run_query(
            query=query,
            bm25=bm25,
            df=df,
            index=index,
            model=model,
        )


if __name__ == "__main__":
    main()