"""
Download Stack Overflow Python Q&A dataset from Kaggle and preprocess it.
Run: python data/download_and_preprocess.py
"""

import os
import json
import zipfile
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent
OUTPUT_FILE = DATA_DIR / "processed_qa.json"
RAW_DIR = DATA_DIR / "raw"


def setup_kaggle():
    username = os.getenv("KAGGLE_USERNAME")
    key = os.getenv("KAGGLE_KEY")
    if not username or not key:
        raise ValueError(
            "Set KAGGLE_USERNAME and KAGGLE_KEY in .env file.\n"
            "Get from: https://www.kaggle.com/settings -> API -> Create New Token"
        )
    kaggle_dir = Path.home() / ".kaggle"
    kaggle_dir.mkdir(exist_ok=True)
    creds = {"username": username, "key": key}
    creds_file = kaggle_dir / "kaggle.json"
    with open(creds_file, "w") as f:
        json.dump(creds, f)
    creds_file.chmod(0o600)
    print("Kaggle credentials configured.")


def download_dataset():
    RAW_DIR.mkdir(exist_ok=True)
    print("Downloading Stack Overflow Python Q&A dataset from Kaggle...")
    from kaggle import KaggleApi
    api = KaggleApi()
    api.authenticate()
    api.dataset_download_files(
        "stackoverflow/pythonquestions",
        path=str(RAW_DIR),
        unzip=True,
        quiet=False,
    )
    print("Download complete.")


def clean_html(text: str) -> str:
    if pd.isna(text):
        return ""
    soup = BeautifulSoup(str(text), "lxml")
    # preserve code blocks with markers
    for code in soup.find_all("code"):
        code.replace_with(f" [CODE] {code.get_text()} [/CODE] ")
    return soup.get_text(separator=" ", strip=True)


def preprocess():
    print("Loading CSVs...")
    questions = pd.read_csv(
        RAW_DIR / "Questions.csv",
        encoding="latin-1",
        usecols=["Id", "Title", "Body", "Score"],
    )
    answers = pd.read_csv(
        RAW_DIR / "Answers.csv",
        encoding="latin-1",
        usecols=["Id", "ParentId", "Body", "Score"],
    )
    tags = pd.read_csv(RAW_DIR / "Tags.csv", encoding="latin-1")
    # aggregate tags per question
    tags_grouped = tags.groupby("Id")["Tag"].apply(lambda x: " ".join(x.dropna().astype(str))).reset_index()
    tags_grouped.columns = ["Id", "Tags"]
    questions = questions.merge(tags_grouped, on="Id", how="left")
    questions["Tags"] = questions["Tags"].fillna("")
    print(f"Questions: {len(questions):,} | Answers: {len(answers):,}")

    # keep only quality answers
    print("Filtering high-quality answers (score > 3)...")
    good_answers = answers[answers["Score"] > 3].copy()

    # best answer per question
    best_answers = (
        good_answers.sort_values("Score", ascending=False)
        .drop_duplicates(subset="ParentId")
        .rename(columns={"Id": "AnswerId", "Body": "AnswerBody", "Score": "AnswerScore"})
    )

    # merge
    print("Merging questions + answers...")
    merged = questions.merge(
        best_answers, left_on="Id", right_on="ParentId", how="inner"
    )

    # keep quality questions
    merged = merged[merged["Score"] > 1].copy()
    print(f"After quality filter: {len(merged):,} Q&A pairs")

    # clean HTML
    print("Cleaning HTML from text...")
    # After merge, question Body becomes Body_x
    body_col = "Body_x" if "Body_x" in merged.columns else "Body"
    merged["clean_question"] = merged["Title"] + " " + merged[body_col].apply(clean_html)
    merged["clean_answer"] = merged["AnswerBody"].apply(clean_html)

    # remove very short answers
    merged = merged[merged["clean_answer"].str.len() > 100]

    # sample to keep manageable
    sample_size = min(50000, len(merged))
    final = merged.sample(n=sample_size, random_state=42).reset_index(drop=True)
    print(f"Final dataset size: {len(final):,} rows")

    # build output records
    records = []
    for _, row in final.iterrows():
        records.append(
            {
                "id": str(row["Id"]),
                "title": str(row["Title"]),
                "question": str(row["clean_question"])[:2000],
                "answer": str(row["clean_answer"])[:3000],
                "tags": str(row.get("Tags", "")),
                "question_score": int(row["Score"]),
                "answer_score": int(row["AnswerScore"]),
                "document": (
                    f"Question: {row['Title']}\n\n"
                    f"{str(row['clean_question'])[:1000]}\n\n"
                    f"Answer: {str(row['clean_answer'])[:2000]}"
                ),
            }
        )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Saved to {OUTPUT_FILE}")
    print(f"Sample record title: {records[0]['title']}")
    return records


if __name__ == "__main__":
    setup_kaggle()
    download_dataset()
    preprocess()
    print("\nPreprocessing complete. Run ingest.py next.")
