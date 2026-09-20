"""
Core engine: for a given syllabus topic, find the best matching YouTube
video AND, if the video's description contains timestamped chapters,
the exact timestamp that covers this topic — so the student jumps
straight to the relevant 2-5 minutes instead of scrubbing a 1-4 hour
lecture.

Works in two modes:
- LIVE mode: uses the YouTube Data API v3 (needs a free API key from
  https://console.cloud.google.com — YouTube Data API v3 enabled).
- DEMO mode: if no API key is configured, generates deterministic,
  clearly-labeled sample results so the app is fully demoable offline /
  without a key. Swap in a real key and it works for real.
"""

import os
import re
import hashlib
import requests

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

TIMESTAMP_LINE_RE = re.compile(r'^\W*(?P<time>(?:\d{1,2}:)?\d{1,2}:\d{2})\W+(?P<label>.+)$')

DEMO_CHANNELS = [
    "Gate Smashers", "Neso Academy", "5 Minutes Engineering",
    "Jenny's Lectures CS/IT", "Unacademy", "Apna College",
]

_search_cache = {}  # simple in-process cache: (topic, subject) -> videos list


def get_api_key():
    return os.environ.get("YOUTUBE_API_KEY")


def timestamp_to_seconds(t: str):
    parts = t.split(":")
    try:
        parts = [int(p) for p in parts]
    except ValueError:
        return None
    if len(parts) == 2:
        m, s = parts
        return m * 60 + s
    if len(parts) == 3:
        h, m, s = parts
        return h * 3600 + m * 60 + s
    return None


def parse_chapters(description: str):
    """Extract (seconds, label) chapter markers from a video description."""
    chapters = []
    for line in (description or "").splitlines():
        m = TIMESTAMP_LINE_RE.match(line.strip())
        if m:
            seconds = timestamp_to_seconds(m.group("time"))
            label = m.group("label").strip(" -–:")
            if seconds is not None and label:
                chapters.append((seconds, label))
    return chapters


def _keywords(text: str):
    return set(w.lower() for w in re.findall(r"[a-zA-Z]+", text) if len(w) > 2)


def best_chapter_for_topic(topic: str, chapters: list):
    if not chapters:
        return None
    topic_kw = _keywords(topic)
    best, best_score = None, 0
    for seconds, label in chapters:
        score = len(topic_kw & _keywords(label))
        if score > best_score:
            best_score, best = score, (seconds, label)
    return best if best_score > 0 else None


def _search_youtube(topic: str, subject: str, api_key: str, max_results: int = 5):
    cache_key = (topic, subject)
    if cache_key in _search_cache:
        return _search_cache[cache_key]

    params = {
        "part": "snippet", "q": f"{topic} {subject}", "type": "video",
        "maxResults": max_results, "key": api_key,
    }
    r = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=10)
    r.raise_for_status()
    items = r.json().get("items", [])
    video_ids = [it["id"]["videoId"] for it in items if "videoId" in it.get("id", {})]
    if not video_ids:
        _search_cache[cache_key] = []
        return []
    vparams = {"part": "snippet,statistics", "id": ",".join(video_ids), "key": api_key}
    vr = requests.get(YOUTUBE_VIDEOS_URL, params=vparams, timeout=10)
    vr.raise_for_status()
    videos = vr.json().get("items", [])
    _search_cache[cache_key] = videos
    return videos


def _score_video(topic: str, video: dict) -> float:
    snippet = video.get("snippet", {})
    title, desc = snippet.get("title", ""), snippet.get("description", "")
    topic_kw = _keywords(topic)
    text_kw = _keywords(title) | _keywords(desc[:500])
    overlap = len(topic_kw & text_kw)
    views = int(video.get("statistics", {}).get("viewCount", 0) or 0)
    return overlap * 10 + min(views, 1_000_000) / 100_000  # relevance dominates, views break ties


def find_best_match(topic: str, subject: str) -> dict:
    api_key = get_api_key()
    if not api_key:
        return _demo_result(topic, subject)

    try:
        videos = _search_youtube(topic, subject, api_key)
    except Exception as e:
        raise RuntimeError(f"YouTube API Error: {e}")

    if not videos:
        raise ValueError(f"No results found on YouTube for this topic.")

    ranked = sorted(videos, key=lambda v: _score_video(topic, v), reverse=True)
    top = ranked[0]
    snippet = top.get("snippet", {})
    chapters = parse_chapters(snippet.get("description", ""))
    match = best_chapter_for_topic(topic, chapters)
    seconds, label = match if match else (0, None)

    return {
        "video_id": top["id"],
        "title": snippet.get("title", ""),
        "channel": snippet.get("channelTitle", ""),
        "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url"),
        "url": f"https://www.youtube.com/watch?v={top['id']}&t={seconds}s",
        "timestamp_seconds": seconds,
        "chapter_label": label,
        "view_count": int(top.get("statistics", {}).get("viewCount", 0) or 0),
        "demo": False,
    }


def _demo_result(topic: str, subject: str, note: str = None) -> dict:
    seed = int(hashlib.md5(topic.encode()).hexdigest(), 16)
    channel = DEMO_CHANNELS[seed % len(DEMO_CHANNELS)]
    minutes = 3 + (seed % 25)
    seconds = minutes * 60
    # Deterministic "shared video" simulation: some topics land on the same
    # demo video id, to illustrate the multi-topic-per-lecture detection.
    bucket = seed % 7
    return {
        "video_id": f"demo{bucket}",
        "title": f"{subject}: Full Concept Playlist (Demo)",
        "channel": channel,
        "thumbnail": None,
        "url": "#",
        "timestamp_seconds": seconds,
        "chapter_label": topic,
        "view_count": 5000 + (seed % 90000),
        "demo": True,
        "note": note,
    }
