import requests
from prompts import BOOKING_PROMPT, CANCELLATION_PROMPT, RESCHEDULING_PROMPT

def call_ollama(message, history, intent):
    prompt = {
        "book": BOOKING_PROMPT,
        "cancel": CANCELLATION_PROMPT,
        "reschedule": RESCHEDULING_PROMPT
    }[intent]

    chat_context = "\n".join([f"User: {x['user']}\nAssistant: {x['bot']}" for x in history])
    full_prompt = f"{prompt}\n\n{chat_context}\nUser: {message}\nAssistant:"

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3",
            "prompt": full_prompt,
            "stream": False
        }
    )

    return response.json()["response"].strip()
