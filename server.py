# backend/server.py
import os
import json
import psycopg2
from psycopg2.extras import Json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.db_insertion import fetch_youtube_comments, save_comments_to_db
from backend.sentiment_model import analyze_comment

load_dotenv()

# ---------------------------
# FastAPI App Initialization
# ---------------------------
app = FastAPI(title="CreatorInsight API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Database Connection
# ---------------------------
def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "creator_insight"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS")
    )

# ---------------------------
# Request Models
# ---------------------------
class VideoURL(BaseModel):
    youtube_url: str = None
    video_id: str = None

# ---------------------------
# Root endpoint (optional)
# ---------------------------
@app.get("/")
def root():
    return {"message": "CreatorInsight API is running. Use /docs for Swagger UI."}

# ---------------------------
# Get sentiment summary
# ---------------------------
@app.get("/videos/{video_id}/insights")
def video_insights(video_id: str):
    conn = get_conn()
    cur = conn.cursor()
    query = """
        SELECT sentiment, COUNT(*) FROM comments
        WHERE video_id = %s
        GROUP BY sentiment;
    """
    cur.execute(query, (video_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"video_id": video_id, "sentiment_counts": dict(rows)}

# ---------------------------
# Get comments for a video
# ---------------------------
@app.get("/videos/{video_id}/comments")
def video_comments(video_id: str, limit: int = 50):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, author, text, sentiment, emotion, keywords "
        "FROM comments WHERE video_id = %s ORDER BY id DESC LIMIT %s",
        (video_id, limit)
    )
    records = cur.fetchall()
    cur.close()
    conn.close()

    data = []
    for id_, author, text, sentiment, emotion, keywords in records:
        data.append({
            "id": id_,
            "author": author,
            "text": text,
            "sentiment": sentiment,
            "emotion": emotion,
            "keywords": keywords
        })
    return {"video_id": video_id, "comments": data}

# ---------------------------
# Process a video
# ---------------------------
@app.post("/videos/process")
def process_video(payload: VideoURL):
    """Fetch YouTube comments, store in DB, run NLP, return summary."""

    # ---------------------------
    # Extract video_id
    # ---------------------------
    vid = payload.video_id
    if not vid and payload.youtube_url:
        url = payload.youtube_url.strip()
        if "v=" in url:
            vid = url.split("v=")[-1].split("&")[0]
        elif "youtu.be/" in url:
            vid = url.split("youtu.be/")[-1].split("?")[0]
        else:
            raise HTTPException(status_code=400, detail="Could not parse video_id from URL")

    if not vid:
        raise HTTPException(status_code=400, detail="Provide either video_id or youtube_url")

    # ---------------------------
    # Step 1: Fetch comments
    # ---------------------------
    try:
        comments = fetch_youtube_comments(vid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch comments: {e}")

    inserted = 0
    try:
        if comments:
            save_comments_to_db(comments)
            inserted = len(comments)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save comments to DB: {e}")

    # ---------------------------
    # Step 2: Process comments
    # ---------------------------
    processed_count = 0
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, text FROM comments WHERE video_id = %s AND (processed IS NULL OR processed = FALSE)",
            (vid,)
        )
        rows = cur.fetchall()

        for comment_id, text in rows:
            try:
                result = analyze_comment(text)
                cur.execute("""
                    UPDATE comments
                    SET processed = TRUE,
                        sentiment = %s,
                        sentiment_score = %s,
                        emotion = %s,
                        emotion_score = %s,
                        keywords = %s,
                        comment_type = %s
                    WHERE id = %s;
                """, (
                    result.get("sentiment"),
                    result.get("sentiment_score"),
                    result.get("emotion"),
                    result.get("emotion_score"),
                    Json(result.get("keywords")),
                    result.get("comment_type"),
                    comment_id
                ))
                conn.commit()
                processed_count += 1
            except Exception as e:
                print(f"Error processing comment {comment_id}: {e}")

        # Build sentiment summary
        cur.execute(
            "SELECT sentiment, COUNT(*) FROM comments WHERE video_id = %s GROUP BY sentiment",
            (vid,)
        )
        sentiment_rows = cur.fetchall()
        sentiment_counts = dict(sentiment_rows)

        cur.close()
        conn.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed during NLP processing: {e}")

    return {
        "video_id": vid,
        "inserted_comments": inserted,
        "processed_comments": processed_count,
        "sentiment_counts": sentiment_counts
    }
