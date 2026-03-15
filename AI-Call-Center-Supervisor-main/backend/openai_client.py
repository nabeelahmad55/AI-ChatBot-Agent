import os
from openai import OpenAI

# === CONFIGURATION ===
# Load your OpenAI API key from environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

if not OPENAI_API_KEY:
    raise ValueError("❌ Missing OPENAI_API_KEY environment variable")

client = OpenAI(api_key=OPENAI_API_KEY)


# === UTILITIES ===
def clean_ascii(text):
    if text is None:
        return ""
    return text.encode("ascii", "ignore").decode()


def validate_question(response, system_prompt):
    """Ensure the AI output is a single, clean question"""
    if not response:
        return None

    response = response.strip()

    # Remove any prefix the model might add
    if "QUESTION TO ASK:" in response:
        response = response.split("QUESTION TO ASK:")[-1].strip()

    response = response.strip('"').strip("'").strip()

    if not response:
        return None

    # Ensure it ends with a '?'
    if not response.endswith('?'):
        response += '?'

    return response


# === MAIN FUNCTION ===
def chat_with_gpt(messages, model=None, temperature=0.1, max_tokens=80):
    """
    Uses the OpenAI Chat Completions API to generate supervisor questions.
    """
    if model is None:
        model = DEFAULT_MODEL

    # Clean up all text to avoid encoding issues
    for msg in messages:
        msg["content"] = clean_ascii(msg["content"])

    try:
        # Call OpenAI's chat completion API
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        response_text = completion.choices[0].message.content.strip()
        validated = validate_question(response_text, messages[0]["content"])
        return validated

    except Exception as e:
        print(f"❌ OpenAI API error: {e}")
        return None
