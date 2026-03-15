# cli_run.py
import requests
import time
import json
import os
from datetime import datetime
from backend.openai_client import chat_with_gpt

BACKEND_BASE = "http://localhost:5000"

# ✅ Load data.json dynamically
DATA_JSON_PATH = os.path.join("data", "data.json")  # Adjust if needed
localData = {}

if os.path.exists(DATA_JSON_PATH):
    with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
        localData = json.load(f)
        print(f"✅ Loaded data.json")
else:
    print("⚠️ data.json NOT FOUND - Continuing without it")


def get_agent_details(agent_name):
    """Return agent details from data.json if name matches"""
    for agent in localData.get("agents", []):
        if agent.get("name", "").lower() == agent_name.lower():
            return agent
    return None


def create_session(agent_name):
    resp = requests.post(f"{BACKEND_BASE}/create_session", json={"agent": agent_name})
    if resp.status_code == 201:
        return resp.json()["id"]
    else:
        print("Failed to create session on backend:", resp.text)
        return None


def push_message(session_id, role, content, ts=None):
    payload = {"role": role, "content": content}
    if ts:
        payload["created_at"] = ts
    resp = requests.post(f"{BACKEND_BASE}/sessions/{session_id}/messages", json=payload)
    if resp.status_code not in (200, 201):
        print("Failed to push message:", resp.status_code, resp.text)


def run_cli():
    agent_name = input("Agent name: ")

    agent_details = get_agent_details(agent_name)
    if not agent_details:
        print(f"❌ Agent '{agent_name}' not found in data.json")
        return

    session_id = create_session(agent_name)
    if not session_id:
        print("Can't continue without backend session.")
        return

    # ✅ Prepare dynamic system prompt with agent's actual data
    schedule = agent_details.get("schedule", {})
    system = agent_details.get("system", {})
    phone = agent_details.get("phone", {})
    agent_disputed = agent_details.get("agent_disputed", {})

    system_prompt = f"""
You are a call center supervisor, reviewing {agent_name}'s edited session during the day.

Shift Date: 10/02/2025

Scheduled Start: {schedule.get('start_time')}
Scheduled End: {schedule.get('end_time')}

System captured Start time: {system.get('start_time')}
System captured End time: {system.get('end_time')}

Phone recorded Start time: {phone.get('start_time')}
Phone recorded End time: {phone.get('end_time')}

Agent's edited start time: {agent_disputed.get('start_time')}
Agent's edited end time: {agent_disputed.get('end_time')}

Review the above times and ask questions for clarification to the agent to get their explanation for the edits.
"""

    now_iso = datetime.utcnow().isoformat()
    push_message(session_id, "system", system_prompt, now_iso)

    gpt_msgs = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Based on actual data.json values above, start with your first question."}
    ]

    while True:
        try:
            assistant = chat_with_gpt(gpt_msgs)
        except Exception as e:
            print("Error calling model:", e)
            return

        print("\nAssistant:\n", assistant)
        push_message(session_id, "assistant", assistant, datetime.utcnow().isoformat())
        gpt_msgs.append({"role": "assistant", "content": assistant})

        reply = input("\nYou: ")
        push_message(session_id, "user", reply, datetime.utcnow().isoformat())
        gpt_msgs.append({"role": "user", "content": reply})

        if reply.lower() in ("done", "exit", "no"):
            print("Session ended.")
            break


if __name__ == "__main__":
    run_cli()
