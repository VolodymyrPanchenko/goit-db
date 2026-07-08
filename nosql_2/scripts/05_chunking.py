# scripts/05_chunking.py

import os
import re
import time
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer


load_dotenv()

MODEL_NAME = "allenai/specter2_base"
VECTOR_DIM = 768

FIXED_INDEX = "arxiv-chunks-fixed"
SEMANTIC_INDEX = "arxiv-chunks-semantic"

CLOUD = "aws"
REGION = "us-east-1"

TOP_ARTICLES = 30
CHUNK_SIZE = 120
OVERLAP = 30
TOP_K = 5

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
model = SentenceTransformer(MODEL_NAME)
df = pd.read_parquet("data/arxiv_subset.parquet")


def create_index_if_needed(index_name):
    existing_indexes = [idx["name"] for idx in pc.list_indexes()]

    if index_name not in existing_indexes:
        print(f"Creating index: {index_name}")

        pc.create_index(
            name=index_name,
            dimension=VECTOR_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud=CLOUD, region=REGION),
        )

        while not pc.describe_index(index_name).status["ready"]:
            print(f"Waiting for {index_name}...")
            time.sleep(5)
    else:
        print(f"Index already exists: {index_name}")

    return pc.Index(index_name)


def fixed_chunk(text, size=CHUNK_SIZE, overlap=OVERLAP):
    words = text.split()
    chunks = []
    step = size - overlap

    for start in range(0, len(words), step):
        chunk = " ".join(words[start:start + size])

        if chunk:
            chunks.append(chunk)

        if start + size >= len(words):
            break

    return chunks


def semantic_chunk(text, max_words=CHUNK_SIZE):
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    current = []
    current_words = 0

    for sentence in sentences:
        sentence_words = len(sentence.split())

        if current_words + sentence_words > max_words and current:
            chunks.append(" ".join(current))
            current = [sentence]
            current_words = sentence_words
        else:
            current.append(sentence)
            current_words += sentence_words

    if current:
        chunks.append(" ".join(current))

    return chunks


def build_chunk_records(source_df, strategy):
    records = []

    for _, row in source_df.iterrows():
        abstract = str(row["abstract"])

        if strategy == "fixed":
            chunks = fixed_chunk(abstract)
        else:
            chunks = semantic_chunk(abstract)

        for chunk_number, chunk_text in enumerate(chunks):
            records.append(
                {
                    "id": f"{row['id']}-{strategy}-{chunk_number}",
                    "text": chunk_text,
                    "metadata": {
                        "arxiv_id": str(row["id"]),
                        "title": str(row["title"]),
                        "chunk_text": chunk_text,
                        "chunk_number": chunk_number,
                        "year": int(row["year"]),
                        "category": str(row["category"]),
                    },
                }
            )

    return records


def upload_records(index, records):
    texts = [r["text"] for r in records]

    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    vectors = []

    for record, embedding in zip(records, embeddings):
        vectors.append(
            {
                "id": record["id"],
                "values": embedding.tolist(),
                "metadata": record["metadata"],
            }
        )

    for start in tqdm(range(0, len(vectors), 100), desc="Uploading batches"):
        index.upsert(vectors=vectors[start:start + 100])


def search_chunks(index, query, label):
    query_embedding = model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    result = index.query(
        vector=query_embedding.tolist(),
        top_k=TOP_K,
        include_metadata=True,
    )

    print(f"\n=== {label}: {query} ===")

    for i, match in enumerate(result["matches"], start=1):
        meta = match["metadata"]

        print(f"\n#{i}")
        print(f"Score: {match['score']:.4f}")
        print(f"Title: {meta.get('title', '')}")
        print(f"Chunk: {meta.get('chunk_text', '')[:300]}...")


def main():
    df["abstract_word_count"] = df["abstract"].fillna("").apply(
        lambda x: len(str(x).split())
    )

    longest_df = (
        df.sort_values("abstract_word_count", ascending=False)
        .head(TOP_ARTICLES)
    )

    print(f"Selected articles: {len(longest_df)}")
    print(longest_df[["title", "category", "year", "abstract_word_count"]].head())

    fixed_index = create_index_if_needed(FIXED_INDEX)
    semantic_index = create_index_if_needed(SEMANTIC_INDEX)

    fixed_records = build_chunk_records(longest_df, "fixed")
    semantic_records = build_chunk_records(longest_df, "semantic")

    print(f"\nFixed chunks: {len(fixed_records)}")
    print(f"Semantic chunks: {len(semantic_records)}")

    print("\nUploading fixed chunks...")
    upload_records(fixed_index, fixed_records)

    print("\nUploading semantic chunks...")
    upload_records(semantic_index, semantic_records)

    test_queries = [
        "reinforcement learning",
        "object recognition in images",
        "natural language processing",
    ]

    for query in test_queries:
        search_chunks(fixed_index, query, "Fixed chunks")
        search_chunks(semantic_index, query, "Semantic chunks")


if __name__ == "__main__":
    main()