# OpenAI Call Center Chatbot POC

This POC demonstrates an OpenAI-powered chatbot that:

- Loads agent shift/session data
- Uses OpenAI GPT to generate clarifying questions and follow-ups
- Accepts agent replies (WebSocket / CLI)
- Stores conversation and resolved session facts in a local SQLite DB

## Quickstart

1. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.
2. Create virtualenv and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate   # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
3. Run the FastAPI app:
   ```bash
   uvicorn app:app --reload
   ```
4. Open `http://localhost:8000` in your browser and start chat.

## CLI mode

Run `python cli_run.py` for a simple terminal experience.

