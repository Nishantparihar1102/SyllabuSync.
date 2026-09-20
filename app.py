"""
SyllabuSync — Find the exact lecture segment for YOUR syllabus topic
Built for HackDevengers 2.0 (Open Innovation Hackathon)

Flask backend + custom HTML/CSS/JS frontend (templates/index.html,
static/css/style.css, static/js/main.js).

See README.md for the full problem/solution writeup.
"""

import sqlite3
from datetime import datetime
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv(override=True)

from flask import Flask, render_template, request, jsonify, g

from syllabus_presets import PRESETS
from youtube_helper import find_best_match, get_api_key

DB_PATH = "syllabusync.db"
app = Flask(__name__)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student TEXT, subject TEXT, unit_label TEXT, created_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS topic_videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unit_id INTEGER, topic TEXT, video_id TEXT, title TEXT,
        channel TEXT, url TEXT, timestamp_seconds INTEGER,
        chapter_label TEXT, view_count INTEGER, demo INTEGER, watched INTEGER DEFAULT 0
    )""")
    conn.commit()
    conn.close()


def fmt_time(seconds: int) -> str:
    m, s = divmod(int(seconds or 0), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ---------------------------------------------------------------- PAGES
@app.route("/")
def index():
    return render_template(
        "index.html",
        presets=PRESETS,
        demo_mode=(get_api_key() is None),
    )


# ---------------------------------------------------------------- API
@app.route("/api/find_topics", methods=["POST"])
def api_find_topics():
    data = request.get_json(force=True)
    student = (data.get("student") or "Student").strip()
    subject = (data.get("subject") or "").strip()
    unit_label = (data.get("unit_label") or "Untitled unit").strip()
    topics = [t.strip() for t in data.get("topics", []) if t.strip()]

    if not subject or not topics:
        return jsonify({"error": "subject and at least one topic are required"}), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO units (student,subject,unit_label,created_at) VALUES (?,?,?,?)",
        (student, subject, unit_label, datetime.now().isoformat()),
    )
    unit_id = cur.lastrowid

    results = []
    for topic in topics:
        try:
            match = find_best_match(topic, subject)
            db.execute(
                """INSERT INTO topic_videos
                   (unit_id,topic,video_id,title,channel,url,timestamp_seconds,chapter_label,view_count,demo)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (unit_id, topic, match["video_id"], match["title"], match["channel"], match["url"],
                 match["timestamp_seconds"], match.get("chapter_label"), match["view_count"], int(match["demo"])),
            )
            results.append({
                "topic": topic,
                "video_id": match["video_id"],
                "title": match["title"],
                "channel": match["channel"],
                "url": match["url"],
                "timestamp": fmt_time(match["timestamp_seconds"]),
                "view_count": match["view_count"],
                "demo": match["demo"],
                "watched": False,
                "error": None
            })
        except Exception as e:
            results.append({
                "topic": topic,
                "video_id": None,
                "title": "Error finding topic",
                "channel": "System",
                "url": "#",
                "timestamp": "0:00",
                "view_count": 0,
                "demo": False,
                "watched": False,
                "error": str(e)
            })
    db.commit()

    # detect topics sharing the same best-match video
    by_video = defaultdict(list)
    for r in results:
        by_video[r["video_id"]].append(r["topic"])
    multi_topic_videos = [
        {"video_id": vid, "title": next(r["title"] for r in results if r["video_id"] == vid), "topics": topics_}
        for vid, topics_ in by_video.items() if len(topics_) > 1
    ]

    # attach db row ids so the frontend can mark watched
    rows = db.execute(
        "SELECT id, topic FROM topic_videos WHERE unit_id=?", (unit_id,)
    ).fetchall()
    topic_to_id = {r["topic"]: r["id"] for r in rows}
    for r in results:
        r["id"] = topic_to_id.get(r["topic"])

    return jsonify({
        "unit_id": unit_id,
        "results": results,
        "multi_topic_videos": multi_topic_videos,
        "demo_mode": get_api_key() is None,
    })


@app.route("/api/mark_watched", methods=["POST"])
def api_mark_watched():
    data = request.get_json(force=True)
    topic_video_id = data.get("id")
    watched = bool(data.get("watched"))
    db = get_db()
    db.execute("UPDATE topic_videos SET watched=? WHERE id=?", (int(watched), topic_video_id))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/delete_unit", methods=["POST"])
def api_delete_unit():
    data = request.get_json(force=True)
    unit_id = data.get("unit_id")
    db = get_db()
    # Delete the unit and all associated topics
    db.execute("DELETE FROM topic_videos WHERE unit_id=?", (unit_id,))
    db.execute("DELETE FROM units WHERE id=?", (unit_id,))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/progress")
def api_progress():
    student = request.args.get("student", "Student")
    db = get_db()
    units = db.execute(
        "SELECT * FROM units WHERE student=? ORDER BY created_at DESC", (student,)
    ).fetchall()
    out = []
    for u in units:
        topics = db.execute(
            "SELECT * FROM topic_videos WHERE unit_id=?", (u["id"],)
        ).fetchall()
        total = len(topics)
        watched = sum(1 for t in topics if t["watched"])
        out.append({
            "id": u["id"],
            "subject": u["subject"],
            "unit_label": u["unit_label"],
            "total": total,
            "watched": watched,
            "pct": round((watched / total) * 100) if total else 0,
            "topics": [{"id": t["id"], "topic": t["topic"], "url": t["url"], "title": t["title"], "watched": bool(t["watched"])} for t in topics]
        })
    return jsonify(out)


@app.route("/api/stats")
def api_stats():
    student = request.args.get("student")
    db = get_db()
    if student:
        units = db.execute("SELECT COUNT(*) c FROM units WHERE student=?", (student,)).fetchone()["c"]
        topics = db.execute("SELECT COUNT(*) c FROM topic_videos JOIN units ON topic_videos.unit_id = units.id WHERE units.student=?", (student,)).fetchone()["c"]
        watched = db.execute("SELECT COUNT(*) c FROM topic_videos JOIN units ON topic_videos.unit_id = units.id WHERE units.student=? AND topic_videos.watched=1", (student,)).fetchone()["c"]
    else:
        units = db.execute("SELECT COUNT(*) c FROM units").fetchone()["c"]
        topics = db.execute("SELECT COUNT(*) c FROM topic_videos").fetchone()["c"]
        watched = db.execute("SELECT COUNT(*) c FROM topic_videos WHERE watched=1").fetchone()["c"]
    return jsonify({"units": units, "topics": topics, "watched": watched})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
else:
    init_db()
