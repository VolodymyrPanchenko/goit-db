import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer


INDEX_NAME = "arxiv-papers"
MODEL_NAME = "allenai/specter2_base"

DATA_FILE = Path("data/arxiv_subset.parquet")
EMBEDDINGS_FILE = Path("embeddings/embeddings.npy")

TOP_K = 5


def encode_query(model, query: str) -> np.ndarray:
    return model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )


def print_result(rank, title, category, year, abstract, score):
    print(f"\n#{rank}")
    print(f"Score: {score:.4f}")
    print(f"Title: {title}")
    print(f"Category: {category}")
    print(f"Year: {year}")
    print(f"Abstract: {str(abstract)[:300]}...")


def pinecone_search(index, query_embedding, title, metadata_filter=None):
    print(f"\n=== Pinecone: {title} ===")

    response = index.query(
        vector=query_embedding.tolist(),
        top_k=TOP_K,
        include_metadata=True,
        filter=metadata_filter,
    )

    matches = response.get("matches", [])

    if not matches:
        print("No results found.")
        return

    for rank, match in enumerate(matches, start=1):
        meta = match.get("metadata", {})

        print_result(
            rank=rank,
            title=meta.get("title", ""),
            category=meta.get("category", ""),
            year=meta.get("year", ""),
            abstract=meta.get("abstract", ""),
            score=match.get("score", 0.0),
        )


def local_metric_search(df, embeddings, query_embedding, title, mask=None):
    print(f"\n=== Local metrics: {title} ===")

    if mask is None:
        filtered_df = df.reset_index(drop=False)
    else:
        filtered_df = df[mask].reset_index(drop=False)

    if filtered_df.empty:
        print("No local results found.")
        return

    original_indices = filtered_df["index"].to_numpy()
    filtered_embeddings = embeddings[original_indices]

    dot_scores = filtered_embeddings @ query_embedding

    cosine_scores = dot_scores / (
        np.linalg.norm(filtered_embeddings, axis=1)
        * np.linalg.norm(query_embedding)
    )

    l2_distances = np.linalg.norm(
        filtered_embeddings - query_embedding,
        axis=1,
    )

    metric_results = {
        "Cosine similarity": np.argsort(cosine_scores)[::-1][:TOP_K],
        "Dot product": np.argsort(dot_scores)[::-1][:TOP_K],
        "L2 distance": np.argsort(l2_distances)[:TOP_K],
    }

    for metric_name, top_indices in metric_results.items():
        print(f"\n--- {metric_name} ---")

        for rank, local_idx in enumerate(top_indices, start=1):
            row = filtered_df.iloc[local_idx]

            if metric_name == "Cosine similarity":
                score = cosine_scores[local_idx]
            elif metric_name == "Dot product":
                score = dot_scores[local_idx]
            else:
                score = l2_distances[local_idx]

            print_result(
                rank=rank,
                title=row.get("title", ""),
                category=row.get("category", ""),
                year=row.get("year", ""),
                abstract=row.get("abstract", ""),
                score=score,
            )


def main():
    load_dotenv()

    api_key = os.getenv("PINECONE_API_KEY")

    if not api_key:
        raise ValueError("PINECONE_API_KEY is missing in .env")

    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset file not found: {DATA_FILE}")

    if not EMBEDDINGS_FILE.exists():
        raise FileNotFoundError(f"Embeddings file not found: {EMBEDDINGS_FILE}")

    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    print(f"Loading dataset from {DATA_FILE}")
    df = pd.read_parquet(DATA_FILE)

    print(f"Loading embeddings from {EMBEDDINGS_FILE}")
    embeddings = np.load(EMBEDDINGS_FILE)

    if len(df) != len(embeddings):
        raise ValueError(
            f"Rows count mismatch: dataframe has {len(df)} rows, "
            f"but embeddings file has {len(embeddings)} vectors"
        )

    pc = Pinecone(api_key=api_key)
    index = pc.Index(INDEX_NAME)

    # ------------------------------------------------------------
    # 1. Чистий semantic search без фільтрації
    # ------------------------------------------------------------
    query_semantic = "teaching machines to recognize objects in pictures"
    query_semantic_embedding = encode_query(model, query_semantic)

    print("\n" + "=" * 80)
    print(f"Query: {query_semantic}")

    pinecone_search(
        index=index,
        query_embedding=query_semantic_embedding,
        title="Pure semantic search without filters",
        metadata_filter=None,
    )

    local_metric_search(
        df=df,
        embeddings=embeddings,
        query_embedding=query_semantic_embedding,
        title="Pure semantic search without filters",
        mask=None,
    )

    # ------------------------------------------------------------
    # 2. Example A:
    # reinforcement learning за останні 5 років і категорія cs.LG
    # ------------------------------------------------------------
    query_rl = "reinforcement learning"
    query_rl_embedding = encode_query(model, query_rl)

    current_year = datetime.now().year
    last_5_years = current_year - 5

    filter_a = {
        "category": {"$eq": "cs.LG"},
        "year": {"$gte": last_5_years},
    }

    mask_a = (
        (df["category"] == "cs.LG")
        & (df["year"] >= last_5_years)
    )

    print("\n" + "=" * 80)
    print(f"Query: {query_rl}")
    print(f"Filter A: category = cs.LG, year >= {last_5_years}")

    pinecone_search(
        index=index,
        query_embedding=query_rl_embedding,
        title=f"Example A: cs.LG, year >= {last_5_years}",
        metadata_filter=filter_a,
    )

    local_metric_search(
        df=df,
        embeddings=embeddings,
        query_embedding=query_rl_embedding,
        title=f"Example A: cs.LG, year >= {last_5_years}",
        mask=mask_a,
    )

    # ------------------------------------------------------------
    # 3. Example B:
    # старіші статті до 2015 року, будь-яка категорія
    # ------------------------------------------------------------
    filter_b = {
        "year": {"$lt": 2015},
    }

    mask_b = df["year"] < 2015

    print("\n" + "=" * 80)
    print(f"Query: {query_rl}")
    print("Filter B: year < 2015")

    pinecone_search(
        index=index,
        query_embedding=query_rl_embedding,
        title="Example B: year < 2015, any category",
        metadata_filter=filter_b,
    )

    local_metric_search(
        df=df,
        embeddings=embeddings,
        query_embedding=query_rl_embedding,
        title="Example B: year < 2015, any category",
        mask=mask_b,
    )


if __name__ == "__main__":
    main()