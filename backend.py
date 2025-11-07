import os
import psycopg2
from googleapiclient.discovery import build
from dotenv import load_dotenv

# ---------------------------------
# 🔑 Load Environment Variables
# ---------------------------------
load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

# ---------------------------------
# 🧠 Setup Connections
# ---------------------------------
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS
)
cursor = conn.cursor()

# ---------------------------------
# 📥 Fetch Comments Function
# ---------------------------------
def fetch_youtube_comments(video_id, max_results=100):
    """
    Fetch all top-level YouTube comments for a given video_id.
    """
    comments = []
    next_page_token = None

    while True:
        response = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_results,
            pageToken=next_page_token,
            textFormat="plainText"
        ).execute()

        for item in response.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            comment = {
                "video_id": video_id,
                "comment_id": item["id"],
                "author": snippet.get("authorDisplayName"),
                "text": snippet.get("textDisplay"),
                "like_count": snippet.get("likeCount", 0),
                "published_at": snippet.get("publishedAt"),
                "parent_id": None
            }
            comments.append(comment)

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return comments

# ---------------------------------
# 💾 Save Comments to PostgreSQL
# ---------------------------------
def save_comments_to_db(comments):
    insert_query = """
    INSERT INTO comments 
    (video_id, comment_id, author, text, like_count, published_at, parent_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (comment_id) DO NOTHING;
    """
    for c in comments:
        cursor.execute(insert_query, (
            c["video_id"],
            c["comment_id"],
            c["author"],
            c["text"],
            c["like_count"],
            c["published_at"],
            c["parent_id"]
        ))
    conn.commit()
    print(f"✅ Inserted {len(comments)} comments into PostgreSQL.")

# ---------------------------------
# 🧪 Example Run
# ---------------------------------
if __name__ == "__main__":
    video_url = input("Enter YouTube video URL: ").strip()
    video_id = video_url.split("v=")[-1].split("&")[0]

    print(f"\n📥 Fetching comments for Video ID: {video_id}")
    comments = fetch_youtube_comments(video_id)
    print(f"Fetched {len(comments)} comments")

    save_comments_to_db(comments)

    cursor.close()
    conn.close()
