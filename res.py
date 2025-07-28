import os, re, requests
from datetime import datetime, timedelta
from database import (
    book_appointment as db_book,
    cancel_appointment as db_cancel,
    reschedule_appointment as db_reschedule,
    get_available_slots
)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3"

# ---- PROMPTS ----
BOOK_APPOINTMENT_PROMPT = """
You are a helpful and structured assistant that books dentist appointments.

 Your task is to collect the following 5 mandatory fields **only once**:
1. Full name
2. Reason for appointment
3. Email address (Valid Email Address)
4. Preferred appointment date (YYYY-MM-DD)
5. Preferred appointment time (HH:MM AM/PM)

 Logic:
- Always check what fields the user has already provided.
- Never ask for the same field again once it's given.
- If multiple fields are missing, ask for ONLY ONE missing field at a time, in this order: name → reason → email → date → time.
- If the user provides multiple fields in one response, extract and save them.
- If the user gives ambiguous or partial data (like just “Monday” or “next week”), ask for proper format again.

 Once all 5 fields are collected, respond with **exactly this format (no more, no less)**:

All details received:
- Name: John Doe
- Email: john@example.com
- Reason: Cleaning
- Date: 2025-07-22
- Time: 10:30 AM

 STRICT RULES:
- Use a colon `:` after “All details received”
- Use a dash `-` to start each detail line
- Do NOT thank the user, explain anything, or say "appointment booked"
- Do NOT skip or reorder fields
- Do NOT include anything else before or after the final 5-line output

 Example:
If the user says:
> Hi, I'm Priya and I need a root canal on July 28th at 2 PM

And hasn't yet provided an email, your next message should be:
> Can you please provide your email address?

 Keep the interaction natural, brief, and respectful. Don't repeat already collected data. Be strict with format.
"""


RESCHEDULE_PROMPT = """You are a helpful assistant responsible for rescheduling dentist appointments.

You MUST collect the following **mandatory details** from the user:
1. Full name
2. Email address (Valid Email Address)
3. Current appointment date (YYYY-MM-DD)
4. Current appointment time (HH:MM AM/PM)
5. New preferred appointment date (YYYY-MM-DD)
6. New preferred appointment time (HH:MM AM/PM)

Once all details are received, respond using **exactly this format**:

All details received:
- Name: Jane Smith
- Email: jane@example.com
- Previous Date: 2025-07-22
- Previous Time: 3:00 PM
- New Date: 2025-07-25
- New Time: 4:30 PM
"""

CANCEL_PROMPT = """You are a helpful assistant that cancels dentist appointments.

You MUST collect the following **mandatory details** from the user:
1. Full name
2. Email address (Valid Email Address)
3. Appointment date (YYYY-MM-DD)
4. Appointment time (HH:MM AM/PM)

Once all fields are collected, respond with the **exact format** below — and **nothing else**:

All details received:
- Name: John Doe
- Email: john@example.com
- Date: 2025-07-22
- Time: 10:30 AM
"""

# ---- API CALL ----
def ask_ollama(prompt, history):
    messages = [{"role": "system", "content": prompt}]
    messages += history
    response = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "stream": False,
        "messages": messages
    })
    return response.json()["message"]["content"]

# ---- TIME NORMALIZER ----
def normalize_time_to_mysql_format(time_str):
    try:
        return datetime.strptime(time_str.strip(), "%I:%M %p").strftime("%H:%M:%S")
    except Exception as e:
        print(f"⚠️ Time parsing failed: {e}")
        return None

# ---- FIELD EXTRACTORS ----
def extract_book_fields(text):
    return {
        "name": re.search(r"Name:\s*(.+)", text).group(1).strip(),
        "email": re.search(r"Email:\s*(.+)", text).group(1).strip(),
        "reason": re.search(r"Reason:\s*(.+)", text).group(1).strip(),
        "date": re.search(r"Date:\s*(\d{4}-\d{2}-\d{2})", text).group(1).strip(),
        "time": re.search(r"Time:\s*(\d{1,2}:\d{2}\s*[APMapm]{2})", text).group(1).strip()
    }

def extract_reschedule_fields(text):
    return {
        "name": re.search(r"Name:\s*(.+)", text).group(1).strip(),
        "email": re.search(r"Email:\s*(.+)", text).group(1).strip(),
        "old_date": re.search(r"Previous Date:\s*(\d{4}-\d{2}-\d{2})", text).group(1).strip(),
        "old_time": re.search(r"Previous Time:\s*(\d{1,2}:\d{2}\s*[APMapm]{2})", text).group(1).strip(),
        "new_date": re.search(r"New Date:\s*(\d{4}-\d{2}-\d{2})", text).group(1).strip(),
        "new_time": re.search(r"New Time:\s*(\d{1,2}:\d{2}\s*[APMapm]{2})", text).group(1).strip()
    }

