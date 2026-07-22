# convert.py — запустите один раз перед загрузкой

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
IMPORT_DIR = BASE_DIR / "import"

IMPORT_DIR.mkdir(exist_ok=True)


# movies.dat: MovieID::Title::Genres
with (
    open(BASE_DIR / "movies.dat", encoding="latin-1") as f_in,
    open(
        IMPORT_DIR / "movies.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as f_out,
):
    writer = csv.writer(f_out)
    writer.writerow(["movieId", "title", "genres"])

    for line in f_in:
        parts = line.rstrip("\n").split("::")
        writer.writerow(parts)


# ratings.dat: UserID::MovieID::Rating::Timestamp
with (
    open(BASE_DIR / "ratings.dat", encoding="latin-1") as f_in,
    open(
        IMPORT_DIR / "ratings.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as f_out,
):
    writer = csv.writer(f_out)
    writer.writerow(["userId", "movieId", "rating", "timestamp"])

    for line in f_in:
        parts = line.rstrip("\n").split("::")
        writer.writerow(parts)


# users.dat: UserID::Gender::Age::Occupation::Zip
with (
    open(BASE_DIR / "users.dat", encoding="latin-1") as f_in,
    open(
        IMPORT_DIR / "users.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as f_out,
):
    writer = csv.writer(f_out)
    writer.writerow(["userId", "gender", "age", "occupation"])

    for line in f_in:
        parts = line.rstrip("\n").split("::")
        writer.writerow(parts[:4])  # Zip не нужен


print("Конвертация завершена.")
print(f"CSV-файлы сохранены в: {IMPORT_DIR}")