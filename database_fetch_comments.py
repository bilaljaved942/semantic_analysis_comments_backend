import os
import psycopg2
import json
from dotenv import load_dotenv

# ------------------------------
# 🔑 Load environment variables
# ------------------------------
load_dotenv()

# ------------------------------
# 🧠 Connect to PostgreSQL
# ------------------------------
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS")
)
cursor = conn.cursor()

# ------------------------------
# 📊 Fetch comments
# ------------------------------
cursor.execute("SELECT COUNT(*) FROM comments;")
count = cursor.fetchone()[0]

cursor.execute("SELECT author, text, like_count, published_at FROM comments;")
records = cursor.fetchall()

# Convert to list of dicts
data = []
for r in records:
    data.append({
        "author": r[0],
        "text": r[1],
        "like_count": r[2],
        "published_at": str(r[3])
    })

# Include total count
output = {
    "total_comments": count,
    "sample_comments": data
}

# ------------------------------
# 💾 Save as JSON file
# ------------------------------
output_path = "comments_sample1.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=4, ensure_ascii=False)

print(f"✅ Exported {len(data)} comments (of total {count}) to {output_path}")

# ------------------------------
# 🔚 Cleanup
# ------------------------------
cursor.close()
conn.close()
