import requests
import json
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

HF_API_KEY = os.environ.get("HUGGING_FACE_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")


def query_hf_api(model_url, text):
    """Simple function to call Hugging Face API"""
    if not HF_API_KEY:
        print("❌ HF_API_KEY is None or empty")
        return None

    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    data = {"inputs": text}

    response = requests.post(model_url, headers=headers, json=data)

    print(f"HF status: {response.status_code}")
    print(f"HF response: {response.text[:300]}")

    if response.status_code == 200:
        return response.json()
    else:
        print(f"HF API Error: {response.status_code} - {response.text}")
        return None


def ask_claude(prompt):
    """Call Claude API"""
    if not ANTHROPIC_API_KEY:
        print("❌ ANTHROPIC_API_KEY is None or empty")
        return None

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text.strip()


def analyze_checkin(happiness_level, feeling_text):
    """Analyze mood using Hugging Face emotion model + Claude"""

    sentiment_url = "https://router.huggingface.co/hf-inference/models/j-hartmann/emotion-english-distilroberta-base"

    sentiment_result = query_hf_api(sentiment_url, feeling_text)

    if sentiment_result and len(sentiment_result) > 0:
        sentiments = sentiment_result[0]
        best_sentiment = max(sentiments, key=lambda x: x['score'])
        sentiment_label = best_sentiment['label']
        confidence = best_sentiment['score']
    else:
        sentiment_label = "neutral"
        confidence = 0.5

    prompt = f"""You're a warm, empathetic friend checking in on someone. They just shared how they're feeling.

    Their happiness level: {happiness_level}/10
    What they said: '{feeling_text}'
    Emotion detected: {sentiment_label} (confidence: {confidence:.2f})
    
    Write them two things:
    1. A natural analysis of what they said and the emotion detected with its confidence level
    2. A thoughtful suggestion that might help - something specific, not generic advice
    
    Note that the user cannot respond to you so assume that they can only read your advice.
    
    Be real. Be kind. Be human. No bullet points, no formality.
    
    Format exactly like this:
    SUMMARY: [your empathetic response]
    RECOMMENDATION: [your helpful suggestion]"""

    claude_response = ask_claude(prompt)

    if claude_response:
        summary = ""
        recommendation = ""

        parts = claude_response.split("RECOMMENDATION:")
        if len(parts) == 2:
            recommendation = parts[1].strip()
            summary_part = parts[0].split("SUMMARY:")
            if len(summary_part) == 2:
                summary = summary_part[1].strip()

        if not summary and not recommendation:
            print(f"Warning: Could not parse Claude response:\n{claude_response}")
            return {"summary": claude_response, "recommendation": ""}

        return {"summary": summary, "recommendation": recommendation}

    return {
        "summary": "Unable to generate summary",
        "recommendation": "Unable to generate recommendation"
    }


def analyze_stability(checkins):
    """Analyze emotional stability from check-ins"""

    if not checkins:
        return "Stability Score: N/A\nComment: No check-ins available for analysis."

    mood_levels = [c['happiness_level'] for c in checkins]
    avg_mood = sum(mood_levels) / len(mood_levels)

    variance = sum((mood - avg_mood) ** 2 for mood in mood_levels) / len(mood_levels)
    stability_score = max(1, min(10, 10 - variance))

    mood_history = ", ".join([str(m) for m in mood_levels[:10]])

    prompt = f"""You're a thoughtful therapist looking at someone's mood journal over time.

Their stability score: {stability_score:.1f}/10 (10 = very steady, 1 = lots of ups and downs)
Average mood: {avg_mood:.1f}/10
Recent moods: {mood_history}
Total entries: {len(checkins)}

Give honest, compassionate insights. What patterns do you notice? What might help them? Be specific and encouraging. Write 2-3 sentences talking to them directly."""

    claude_response = ask_claude(prompt)

    if claude_response:
        return f"Stability Score: {stability_score:.1f}/10\nComment: {claude_response}"

    return f"Stability Score: {stability_score:.1f}/10\nComment: Unable to generate analysis."


def test_api():
    """Test all API connections"""
    print("Testing APIs...")

    if not HF_API_KEY:
        print("❌ No HUGGING_FACE_API_KEY found")
        return False

    if not ANTHROPIC_API_KEY:
        print("❌ No ANTHROPIC_API_KEY found")
        return False

    test_result = analyze_checkin(7, "I had a good day at work today!")
    print("✅ API test successful!")
    print("Sample analysis:", test_result)
    return True


if __name__ == "__main__":
    test_api()
