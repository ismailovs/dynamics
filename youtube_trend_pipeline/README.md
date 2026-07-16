# YouTube Trend Pipeline

A local-first implementation of long-form YouTube discovery, daily snapshots,
theme clustering, opportunity scoring, SQLite storage, and Excel reporting.

## What the first release does

- Rotates a precise rolling 14-day UTC publication window across a balanced
  60-query matrix in ten categories.
- Fetches video, channel, and current public statistics through YouTube Data API
  v3, deduplicating IDs before detail requests.
- Keeps English videos from 8–60 minutes and excludes live/upcoming streams,
  music, trailers, reuploads, missing statistics, and same-channel title
  duplicates.
- Stores videos and one updatable snapshot per UTC date in SQLite.
- Clusters title, description excerpt, tags, and discovery category with
  TF-IDF/K-means. The target is capped by the evidence available, and clusters
  below the configured minimum are removed.
- Calculates immediate performance, channel normalization, engagement, snapshot
  velocity, acceleration, correlation, confidence, and the specified weighted
  opportunity score.
- Generates the six requested Excel worksheets.

The local release deliberately uses a deterministic, lightweight clustering
backend. Sentence Transformers → UMAP → HDBSCAN is the production upgrade path
once collection volume justifies the compute and model dependencies. K-means
already performs the requested final normalization and does not force a target
that the sample count cannot support.

## Install

Python 3.12 is recommended.

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r youtube_trend_pipeline/requirements.txt
export YOUTUBE_API_KEY="<official-api-key>"
```

Never commit the API key. The client uses only official read APIs and must be
operated in accordance with the current YouTube API Services Terms.

## Run

Run the entire live workflow:

```bash
python3 -m youtube_trend_pipeline run-all
```

Run individual stages:

```bash
python3 -m youtube_trend_pipeline init
python3 -m youtube_trend_pipeline collect
python3 -m youtube_trend_pipeline refresh
python3 -m youtube_trend_pipeline analyze
python3 -m youtube_trend_pipeline export
```

Use `snapshot` instead of `refresh` only when current statistics were populated
by another trusted process. Use a JSON fixture without an API key:

```bash
python3 -m youtube_trend_pipeline run-all --fixture videos.json
```

Fixture records use the fields of `youtube_trend_pipeline.models.Video`;
`published_at` is an RFC 3339 timestamp.

## Configuration

| Environment variable | Default | Purpose |
| --- | ---: | --- |
| `YOUTUBE_API_KEY` | empty | Official API key; required for live calls |
| `YT_TRENDS_DB` | `youtube_trends.db` | SQLite file |
| `YT_TRENDS_REPORT` | `youtube_trends.xlsx` | Excel workbook |
| `YT_WINDOW_DAYS` | `14` | Rolling collection window |
| `YT_MIN_DURATION_SECONDS` | `480` | Minimum video length |
| `YT_MAX_DURATION_SECONDS` | `3600` | Maximum video length |
| `YT_MAX_SEARCH_REQUESTS` | `90` | Search cap reserving quota for details |
| `YT_DAILY_QUOTA_UNITS` | `10000` | Quota used to reduce search dynamically |
| `YT_TARGET_CLUSTERS` | `200` | Requested cluster target |
| `YT_MIN_THEME_VIDEOS` | `5` | Minimum retained cluster size |
| `YT_RANDOM_STATE` | `42` | Reproducible K-means seed |

For a mature 50,000–100,000-video corpus, set `YT_TARGET_CLUSTERS` between 800
and 1,200. For the initial 5,000–10,000 corpus, 100–300 is appropriate.

## Daily schedule

Cron example (all times are server-local):

```cron
0 2 * * * cd /app && python3 -m youtube_trend_pipeline collect
0 3 * * * cd /app && python3 -m youtube_trend_pipeline refresh
30 4 * * * cd /app && python3 -m youtube_trend_pipeline analyze
0 5 * * * cd /app && python3 -m youtube_trend_pipeline export
```

`refresh` writes the daily snapshot, so a separate 04:00 snapshot command would
only overwrite the same UTC-date row.

## Quota and data limitations

YouTube does not expose historical daily views for unrelated channels.
Immediate scores use current views divided by age; true velocity, acceleration,
and correlation remain zero until at least two local snapshot dates exist.

Under the standard quota model, a project commonly receives 10,000 units/day
and `search.list` costs 100 units, while `videos.list` and `channels.list` cost
1 unit. That supports roughly 100 search requests—not a separate 100-request
allowance—and at most about 5,000 raw search hits before duplicates if every
request returns 50. The safer default caps search at 90 requests to reserve
units for video/channel detail calls. The effective cap is reduced further based
on the number of active-window videos that `run-all` will refresh, and old
retained videos are not refreshed or included in current theme analysis. Actual
quota and policy can change; verify them in the Google Cloud Console and current
YouTube documentation. Multi-day collection or an approved quota increase is
required for the larger corpus.

Language filtering prefers YouTube's declared audio/default language and uses a
conservative text heuristic when it is absent. Public like/comment statistics
can be disabled; those records are excluded on discovery as requested. If they
become unavailable later, view-only snapshots are still retained. Hidden
subscriber counts are treated as unknown and omitted from channel-normalized
theme medians; scoring renormalizes the remaining weights instead of treating
unknown counts as zero performance.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The tests exercise date-window API parameters, duration parsing, every major
filter, SQLite snapshots, two-cluster scoring, and all six exported worksheets.
