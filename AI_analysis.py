import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

HF_API_KEY = os.getenv("HUGGING_FACE_API_KEY")
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')


def query_hf_api(model_url, text):
    """Simple function to call Hugging Face API"""
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    data = {"inputs": text}

    response = requests.post(model_url, headers=headers, json=data)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"API Error: {response.status_code}")
        return None


def ask_gemini(prompt):
    """Call Gemini API"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 400
        }
    }

    response = requests.post(url, headers={"Content-Type": "application/json"}, json=payload)

    if response.status_code == 200:
        return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    else:
        print(f"Gemini API Error: {response.status_code}")
        return None


def analyze_checkin(happiness_level, feeling_text):
    """Analyze mood using free Hugging Face models"""

    sentiment_url = "https://api-inference.huggingface.co/models/cardiffnlp/twitter-roberta-base-sentiment-latest"

    # Get sentiment from Hugging Face
    sentiment_result = query_hf_api(sentiment_url, feeling_text)

    if sentiment_result and len(sentiment_result) > 0:
        sentiments = sentiment_result[0]
        best_sentiment = max(sentiments, key=lambda x: x['score'])
        sentiment_label = best_sentiment['label']
        confidence = best_sentiment['score']
    else:
        sentiment_label = "LABEL_1"
        confidence = 0.5

    # Map labels
    sentiment_map = {
        "LABEL_0": "negative",
        "LABEL_1": "neutral",
        "LABEL_2": "positive"
    }
    sentiment_name = sentiment_map.get(sentiment_label, "neutral")

    # Ask Gemini to create summary and recommendation
    prompt = f"""You're a warm, empathetic friend checking in on someone. They just shared how they're feeling.

Their happiness level: {happiness_level}/10
What they said: "{feeling_text}"
Sentiment detected: {sentiment_name} (confidence: {confidence:.2f})

Write them two things:
1. An natural analysis of what they said and the sentiment detected with its confidence level and name
2. A thoughtful suggestion that might help - something specific, not generic advice

Note that the user cannot respond to you so assume that they can only read your advice.

Be real. Be kind. Be human. No bullet points, no formality.

Format exactly like this:
SUMMARY: [your empathetic response]
RECOMMENDATION: [your helpful suggestion]"""

    gemini_response = ask_gemini(prompt)

    if gemini_response:
        # Parse response
        summary = ""
        recommendation = ""

        for line in gemini_response.split('\n'):
            if line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()
            elif line.startswith("RECOMMENDATION:"):
                recommendation = line.replace("RECOMMENDATION:", "").strip()

        return {
            "summary": summary,
            "recommendation": recommendation
        }

    return {
        "summary": "Unable to generate summary",
        "recommendation": "Unable to generate recommendation"
    }


def analyze_stability(checkins):
    """Analyze emotional stability from check-ins"""

    if not checkins:
        return "Stability Score: N/A\nComment: No check-ins available for analysis."

    # Basic stability calculation
    mood_levels = [c['happiness_level'] for c in checkins]
    avg_mood = sum(mood_levels) / len(mood_levels)

    # Calculate how much moods vary
    variance = sum((mood - avg_mood) ** 2 for mood in mood_levels) / len(mood_levels)
    stability_score = max(1, min(10, 10 - variance))

    # Prepare mood history
    mood_history = ", ".join([str(m) for m in mood_levels[:10]])

    # Ask Gemini for insights
    prompt = f"""You're a thoughtful therapist looking at someone's mood journal over time. Do not respond
    to the person

Their stability score: {stability_score:.1f}/10 (10 = very steady, 1 = lots of ups and downs)
Average mood: {avg_mood:.1f}/10
Recent moods: {mood_history}
Total entries: {len(checkins)}

Give them honest, compassionate insights. What patterns do you notice? What might help them? Be specific and encouraging. Write 2-3 sentences like you're talking to them directly."""

    gemini_response = ask_gemini(prompt)

    if gemini_response:
        return f"Stability Score: {stability_score:.1f}/10\nComment: {gemini_response}"

    return f"Stability Score: {stability_score:.1f}/10\nComment: Unable to generate analysis."


# Test function to make sure everything works
def test_api():
    """Test the Hugging Face API connection"""
    print("Testing APIs...")

    if not HF_API_KEY:
        print("No Hugging Face API key found! Add HUGGING_FACE_API_KEY to your .env file")
        return False

    if not GEMINI_API_KEY:
        print("No Gemini API key found! Add GEMINI_API_KEY to your .env file")
        return False

    # Test with simple text
    test_result = analyze_checkin(7, "I had a good day at work today!")
    print("✅ API test successful!")
    print("Sample analysis:", test_result)
    return True


if __name__ == "__main__":
    test_api()
