import json
from pathlib import Path

import pandas as pd
from tqdm import tqdm


INPUT_FILE = Path("arxiv-metadata-oai-snapshot.json")
OUTPUT_DIR = Path("data")
OUTPUT_FILE = OUTPUT_DIR / "arxiv_subset.parquet"

MAX_RECORDS = 10_000


def extract_year(paper: dict) -> int:
    """
    Беремо рік із першої версії статті.
    Це ближче до року публікації на arXiv.

    Приклад created:
    "Mon, 2 Apr 2007 19:18:42 GMT"
    """
    try:
        versions = paper.get("versions", [])

        if versions:
            created = versions[0].get("created", "")
            parts = created.split()

            # Mon, 2 Apr 2007 19:18:42 GMT
            return int(parts[3])

    except (IndexError, ValueError, AttributeError):
        pass

    # запасний варіант — дата останнього оновлення
    try:
        return int(paper.get("update_date", "2000-01-01")[:4])
    except ValueError:
        return 2000


def format_authors(paper: dict) -> str:
    """
    authors_parsed має формат:
    [["Balázs", "C.", ""], ["Berger", "E. L.", ""]]

    Робимо читабельний рядок:
    Balázs C., Berger E. L.
    """
    parsed = paper.get("authors_parsed", [])

    if parsed:
        authors = []

        for entry in parsed[:10]:
            last_name = entry[0].strip() if len(entry) > 0 else ""
            initials = entry[1].strip() if len(entry) > 1 else ""

            full_name = f"{last_name} {initials}".strip()

            if full_name:
                authors.append(full_name)

        return ", ".join(authors)

    return str(paper.get("authors", "")).replace("\n", " ").strip()


def main():
    records = []

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"File not found: {INPUT_FILE}. "
            "Download and unzip the Kaggle arXiv dataset first."
        )

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        for line in tqdm(file, desc="Читаємо датасет"):
            if len(records) >= MAX_RECORDS:
                break

            line = line.strip()

            if not line:
                continue

            paper = json.loads(line)

            title = str(paper.get("title", "")).replace("\n", " ").strip()
            abstract = str(paper.get("abstract", "")).replace("\n", " ").strip()

            # пропускаємо записи без title або abstract
            if not title or not abstract:
                continue

            categories_raw = str(paper.get("categories", "unknown"))
            categories = categories_raw.split()
            primary_category = categories[0] if categories else "unknown"

            records.append(
                {
                    "id": paper.get("id", ""),
                    "title": title,
                    "abstract": abstract,
                    "authors": format_authors(paper),
                    "year": extract_year(paper),
                    "category": primary_category,
                }
            )

    df = pd.DataFrame(records)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_FILE, index=False)

    print(f"\nЗавантажено статей: {len(df)}")

    print("\nРозподіл за категоріями (топ-10):")
    print(df["category"].value_counts().head(10))

    print("\nРозподіл за роками:")
    print(df["year"].value_counts().sort_index())

    print("\nПриклад запису:")
    print(df.iloc[0].to_dict())

    print(f"\nЗбережено в {OUTPUT_FILE}")


if __name__ == "__main__":
    main()