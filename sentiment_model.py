import re
import emoji
from langdetect import detect
from transformers import pipeline
from keybert import KeyBERT

# ------------------------------
# 🧹 Text Preprocessing Function
# ------------------------------
def clean_text(text):
    text = text.lower()
    text = re.sub(r'http\S+|www\S+', '', text)           # remove URLs
    text = re.sub(r'[@#]\S+', '', text)                  # remove mentions/hashtags
    text = emoji.demojize(text, delimiters=(" ", " "))   # convert emojis to words
    text = re.sub(r'[^a-zA-Z0-9\s.,!?]', ' ', text)      # keep only basic chars
    text = re.sub(r'(.)\1{2,}', r'\1\1', text)           # normalize repeating chars
    text = re.sub(r'\s+', ' ', text).strip()             # remove extra spaces
    return text

# ------------------------------
# 🚀 Load Models
# ------------------------------
translator = pipeline("translation", model="Helsinki-NLP/opus-mt-hi-en")
sentiment_analyzer = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment-latest")
emotion_analyzer = pipeline("text-classification", 
                            model="j-hartmann/emotion-english-distilroberta-base", 
                            top_k=1)
kw_model = KeyBERT()

# ------------------------------
# 🧩 Comment Category Classification
# ------------------------------
def classify_comment_type(text):
    text = text.lower()
    if "?" in text:
        return "Question"
    elif any(word in text for word in ["please", "suggest", "can you", "should i"]):
        return "Suggestion"
    elif any(word in text for word in ["love", "awesome", "great", "amazing", "thanks", "thank you", "nice"]):
        return "Praise"
    elif any(word in text for word in ["bad", "worst", "hate", "terrible", "dislike", "boring"]):
        return "Criticism"
    elif any(word in text for word in ["subscribe", "channel", "follow", "check my"]):
        return "Spam/Promotion"
    else:
        return "General"

# ------------------------------
# 🧠 Full Analysis Function
# ------------------------------
def analyze_comment(text):
    cleaned = clean_text(text)
    
    # Detect language
    try:
        lang = detect(cleaned)
    except:
        lang = "en"
    
    # Translate if Hindi or Urdu
    if lang in ["hi", "ur"]:
        translated = translator(cleaned)[0]['translation_text']
    else:
        translated = cleaned
    
    # Sentiment
    sentiment = sentiment_analyzer(translated)[0]
    
    # Emotion
    emotion_result = emotion_analyzer(translated)
    emotion = emotion_result[0][0] if isinstance(emotion_result[0], list) else emotion_result[0]
    
    # Keywords
    keywords = [kw for kw, score in kw_model.extract_keywords(translated, keyphrase_ngram_range=(1, 2), stop_words='english', top_n=5)]
    
    # Comment Type
    comment_type = classify_comment_type(translated)
    
    # Return structured output
    return {
        "original": text,
        "cleaned": cleaned,
        "language": lang,
        "translated": translated,
        "sentiment": sentiment["label"],
        "sentiment_score": round(sentiment["score"], 3),
        "emotion": emotion["label"],
        "emotion_score": round(emotion["score"], 3),
        "keywords": keywords,
        "comment_type": comment_type
    }

# ------------------------------
# 🧪 Example Run
# ------------------------------
text = "Bhai video mast tha yaar 😍 please make one on thumbnail editing too!"
result = analyze_comment(text)

print("\n🧠 NLP Analysis Result:")
for k, v in result.items():
    print(f"{k:18}: {v}")
