from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import re

# Import your original file here
from res import (
    BOOK_APPOINTMENT_PROMPT,
    RESCHEDULE_PROMPT,
    CANCEL_PROMPT,
    ask_ollama,
    extract_book_fields,
    extract_reschedule_fields,
    extract_cancel_fields,
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
    get_available_slots
)

app = Flask(__name__)
CORS(app)

# Track session history in memory (you can later use DB/Redis if needed)
SESSION_HISTORY = {}

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_input = data.get("content", "")
    session_id = data.get("session_id", "default")

    # Default to booking if not yet detected (optional enhancement: detect intent)
    action = data.get("intent", "book")

    # Create or update chat history
    history = SESSION_HISTORY.get(session_id, [])

    # Select prompt and logic based on action
    if action == "book":
        prompt = BOOK_APPOINTMENT_PROMPT
        extractor = extract_book_fields
        handler = book_appointment
    elif action == "cancel":
        prompt = CANCEL_PROMPT
        extractor = extract_cancel_fields
        handler = cancel_appointment
    elif action == "reschedule":
        prompt = RESCHEDULE_PROMPT
        extractor = extract_reschedule_fields
        handler = reschedule_appointment
    else:
        return jsonify({"response": "❌ Unknown intent."})

    history.append({"role": "user", "content": user_input})
    assistant_response = ask_ollama(prompt, history)

    # Add assistant reply to history unless it's final
    if "all details received:" not in assistant_response.lower():
        history.append({"role": "assistant", "content": assistant_response})
        SESSION_HISTORY[session_id] = history
        return jsonify({"response": assistant_response})

    # Final step: extract fields and call DB handler
    try:
        data = extractor(assistant_response)
        handler(**data)
        del SESSION_HISTORY[session_id]  # Clear session after processing
        return jsonify({"response": assistant_response})
    except Exception as e:
        return jsonify({"response": f"❌ Failed to process: {str(e)}"})

if __name__ == "__main__":
    app.run(port=8000)
