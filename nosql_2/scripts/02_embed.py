from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


DATA_FILE = Path("data/arxiv_subset.parquet")
OUTPUT_DIR = Path("embeddings")
OUTPUT_FILE = OUTPUT_DIR / "embeddings.npy"

MODEL_NAME = "allenai/specter2_base"
BATCH_SIZE = 64


def main():
    # 1. Завантажити датасет
    print(f"Loading dataset from {DATA_FILE}...")
    df = pd.read_parquet(DATA_FILE)

    required_columns = ["title", "abstract"]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}. "
            f"Available columns: {list(df.columns)}"
        )

    # 2. Підготувати тексти
    titles = df["title"].fillna("").astype(str)
    abstracts = df["abstract"].fillna("").astype(str)

    texts = (titles + " [SEP] " + abstracts).tolist()

    print(f"Total texts: {len(texts)}")

    # 3. Завантажити модель
    print(f"Loading model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    # 4. Згенерувати ембеддинги
    print("Generating embeddings...")

    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    # 5. Вивести інформацію
    print(f"Embeddings shape: {embeddings.shape}")
    print(f"Embedding dimension: {embeddings.shape[1]}")

    first_embedding_norm = np.linalg.norm(embeddings[0])
    print(f"First embedding norm: {first_embedding_norm:.4f}")

    # Очікується 768
    if embeddings.shape[1] != 768:
        print(f"Warning: expected embedding dimension 768, got {embeddings.shape[1]}")

    # 6-7. Створити директорію і зберегти файл
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(OUTPUT_FILE, embeddings)

    print(f"Embeddings saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()