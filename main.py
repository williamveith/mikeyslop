import os
import csv
import math
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load .env from the same directory as this script
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

if not YOUTUBE_API_KEY:
    raise RuntimeError(
        f"Missing YOUTUBE_API_KEY. Create a .env file at: {ENV_PATH}"
    )

YOUTUBE_BASE = "https://www.googleapis.com/youtube/v3"

DEFAULT_MODIFIERS = [
    "how to",
    "best",
    "why",
    "beginner",
    "mistakes",
    "review",
    "tutorial",
    "explained",
    "vs",
    "cheap",
    "fast",
    "2026",
]


def youtube_get(endpoint, params):
    params["key"] = YOUTUBE_API_KEY

    response = requests.get(
        f"{YOUTUBE_BASE}/{endpoint}",
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def get_youtube_autocomplete(seed):
    """
    Uses YouTube/Google autocomplete behavior to generate candidate phrases.

    This is not the official YouTube Data API. It is useful for local keyword
    discovery, but it can change or break. For strict API-only usage, replace
    this with your own seed keyword list.
    """
    url = "https://suggestqueries.google.com/complete/search"

    params = {
        "client": "firefox",
        "ds": "yt",
        "q": seed,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data[1]
    except Exception:
        return []


def expand_keywords(seed_terms):
    candidates = set()

    for seed in seed_terms:
        seed = seed.strip().lower()
        if not seed:
            continue

        candidates.add(seed)

        # Base autocomplete
        for suggestion in get_youtube_autocomplete(seed):
            candidates.add(suggestion.lower())

        # Modifier autocomplete
        for modifier in DEFAULT_MODIFIERS:
            phrase = f"{modifier} {seed}"
            candidates.add(phrase)

            for suggestion in get_youtube_autocomplete(phrase):
                candidates.add(suggestion.lower())

        # Alphabet expansion: seed + a, seed + b, etc.
        for letter in "abcdefghijklmnopqrstuvwxyz":
            phrase = f"{seed} {letter}"

            for suggestion in get_youtube_autocomplete(phrase):
                candidates.add(suggestion.lower())

            time.sleep(0.05)

    return sorted(candidates)


def search_videos_for_keyword(keyword, days_back=90, max_results=25):
    published_after = (
        datetime.now(timezone.utc) - timedelta(days=days_back)
    ).isoformat().replace("+00:00", "Z")

    data = youtube_get("search", {
        "part": "snippet",
        "type": "video",
        "q": keyword,
        "order": "relevance",
        "publishedAfter": published_after,
        "maxResults": max_results,
    })

    video_ids = []

    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        if video_id:
            video_ids.append(video_id)

    total_results = data.get("pageInfo", {}).get("totalResults", 0)

    return video_ids, total_results


def get_video_details(video_ids):
    if not video_ids:
        return []

    data = youtube_get("videos", {
        "part": "snippet,statistics",
        "id": ",".join(video_ids),
    })

    return data.get("items", [])


def safe_int(value):
    try:
        return int(value)
    except Exception:
        return 0


def age_days(published_at):
    published = datetime.fromisoformat(
        published_at.replace("Z", "+00:00")
    )
    now = datetime.now(timezone.utc)

    age = (now - published).total_seconds() / 86400
    return max(age, 1)


def median(values):
    values = sorted(values)

    if not values:
        return 0

    n = len(values)
    mid = n // 2

    if n % 2 == 1:
        return values[mid]

    return (values[mid - 1] + values[mid]) / 2


def analyze_keyword(keyword, days_back, max_results, min_views):
    video_ids, total_results = search_videos_for_keyword(
        keyword,
        days_back=days_back,
        max_results=max_results,
    )

    videos = get_video_details(video_ids)

    video_rows = []

    for video in videos:
        snippet = video.get("snippet", {})
        stats = video.get("statistics", {})

        views = safe_int(stats.get("viewCount"))
        likes = safe_int(stats.get("likeCount"))
        comments = safe_int(stats.get("commentCount"))

        if views < min_views:
            continue

        published_at = snippet.get("publishedAt")
        days_old = age_days(published_at)

        engagements = likes + comments
        engagement_rate = engagements / views if views else 0
        views_per_day = views / days_old
        engagements_per_day = engagements / days_old

        video_rows.append({
            "keyword": keyword,
            "video_id": video.get("id"),
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "published_at": published_at,
            "views": views,
            "likes": likes,
            "comments": comments,
            "engagements": engagements,
            "engagement_rate": engagement_rate,
            "views_per_day": views_per_day,
            "engagements_per_day": engagements_per_day,
            "url": f"https://www.youtube.com/watch?v={video.get('id')}",
        })

    if not video_rows:
        return None, []

    engagement_rates = [v["engagement_rate"] for v in video_rows]
    views_per_day_values = [v["views_per_day"] for v in video_rows]
    engagements_per_day_values = [v["engagements_per_day"] for v in video_rows]
    view_values = [v["views"] for v in video_rows]

    median_engagement_rate = median(engagement_rates)
    median_views_per_day = median(views_per_day_values)
    median_engagements_per_day = median(engagements_per_day_values)
    median_views = median(view_values)

    # Demand/interaction signal:
    # Are recent videos getting attention quickly?
    demand_score = (
        math.log10(median_views_per_day + 1)
        * math.log10(median_engagements_per_day + 1)
        * (median_engagement_rate * 100)
    )

    # Competition signal:
    # More total results and more recent videos means more crowded.
    competition_score = (
        math.log10(total_results + 10)
        * math.log10(len(video_rows) + 2)
    )

    # Opportunity:
    # High demand, high interaction, lower competition.
    opportunity_score = demand_score / competition_score if competition_score else 0

    keyword_row = {
        "keyword": keyword,
        "opportunity_score": opportunity_score,
        "demand_score": demand_score,
        "competition_score": competition_score,
        "total_results_estimate": total_results,
        "videos_analyzed": len(video_rows),
        "median_views": median_views,
        "median_views_per_day": median_views_per_day,
        "median_engagements_per_day": median_engagements_per_day,
        "median_engagement_rate": median_engagement_rate,
    }

    return keyword_row, video_rows


def write_csv(path, rows):
    if not rows:
        return

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Local YouTube keyword opportunity scanner"
    )

    parser.add_argument(
        "seeds",
        nargs="+",
        help="Seed topics, e.g. 'fitness' 'semiconductor' 'meal prep'",
    )

    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Only analyze videos published within this many days",
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=25,
        help="Videos to analyze per keyword. Max 50.",
    )

    parser.add_argument(
        "--min-views",
        type=int,
        default=1000,
        help="Ignore videos below this view count",
    )

    parser.add_argument(
        "--limit-keywords",
        type=int,
        default=100,
        help="Maximum generated keywords to analyze",
    )

    args = parser.parse_args()

    print("Generating keyword candidates...")
    keywords = expand_keywords(args.seeds)
    keywords = keywords[:args.limit_keywords]

    print(f"Analyzing {len(keywords)} keywords...")

    keyword_rows = []
    video_rows = []

    for i, keyword in enumerate(keywords, start=1):
        print(f"[{i}/{len(keywords)}] {keyword}")

        try:
            keyword_row, videos = analyze_keyword(
                keyword=keyword,
                days_back=args.days,
                max_results=min(args.max_results, 50),
                min_views=args.min_views,
            )

            if keyword_row:
                keyword_rows.append(keyword_row)
                video_rows.extend(videos)

        except requests.HTTPError as e:
            print(f"HTTP error for keyword '{keyword}': {e}")
        except Exception as e:
            print(f"Error for keyword '{keyword}': {e}")

        time.sleep(0.1)

    keyword_rows.sort(
        key=lambda row: row["opportunity_score"],
        reverse=True,
    )

    write_csv("keyword_opportunities.csv", keyword_rows)
    write_csv("video_evidence.csv", video_rows)

    print("\nTop opportunities:")
    for row in keyword_rows[:25]:
        print(
            f"{row['opportunity_score']:.3f} | "
            f"{row['keyword']} | "
            f"engagement={row['median_engagement_rate']:.2%} | "
            f"views/day={row['median_views_per_day']:.1f} | "
            f"competition={row['competition_score']:.2f}"
        )

    print("\nSaved:")
    print("keyword_opportunities.csv")
    print("video_evidence.csv")


