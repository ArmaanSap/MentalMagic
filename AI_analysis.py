import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

HF_API_KEY = os.getenv("HUGGING_FACE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def get_sentiment(text):
    """Get sentiment from Hugging Face"""
    url = "https://api-inference.huggingface.co/models/cardiffnlp/twitter-roberta-base-sentiment-latest"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    response = requests.post(url, headers=headers, json={"inputs": text})
    
    if response.status_code != 200:
        raise Exception(f"Sentiment analysis failed: {response.status_code}")
    
    results = response.json()[0]
    top_result = max(results, key=lambda x: x['score'])
    
    sentiment_map = {
        "LABEL_0": "negative",
        "LABEL_1": "neutral", 
        "LABEL_2": "positive"
    }
    
    return {
        "feeling": sentiment_map[top_result['label']],
        "confidence": top_result['score']
    }


def ask_gemini(prompt):
    """Talk to Gemini"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 400
        }
    }
    
    response = requests.post(url, headers={"Content-Type": "application/json"}, json=payload)
    
    if response.status_code != 200:
        raise Exception(f"Gemini failed: {response.status_code} - {response.text}")
    
    return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()


def analyze_checkin(happiness_level, feeling_text):
    """Understand how someone's feeling today"""
    
    sentiment = get_sentiment(feeling_text)
    
    prompt = f"""You're a warm, empathetic friend checking in on someone. They just shared how they're feeling.

Their happiness level: {happiness_level}/10
What they said: "{feeling_text}"
AI detected: {sentiment['feeling']} emotions (I'm {sentiment['confidence']:.0%} sure)

Write them two things:
1. A natural, caring response that shows you really heard them (like a text from a close friend)
2. A thoughtful suggestion that might help - something specific, not generic advice

Be real. Be kind. Be human. No bullet points, no formality.

Format exactly like this:
SUMMARY: [your empathetic response]
RECOMMENDATION: [your helpful suggestion]"""

    response = ask_gemini(prompt)
    
    # Parse Gemini's response
    summary = ""
    recommendation = ""
    
    for line in response.split('\n'):
        if line.startswith("SUMMARY:"):
            summary = line.replace("SUMMARY:", "").strip()
        elif line.startswith("RECOMMENDATION:"):
            recommendation = line.replace("RECOMMENDATION:", "").strip()
    
    return {
        "summary": summary,
        "recommendation": recommendation,
        "sentiment": sentiment['feeling'],
        "confidence": sentiment['confidence']
    }


def analyze_stability(checkins):
    """See how someone's mood has been over time"""
    
    if not checkins:
        raise Exception("Need at least one check-in to analyze stability")
    
    moods = [c['happiness_level'] for c in checkins]
    avg = sum(moods) / len(moods)
    variance = sum((m - avg) ** 2 for m in moods) / len(moods)
    stability = max(1, min(10, 10 - variance))
    
    recent = moods[:5]
    mood_story = ", ".join(str(m) for m in moods[:10])
    
    prompt = f"""You're a thoughtful therapist looking at someone's mood journal over time.

Their stability score: {stability:.1f}/10 (10 = very steady, 1 = lots of ups and downs)
Average mood: {avg:.1f}/10
Recent moods: {mood_story}
Total entries: {len(checkins)}

Give them honest, compassionate insights. What patterns do you notice? What might help them? Be specific and encouraging. Write 2-3 sentences like you're talking to them directly."""

    insight = ask_gemini(prompt)
    
    return f"Stability Score: {stability:.1f}/10\n\n{insight}"


def test_connection():
    """Make sure everything's working"""
    
    print("🔍 Checking API connections...\n")
    
    if not HF_API_KEY:
        print(" Missing HUGGING_FACE_API_KEY in render file")
        return False
    
    if not GEMINI_API_KEY:
        print(" Missing GEMINI_API_KEY in render file")
        return False
    
    print("Testing with: 'Had a really productive day at work!'\n")
    
    result = analyze_checkin(7, "Had a really productive day at work!")
    
    print("✨ It works!\n")
    print(f"💭 {result['summary']}\n")
    print(f"💡 {result['recommendation']}\n")
    print(f"📊 Detected {result['sentiment']} sentiment ({result['confidence']:.0%} confidence)")
    
    return True


if __name__ == "__main__":
    test_connection()
