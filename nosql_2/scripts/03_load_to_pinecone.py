import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from tqdm import tqdm


DATA_FILE = Path("data/arxiv_subset.parquet")
EMBEDDINGS_FILE = Path("embeddings/embeddings.npy")

INDEX_NAME = "arxiv-papers"
VECTOR_DIM = 768

BATCH_SIZE = 200

CLOUD = "aws"
REGION = "us-east-1"


def create_index_if_needed(pc: Pinecone, index_name: str, dimension: int):
    existing_indexes = [index["name"] for index in pc.list_indexes()]

    if index_name not in existing_indexes:
        print(f"Creating Pinecone index: {index_name}")

        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=CLOUD,
                region=REGION,
            ),
        )

        while not pc.describe_index(index_name).status["ready"]:
            print("Waiting for index to be ready...")
            time.sleep(5)
    else:
        print(f"Index already exists: {index_name}")

    return pc.Index(index_name)


def build_metadata(row) -> dict:
    return {
        "arxiv_id": str(row.get("id", "")),
        "title": str(row.get("title", "")),
        "abstract": str(row.get("abstract", ""))[:500],
        "authors": str(row.get("authors", ""))[:200],
        "year": int(row.get("year", 0)) if pd.notna(row.get("year", 0)) else 0,
        "category": str(row.get("category", "")),
    }


def main():
    load_dotenv()

    api_key = os.getenv("PINECONE_API_KEY")

    if not api_key:
        raise ValueError("PINECONE_API_KEY is missing. Add it to your .env file.")

    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset file not found: {DATA_FILE}")

    if not EMBEDDINGS_FILE.exists():
        raise FileNotFoundError(f"Embeddings file not found: {EMBEDDINGS_FILE}")

    print(f"Loading dataset from {DATA_FILE}")
    df = pd.read_parquet(DATA_FILE)

    print(f"Loading embeddings from {EMBEDDINGS_FILE}")
    embeddings = np.load(EMBEDDINGS_FILE)

    print(f"Dataset shape: {df.shape}")
    print(f"Embeddings shape: {embeddings.shape}")

    if embeddings.shape[1] != VECTOR_DIM:
        raise ValueError(
            f"Expected vector dimension {VECTOR_DIM}, "
            f"but got {embeddings.shape[1]}"
        )

    if len(df) != len(embeddings):
        raise ValueError(
            f"Rows count mismatch: dataframe has {len(df)} rows, "
            f"but embeddings file has {len(embeddings)} vectors"
        )

    pc = Pinecone(api_key=api_key)

    index = create_index_if_needed(
        pc=pc,
        index_name=INDEX_NAME,
        dimension=embeddings.shape[1],
    )

    for start in tqdm(range(0, len(df), BATCH_SIZE), desc="Uploading to Pinecone"):
        end = min(start + BATCH_SIZE, len(df))

        batch_df = df.iloc[start:end]
        batch_embeddings = embeddings[start:end]

        vectors = []

        for local_idx, (_, row) in enumerate(batch_df.iterrows()):
            global_idx = start + local_idx

            vector = {
                "id": f"paper_{global_idx}",
                "values": batch_embeddings[local_idx].tolist(),
                "metadata": build_metadata(row),
            }

            vectors.append(vector)

        index.upsert(vectors=vectors)

    print("Upload completed.")

    stats = index.describe_index_stats()

    print("\nIndex stats:")
    print(stats)

    print(f"\nTotal vector count: {stats.get('total_vector_count', 0)}")


if __name__ == "__main__":
    main()