"""
Scrape Polar Flow reviews from Google Play across multiple languages/locales,
going back 5 years. RESUMABLE: saves progress after each locale, so if it
dies or you stop it (network drop, Ctrl+C), just re-run the same command and
it picks up from the next unfinished locale instead of starting over.

Install dependencies first:
    pip install google-play-scraper pandas vaderSentiment --break-system-packages

IMPORTANT CAVEAT:
VADER sentiment scoring and the English keyword-based theme tags only work
reliably on ENGLISH text. They're computed for every row, but for non-English
reviews those columns aren't meaningful — filter to lang == "en" before
trusting sentiment_label or the mentions_* columns.

To start completely fresh (ignore prior progress), delete these two files
first: polar_flow_reviews_multilang.csv and completed_locales.txt
"""

import os
import socket
import time
from datetime import datetime, timedelta
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# A dropped/stalled connection will now raise after this many seconds instead
# of hanging silently forever.
socket.setdefaulttimeout(20)

APP_ID = "fi.polar.polarflow"
OUTPUT_CSV = "polar_flow_reviews_multilang.csv"
COMPLETED_LOG = "completed_locales.txt"

END_DATE = datetime(2026, 9, 30)
START_DATE = END_DATE - timedelta(days=5 * 365)

MAX_BATCHES_PER_LOCALE = 500  # safety valve, not a target

LOCALES = [
    ("en", "us"),
    ("de", "de"),
    ("fi", "fi"),
    ("es", "es"),
    ("fr", "fr"),
    ("it", "it"),
    ("nl", "nl"),
    ("sv", "se"),
    ("no", "no"),
    ("da", "dk"),
    ("pt", "br"),
    ("ru", "ru"),
    ("ja", "jp"),
    ("ko", "kr"),
    ("zh", "cn"),
    ("pl", "pl"),
    ("tr", "tr"),
]


def load_completed():
    if not os.path.exists(COMPLETED_LOG):
        return set()
    with open(COMPLETED_LOG) as f:
        return set(line.strip() for line in f if line.strip())


def mark_completed(lang, country):
    with open(COMPLETED_LOG, "a") as f:
        f.write(f"{lang}-{country}\n")


def scrape_locale(app_id, lang, country, start_date, end_date, max_batch_retries=3):
    from google_play_scraper import reviews, Sort

    all_reviews = []
    continuation_token = None

    for batch_num in range(MAX_BATCHES_PER_LOCALE):
        batch = None
        for attempt in range(1, max_batch_retries + 1):
            try:
                batch, continuation_token = reviews(
                    app_id,
                    lang=lang,
                    country=country,
                    sort=Sort.NEWEST,
                    count=200,
                    continuation_token=continuation_token,
                )
                break
            except Exception as e:
                print(f"    batch {batch_num + 1}, attempt {attempt}/{max_batch_retries} "
                      f"failed: {e}")
                if attempt < max_batch_retries:
                    time.sleep(3 * attempt)

        if batch is None:
            print(f"    batch {batch_num + 1}: giving up after {max_batch_retries} "
                  f"retries, stopping this locale here (partial data kept).")
            break

        if not batch:
            break

        all_reviews.extend(batch)
        oldest_in_batch = min(r["at"] for r in batch)
        print(f"    batch {batch_num + 1}: {len(all_reviews)} so far, "
              f"oldest so far {oldest_in_batch.date()}")

        if oldest_in_batch < start_date:
            break
        if continuation_token is None:
            break
        time.sleep(0.4)

    df = pd.DataFrame(all_reviews)
    if df.empty:
        return df

    df = df.rename(columns={
        "content": "text",
        "score": "rating",
        "at": "date",
        "thumbsUpCount": "helpful_count",
    })
    df["lang"] = lang
    df["country"] = country
    df["source"] = "google_play"
    df = df[["reviewId", "text", "rating", "date", "helpful_count",
              "lang", "country", "source"]]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df[(df["date"] >= start_date) & (df["date"] <= end_date)]