def get_seed_terms_from_env():
    seed_terms = os.getenv("SEED_TERMS", "")

    return [
        term.strip()
        for term in seed_terms.split(",")
        if term.strip()
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Local YouTube keyword opportunity scanner"
    )

    parser.add_argument(
        "seeds",
        nargs="*",
        help=(
            "Seed topics, e.g. 'fitness' 'semiconductor' 'meal prep'. "
            "If omitted, SEED_TERMS will be read from .env."
        ),
    )

    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Only analyze videos published within this many days",
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=25,
        help="Videos to analyze per keyword. Max 50.",
    )

    parser.add_argument(
        "--min-views",
        type=int,
        default=1000,
        help="Ignore videos below this view count",
    )

    parser.add_argument(
        "--limit-keywords",
        type=int,
        default=100,
        help="Maximum generated keywords to analyze",
    )

    args = parser.parse_args()

    seeds = args.seeds or get_seed_terms_from_env()

    if not seeds:
        raise RuntimeError(
            "No seed terms provided. Either run:\n"
            "  python main.py \"fitness for beginners\" \"meal prep\"\n\n"
            "Or add this to your .env file:\n"
            "  SEED_TERMS=fitness for beginners,weight loss,meal prep"
        )

    print(f"Using seed terms: {', '.join(seeds)}")

    print("Generating keyword candidates...")
    keywords = expand_keywords(seeds)
    keywords = keywords[:args.limit_keywords]

    print(f"Analyzing {len(keywords)} keywords...")

    keyword_rows = []
    video_rows = []

    for i, keyword in enumerate(keywords, start=1):
        print(f"[{i}/{len(keywords)}] {keyword}")

        try:
            keyword_row, videos = analyze_keyword(
                keyword=keyword,
                days_back=args.days,
                max_results=min(args.max_results, 50),
                min_views=args.min_views,
            )

            if keyword_row:
                keyword_rows.append(keyword_row)
                video_rows.extend(videos)

        except requests.HTTPError as e:
            print(f"HTTP error for keyword '{keyword}': {e}")
        except Exception as e:
            print(f"Error for keyword '{keyword}': {e}")

        time.sleep(0.1)

    keyword_rows.sort(
        key=lambda row: row["opportunity_score"],
        reverse=True,
    )

    write_csv("keyword_opportunities.csv", keyword_rows)
    write_csv("video_evidence.csv", video_rows)

    print("\nTop opportunities:")
    for row in keyword_rows[:25]:
        print(
            f"{row['opportunity_score']:.3f} | "
            f"{row['keyword']} | "
            f"engagement={row['median_engagement_rate']:.2%} | "
            f"views/day={row['median_views_per_day']:.1f} | "
            f"competition={row['competition_score']:.2f}"
        )

    print("\nSaved:")
    print("keyword_opportunities.csv")
    print("video_evidence.csv")


if __name__ == "__main__":
    main()