def extract_cancel_fields(text):
    return {
        "name": re.search(r"Name:\s*(.+)", text).group(1).strip(),
        "email": re.search(r"Email:\s*(.+)", text).group(1).strip(),
        "date": re.search(r"Date:\s*(\d{4}-\d{2}-\d{2})", text).group(1).strip(),
        "time": re.search(r"Time:\s*(\d{1,2}:\d{2}\s*[APMapm]{2})", text).group(1).strip()
    }

# ---- HANDLERS ----
def book_appointment(name, email, reason, date, time):
    time_24 = normalize_time_to_mysql_format(time)
    if not time_24:
        print("❌ Invalid time format.")
        return
    print(f"\n📌 Trying to book slot on {date} at {time_24} for {name}")
    success = db_book(name, email, date, time_24)
    print("✅ Appointment booked successfully." if success else "❌ Slot already booked.")

def cancel_appointment(name, email, date, time):
    time_24 = normalize_time_to_mysql_format(time)
    if not time_24:
        print("❌ Invalid time format.")
        return
    print(f"\n🗑️ Canceling appointment for {name}")
    success = db_cancel(name, email, date, time_24)
    print("✅ Canceled." if success else "❌ No matching appointment.")

def reschedule_appointment(name, email, old_date, old_time, new_date, new_time):
    old_time_24 = normalize_time_to_mysql_format(old_time)
    new_time_24 = normalize_time_to_mysql_format(new_time)
    if not old_time_24 or not new_time_24:
        print("❌ Time format error.")
        return
    print(f"\n🔁 Rescheduling for {name}")
    status = db_reschedule(name, email, old_date, old_time_24, new_date, new_time_24)
    messages = {
        "success": "✅ Rescheduled.",
        "not_found": "❌ No matching appointment.",
        "slot_taken": "❌ New slot is booked."
    }
    print(messages.get(status, "❌ Unknown error."))

# ---- MAIN LOOP ----
while True:
    print("\n🦷 Dentist Assistant")
    action = input("What would you like to do? (book / reschedule / cancel / exit): ").strip().lower()

    if action == "exit":
        print("👋 Goodbye!")
        break
    elif action not in ("book", "reschedule", "cancel"):
        print("❌ Invalid action.")
        continue

    prompt = {
        "book": BOOK_APPOINTMENT_PROMPT,
        "reschedule": RESCHEDULE_PROMPT,
        "cancel": CANCEL_PROMPT
    }[action]
    extractor = {
        "book": extract_book_fields,
        "reschedule": extract_reschedule_fields,
        "cancel": extract_cancel_fields
    }[action]
    handler = {
        "book": book_appointment,
        "reschedule": reschedule_appointment,
        "cancel": cancel_appointment
    }[action]

    history = []
    while True:
        user_msg = input("You: ")
        history.append({"role": "user", "content": user_msg})
        assistant_response = ask_ollama(prompt, history)

        # Check if "All details received" was already printed before
        already_confirmed = any(
            "all details received:" in msg["content"].lower()
            for msg in history if msg["role"] == "assistant"
        )

        # Only print if not already printed OR it's the first time
        if not already_confirmed or "all details received:" in assistant_response.lower():
            print(f"🤖 Assistant: {assistant_response}")

        # Don't add assistant message to history if it's the final confirmation
        if "all details received:" not in assistant_response.lower():
            history.append({"role": "assistant", "content": assistant_response})

        # Once final confirmation is detected, extract and process
        if "all details received:" in assistant_response.lower():
            try:
                data = extractor(assistant_response)
                print("\n📥 Processing your booking...")
                handler(**data)
                break
            except Exception as e:
                print(f"❌ Failed to parse: {e}")
                break


        if action == "book":
            date_match = re.search(r"Date:\s*(\d{4}-\d{2}-\d{2})", assistant_response)
            if date_match:
                entered_date = date_match.group(1).strip()
                slots = get_available_slots(entered_date)
                if slots:
                    print(f"\n📆 Available slots on {entered_date}:")
                    for s in slots:
                        try:
                            print(f"  - {datetime.strptime(s, '%H:%M:%S').strftime('%I:%M %p')}")
                        except ValueError:
                            print(f"  - {s}")
                else:
                    print(f"\n❌ No slots on {entered_date}. Searching future days...")
                    for i in range(1, 5):
                        future_date = (datetime.strptime(entered_date, "%Y-%m-%d") + timedelta(days=i)).strftime("%Y-%m-%d")
                        future_slots = get_available_slots(future_date)
                        if future_slots:
                            print(f"📅 Next available: {future_date}")
                            use_next = input("Use this date? (yes/no): ").strip().lower()
                            if use_next == "yes":
                                history.append({"role": "user", "content": f"My new preferred date is {future_date}"})
                                break

    again = input("\n🔁 Start new session? (yes/no): ").strip().lower()
    if again != "yes":
        print("👋 Goodbye!")
        break
