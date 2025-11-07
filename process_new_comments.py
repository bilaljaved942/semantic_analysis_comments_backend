import os
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv
from sentiment_model import analyze_comment  # import your existing NLP pipeline

# -------------------------------------
# 🔑 Load environment variables
# -------------------------------------
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

# -------------------------------------
# 🧠 Connect to PostgreSQL
# -------------------------------------
try:
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    cursor = conn.cursor()
    print("✅ Connected to PostgreSQL successfully.")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    exit()

# -------------------------------------
# 📥 Step 1: Get the most recent video_id
# -------------------------------------
cursor.execute("SELECT video_id FROM comments ORDER BY id DESC LIMIT 1;")
latest_video_id = cursor.fetchone()[0]

print(f"\n🎥 Latest video_id detected: {latest_video_id}")

# -------------------------------------
# 📤 Step 2: Fetch unprocessed comments for that video
# -------------------------------------
cursor.execute("""
    SELECT id, text FROM comments 
    WHERE video_id = %s AND (processed IS NULL OR processed = FALSE);
""", (latest_video_id,))

rows = cursor.fetchall()
print(f"📝 Found {len(rows)} new comments for video: {latest_video_id}")

if not rows:
    print("✅ No new comments to process. Exiting...")
    cursor.close()
    conn.close()
    exit()

# -------------------------------------
# 🧮 Step 3: Run NLP pipeline and update DB
# -------------------------------------
for comment_id, text in rows:
    try:
        result = analyze_comment(text)

        cursor.execute("""
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
            result["sentiment"],
            result["sentiment_score"],
            result["emotion"],
            result["emotion_score"],
            Json(result["keywords"]),  # ✅ FIX: safely store JSON list
            result["comment_type"],
            comment_id
        ))

        conn.commit()
        print(f"✅ Processed comment ID {comment_id}")

    except Exception as e:
        print(f"⚠️ Error processing comment ID {comment_id}: {e}")

# -------------------------------------
# 📊 Step 4: Summary report
# -------------------------------------
cursor.execute("""
    SELECT sentiment, COUNT(*) 
    FROM comments 
    WHERE video_id = %s 
    GROUP BY sentiment;
""", (latest_video_id,))

sentiment_summary = cursor.fetchall()
print("\n📈 Sentiment Summary for this Video:")
for sentiment, count in sentiment_summary:
    print(f"   {sentiment:<10} → {count} comments")

# -------------------------------------
# ✅ Step 5: Close connection
# -------------------------------------
cursor.close()
conn.close()

print(f"\n🎉 All new comments for video {latest_video_id} have been processed and updated in DB.")
