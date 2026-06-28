# YouTube Keyword Opportunity Scanner

This is a small one-off Python script built for my best friend's son to help with his YouTube content planning.

It is not intended to be a polished product, SaaS tool, production analytics platform, or broadly maintained project. It is just a practical helper script for generating YouTube keyword ideas, checking recent video performance, and producing CSV files that can be reviewed in Excel or Google Sheets.

## What It Does

The script takes one or more seed topics, expands them into YouTube keyword candidates, analyzes recent YouTube videos for those keywords, and outputs ranked keyword opportunities.

It helps answer questions like:

* What content topics might be worth making videos about?
* Which keywords have demand but lower competition?
* Which topics are getting views and engagement recently?
* Which keyword ideas should be prioritized first?

## How It Works

At a high level, the script:

1. Reads seed keywords from the command line or `.env` file.
2. Expands those seeds using YouTube/Google autocomplete suggestions.
3. Searches YouTube for recent videos related to each keyword.
4. Pulls video statistics such as views, likes, and comments.
5. Calculates demand, competition, and opportunity scores.
6. Writes results to CSV files inside an `output` folder.

Each run clears and recreates the output files.

## Important Note

This script uses the official YouTube Data API for video searching and statistics.

It also uses YouTube/Google autocomplete behavior to generate keyword candidates. That autocomplete endpoint is not part of the official YouTube Data API and could change or stop working at any time.

This is fine for a personal one-off tool, but it should not be treated as a stable production dependency.

## Requirements

* Windows, macOS, or Linux
* Python 3.10+
* A YouTube Data API key
* A `.env` file containing your API key

Python packages:

```txt
requests
python-dotenv
```

Install dependencies with:

```bash
python -m pip install -r requirements.txt
```

If there is no `requirements.txt`, install manually:

```bash
python -m pip install requests python-dotenv
```

## Setup

Create a `.env` file in the same folder as `main.py`.

```env
YOUTUBE_API_KEY=your_youtube_api_key_here
```

Optionally, you can also add default seed terms:

```env
SEED_TERMS=gaming tips,fortnite settings,youtube shorts
```

## Usage

Run with seed keywords directly:

```bash
python main.py "gaming tips" "fortnite settings" "youtube shorts"
```

Or run without arguments if `SEED_TERMS` is set in `.env`:

```bash
python main.py
```

## Common Options

Analyze videos from the last 90 days by default:

```bash
python main.py "gaming tips"
```

Analyze a longer time window:

```bash
python main.py "gaming tips" --days 180
```

Limit how many generated keywords are analyzed:

```bash
python main.py "gaming tips" --limit-keywords 25
```

Ignore videos below a certain view count:

```bash
python main.py "gaming tips" --min-views 500
```

Analyze more videos per keyword:

```bash
python main.py "gaming tips" --max-results 50
```

Set a stricter YouTube search API safety cap:

```bash
python main.py "gaming tips" --max-search-calls 50
```

## Output Files

The script creates an `output` folder next to `main.py`.

Each run clears the existing contents of `output` and writes new files.

### `output/keyword_opportunities.csv`

This file contains one row per analyzed keyword.

Columns include:

* `keyword`
* `opportunity_score`
* `demand_score`
* `competition_score`
* `total_results_estimate`
* `videos_analyzed`
* `median_views`
* `median_views_per_day`
* `median_engagements_per_day`
* `median_engagement_rate`

This is the main file to review when deciding what content ideas to prioritize.

### `output/video_evidence.csv`

This file contains the individual videos used as evidence for each keyword.

Columns include:

* `keyword`
* `video_id`
* `title`
* `channel`
* `published_at`
* `views`
* `likes`
* `comments`
* `engagements`
* `engagement_rate`
* `views_per_day`
* `engagements_per_day`
* `url`

This file is useful for checking which videos caused a keyword to score well.

## Scoring

The script calculates three main scores.

### Demand Score

Demand score estimates whether recent videos for a keyword are getting attention.

It considers:

* Median views per day
* Median engagements per day
* Median engagement rate

### Competition Score

Competition score estimates how crowded the keyword appears to be.

It considers:

* YouTube's estimated total results
* Number of recent videos found and analyzed

Higher competition means the topic may be harder to break into.

### Opportunity Score

Opportunity score is calculated by comparing demand against competition.

In simple terms:

```txt
Higher demand + lower competition = better opportunity
```

The highest opportunity scores are printed in the terminal and saved to the keyword CSV.

## YouTube API Quota Safety

This script is intentionally conservative with YouTube API usage.

It makes one `search.list` call per keyword analyzed. The script has a hard safety cap of 90 search calls to stay below the common free daily search quota bucket.

Defaults:

```txt
FREE_SEARCH_CALL_LIMIT = 100
HARD_SEARCH_CALL_SAFETY_CAP = 90
```

The script will refuse to run if the estimated search calls are too high.

## Example

```bash
python main.py "minecraft survival" --days 90 --limit-keywords 30 --min-views 1000
```

This will:

1. Generate keyword ideas related to `minecraft survival`.
2. Analyze up to 30 keyword candidates.
3. Only include videos from the last 90 days.
4. Ignore videos with fewer than 1,000 views.
5. Save CSV results to the `output` folder.

## Notes

This project was made for a specific personal use case: helping my best friend's son explore YouTube content ideas.

It is intentionally simple. It does not include:

* A database
* A web interface
* User accounts
* Scheduled jobs
* Advanced error handling
* Production deployment setup

The goal is just to run the script, generate CSV files, and use those files to decide what YouTube content might be worth making.

## Disclaimer

The scores are directional, not absolute truth.

A high score does not guarantee that a video will perform well. YouTube performance depends on many other factors, including:

* Thumbnail quality
* Title quality
* Viewer retention
* Channel authority
* Timing
* Video quality
* Audience fit
* Topic relevance

Use this script as a content research helper, not as a guaranteed prediction engine.