def add_sentiment(df):
    """English-reliable only — see module docstring caveat."""
    analyzer = SentimentIntensityAnalyzer()
    df["sentiment_compound"] = df["text"].astype(str).apply(
        lambda t: analyzer.polarity_scores(t)["compound"]
    )
    df["sentiment_label"] = pd.cut(
        df["sentiment_compound"],
        bins=[-1.01, -0.05, 0.05, 1.01],
        labels=["negative", "neutral", "positive"],
    )
    return df


COMPLAINT_KEYWORDS = {
    "sync": ["sync", "syncing", "bluetooth", "pairing", "connect"],
    "crash_reliability": ["crash", "crashes", "freeze", "bug", "glitch", "unreliable"],
    "ui_ux": ["ugly", "confusing", "clunky", "outdated", "hard to use", "navigate", "interface", "design"],
    "vs_strava": ["strava"],
    "social": ["kudos", "follow", "segment", "social", "friends", "community"],
    "data_viz": ["graph", "chart", "trend", "insight", "analysis", "data"],
    "customer_support": ["support", "customer service", "response", "help desk"],
}

def tag_themes(df):
    """English keyword matching only — see module docstring caveat."""
    text_lower = df["text"].astype(str).str.lower()
    for theme, keywords in COMPLAINT_KEYWORDS.items():
        df[f"mentions_{theme}"] = text_lower.apply(
            lambda t: any(k in t for k in keywords)
        )
    return df


def append_to_csv(df, path=OUTPUT_CSV):
    file_exists = os.path.exists(path)
    df.to_csv(path, mode="a", header=not file_exists, index=False)


def summarize(path=OUTPUT_CSV):
    if not os.path.exists(path):
        print("No data saved yet.")
        return

    df = pd.read_csv(path)
    # dedupe across locales in case the same review id ever surfaced twice
    before = len(df)
    df = df.drop_duplicates(subset="reviewId")
    if len(df) != before:
        print(f"(Deduped {before - len(df)} cross-locale duplicate reviews)\n")

    print("=== Reviews by locale ===")
    print(df.groupby(["lang", "country"]).size().sort_values(ascending=False).to_string())
    print()

    en_df = df[df["lang"] == "en"]
    print(f"=== English-only subset: {len(en_df)} of {len(df)} total reviews ===")
    print("(Sentiment/theme numbers below are only reliable for this subset)")
    print()

    print("=== Rating distribution (ALL languages) ===")
    print(df["rating"].value_counts().sort_index())
    print()

    if "sentiment_label" in en_df.columns:
        print("=== Sentiment distribution (English-only) ===")
        print(en_df["sentiment_label"].value_counts())
        print()

        print("=== Theme mention counts, English-only non-positive reviews ===")
        neg = en_df[en_df["sentiment_label"] != "positive"]
        for theme in COMPLAINT_KEYWORDS:
            col = f"mentions_{theme}"
            if len(neg) > 0 and col in neg.columns:
                print(f"{theme}: {neg[col].sum()} mentions "
                      f"({neg[col].mean()*100:.1f}% of non-positive EN reviews)")


if __name__ == "__main__":
    completed = load_completed()
    if completed:
        print(f"Resuming — {len(completed)} locale(s) already done: "
              f"{', '.join(sorted(completed))}\n")

    print(f"Scraping Polar Flow Google Play reviews, {len(LOCALES)} locales total, "
          f"{START_DATE.date()} to {END_DATE.date()}...\n")

    try:
        for lang, country in LOCALES:
            key = f"{lang}-{country}"
            if key in completed:
                print(f"--- Locale {key}: already done, skipping ---\n")
                continue

            print(f"--- Locale {key} ---")
            df = scrape_locale(APP_ID, lang, country, START_DATE, END_DATE)
            print(f"  -> {len(df)} reviews for {key}")

            if not df.empty:
                df = add_sentiment(df)
                df = tag_themes(df)
                append_to_csv(df)
                print(f"  -> saved to {OUTPUT_CSV}")

            mark_completed(lang, country)
            print()
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nInterrupted by user. Progress so far is saved — "
              "just re-run this script to resume from the next locale.\n")

    print("\n=== FINAL SUMMARY (of everything saved so far) ===\n")
    summarize()
