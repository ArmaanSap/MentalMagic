import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

# Your free Hugging Face API key
HF_API_KEY = os.getenv("HUGGING_FACE_API_KEY")


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


def analyze_checkin(happiness_level, feeling_text):
    """Analyze mood using free Hugging Face models"""

    # Use free sentiment analysis model
    sentiment_url = "https://api-inference.huggingface.co/models/cardiffnlp/twitter-roberta-base-sentiment-latest"

    try:
        # Get sentiment from Hugging Face
        sentiment_result = query_hf_api(sentiment_url, feeling_text)

        if sentiment_result and len(sentiment_result) > 0:
            # Parse sentiment
            sentiments = sentiment_result[0]
            best_sentiment = max(sentiments, key=lambda x: x['score'])
            sentiment_label = best_sentiment['label']
            confidence = best_sentiment['score']
        else:
            sentiment_label = "NEUTRAL"
            confidence = 0.5

        # Create summary based on sentiment + happiness level
        if sentiment_label == "LABEL_2" and happiness_level >= 7:  # Positive
            summary = f"You're feeling quite positive today with good energy and a {happiness_level}/10 happiness level."
        elif sentiment_label == "LABEL_0" and happiness_level <= 4:  # Negative
            summary = f"You seem to be having a challenging day with a {happiness_level}/10 happiness level."
        else:
            summary = f"Your mood seems mixed today with a {happiness_level}/10 happiness level."

        # Generate recommendations based on happiness level
        if happiness_level >= 8:
            recommendation = "Great to see you're doing well! Consider journaling about what's working."
        elif happiness_level >= 6:
            recommendation = "You're in a good place. Maybe try something fun or connect with a friend."
        elif happiness_level >= 4:
            recommendation = "Take some time for self-care. A short walk or relaxing music might help."
        else:
            recommendation = "Be gentle with yourself today. Consider reaching out to someone you trust."

        # Add sentiment-specific advice
        if sentiment_label == "LABEL_0":  # Negative
            recommendation += " Remember that difficult feelings are temporary."
        elif sentiment_label == "LABEL_2":  # Positive
            recommendation += " Keep up this positive momentum!"

        return {
            "summary": summary,
            "recommendation": recommendation
        }

    except Exception as e:
        print(f"AI analysis failed: {e}")
        # Fallback to basic analysis
        return create_basic_checkin_analysis(happiness_level, feeling_text)


def create_basic_checkin_analysis(happiness_level, feeling_text):
    """Fallback analysis without AI"""

    if happiness_level >= 8:
        summary = f"You're having a great day with {happiness_level}/10 happiness!"
        recommendation = "Keep up the positive energy and maybe share it with others."
    elif happiness_level >= 6:
        summary = f"You're doing well today with {happiness_level}/10 happiness."
        recommendation = "You're in a good place. Consider doing something you enjoy."
    elif happiness_level >= 4:
        summary = f"Your mood is moderate today at {happiness_level}/10."
        recommendation = "Take some time for self-care and relaxation."
    else:
        summary = f"You're having a tough day with {happiness_level}/10 happiness."
        recommendation = "Be kind to yourself and consider talking to someone you trust."

    return {
        "summary": summary,
        "recommendation": recommendation
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

    # Generate comment based on patterns
    recent_moods = mood_levels[:5]  # Last 5 entries
    if len(recent_moods) >= 3:
        recent_avg = sum(recent_moods) / len(recent_moods)
        if recent_avg > avg_mood + 1:
            trend = "Your mood has been improving recently!"
        elif recent_avg < avg_mood - 1:
            trend = "Your mood has been declining recently."
        else:
            trend = "Your mood has been fairly consistent."
    else:
        trend = "Not enough recent data for trend analysis."

    # Create detailed comment
    if stability_score >= 8:
        comment = f"Excellent emotional stability! {trend} Average mood: {avg_mood:.1f}/10"
    elif stability_score >= 6:
        comment = f"Good stability with some natural fluctuations. {trend}"
    elif stability_score >= 4:
        comment = f"Moderate mood swings. {trend} Consider tracking what affects your mood."
    else:
        comment = f"Significant mood variations detected. {trend} Consider speaking with a counselor."

    return f"Stability Score: {stability_score:.1f}/10\nComment: {comment}"


# Test function to make sure everything works
def test_api():
    """Test the Hugging Face API connection"""
    print("Testing Hugging Face API...")

    if not HF_API_KEY:
        print("No API key found! Add HUGGING_FACE_API_KEY to your .env file")
        return False

    # Test with simple text
    test_result = analyze_checkin(7, "I had a good day at work today!")
    print("✅ API test successful!")
    print("Sample analysis:", test_result)
    return True


if __name__ == "__main__":
    test_api()