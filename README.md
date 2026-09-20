# 🎯 SyllabuSync

**Find the exact lecture segment for YOUR syllabus topic — built for HackDevengers 2.0 (Open Innovation Hackathon)**

## The Problem
Ask any Tier-2/Tier-3 college student how they study for exams and you'll hear the same story: they search YouTube for a syllabus topic and, after digging for hours, either find nothing useful, or find a video made for a *completely different* university's syllabus — one that overlaps with maybe 2-4 of their actual topics. When they do find something relevant, it's often a 2-4 hour unstructured lecture that assumes you've watched five earlier videos in a series, and there's no way to tell where in the video your specific topic even starts. Worst of all, a single unit with 6 topics frequently ends up scattered across 6 completely different lectures on 6 different channels — turning a 30-minute study session into an afternoon of searching.

## The Solution
SyllabuSync flips the workflow: instead of the student searching video-by-video, the student pastes **their own syllabus topics** (this works for literally any college or university — it doesn't depend on a pre-loaded syllabus database, which is the whole reason the "wrong university's syllabus" problem exists in the first place). For every topic, SyllabuSync:

1. Searches YouTube and ranks results by actual relevance to that specific topic (not just view count).
2. Reads the top video's description for timestamped chapters (the `0:00 Topic Name` lines creators add) and matches your topic to the exact chapter — so you get a direct **jump-to-segment link**, not a 4-hour video to scrub through.
3. Detects when a single lecture already covers **multiple topics** from your unit, and calls it out explicitly — so instead of hunting across 6 channels, you find out one video already has 3 of your 6 topics.
4. Lets you check off topics as watched and tracks per-unit progress.

## Why It Matters
- **Real-world impact:** solves a daily, hours-wasting problem for a huge population of students who don't have access to curated coaching-class content — directly from a problem description by an actual affected student.
- **Generalizable by design:** works for any syllabus from any college, because the student provides the topics — no fragile pre-loaded database that only covers a handful of universities (which is exactly the trap this project avoids).
- **Real technical depth:** live YouTube Data API integration, relevance ranking, and a custom timestamp-chapter parser/matcher (regex + keyword-overlap scoring) — not just a search bar wrapper.
- **Scalable:** works standalone with a free YouTube API key; the same architecture extends naturally to other platforms (Unacademy, university OCW, etc.) as additional sources.

## Tech Stack
- **Backend:** Flask (Python) with a small REST API (`/api/find_topics`, `/api/mark_watched`, `/api/progress`, `/api/stats`)
- **Frontend:** hand-built HTML / CSS / vanilla JS (no framework) — single-page app with tabbed views
- **Data:** SQLite (per-student unit & topic-match history, watched tracking)
- **Video search:** YouTube Data API v3 (`search.list` + `videos.list`)
- **Chapter matching:** custom regex-based timestamp parser + keyword-overlap topic matcher

## Project Structure
```
app.py                 Flask app + REST API
youtube_helper.py       YouTube search, ranking, chapter parsing/matching
syllabus_presets.py     Example syllabi for the "quick-try" dropdown
templates/index.html    Single-page frontend
static/css/style.css    Styling
static/js/main.js       Frontend logic (tabs, API calls, rendering)
requirements.txt
```

## Running Locally
```bash
pip install -r requirements.txt
python app.py
```
Then open `http://127.0.0.1:5000` in your browser.

### Going live with real YouTube results (free, ~2 minutes)
By default the app runs in **Demo Mode** (clearly banner-labeled in the UI) with simulated results, so it's fully usable and demoable without any setup. To get real YouTube matches:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/apis/library/youtube.googleapis.com) and enable the **YouTube Data API v3** on a project (free tier is generous — default quota covers ~100 topic searches/day).
2. Create an API key under **APIs & Services → Credentials**.
3. Set it as an environment variable before running:
   ```bash
   export YOUTUBE_API_KEY="your_key_here"
   python app.py
   ```

## How It Works Under the Hood
1. **Search & rank:** for each topic, query `search.list` with `{topic} {subject}`, fetch full snippet + stats for the top candidates via `videos.list`, then score each by keyword overlap between the topic and the video's title/description (relevance-first, view count only as a tiebreaker).
2. **Chapter parsing:** the winning video's description is scanned line-by-line for timestamp patterns (`0:00`, `1:23:45`, etc.) paired with a label — the same format most Indian YouTube education channels already use for chapters.
3. **Topic-to-chapter matching:** the syllabus topic's keywords are compared against each parsed chapter label; the best keyword-overlap match wins, giving a direct `&t=Ns` link straight to that segment.
4. **Multi-topic detection:** after matching all topics in a unit, SyllabuSync groups results by video ID — if the same video was the best match for more than one topic, it's surfaced as an "efficient pick" covering multiple topics at once.

## What's Next (Roadmap)
- Rank and show 2-3 alternative videos per topic, not just the top one
- OCR/PDF upload to auto-extract topics from an actual syllabus PDF instead of manual pasting
- Community-contributed corrections when a chapter match is wrong
- Expand sources beyond YouTube (NPTEL, university OCW content)

## Team
Built solo for HackDevengers 2.0 within the 24-hour hackathon window, based on a real problem described by a Tier-3 college student.
