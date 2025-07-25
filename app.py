import re
from datetime import datetime
from ollama_agent import call_ollama
from database import (
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
    get_available_slots
)

def normalize_date(date_str):
    try:
        date_str = re.sub(r"(st|nd|rd|th)", "", date_str)
        return datetime.strptime(date_str.strip(), "%d %B %Y").strftime("%Y-%m-%d")
    except:
        try:
            return datetime.strptime(date_str.strip(), "%Y-%m-%d").strftime("%Y-%m-%d")
        except:
            return None

def normalize_time(time_str):
    try:
        return datetime.strptime(time_str.strip().upper(), "%I:%M %p").strftime("%H:%M:%S")
    except:
        return None

print("🦷 Welcome to NaturalPrompt - Dentist Assistant")
intent = input("👉 What would you like to do? (book / cancel / reschedule): ").strip().lower()
if intent not in ["book", "cancel", "reschedule"]:
    print("❌ Invalid option.")
    exit()

chat_history = []
info = {}

while True:
    print("📦 Current info:", info)
    user_input = input("🧑 You: ")
    if user_input.lower() in ["exit", "quit"]:
        break

    bot_reply = call_ollama(user_input, chat_history, intent)
    print("🤖 Bot:", bot_reply)
    chat_history.append({"user": user_input, "bot": bot_reply})

    # --- Extract Fields ---
    if intent == "book":
        match = re.search(r"Name:\s*(.+)", bot_reply, re.IGNORECASE)
        if match: info["name"] = match.group(1).strip()

        match = re.search(r"Email:\s*(.+)", bot_reply, re.IGNORECASE)
        if match: info["email"] = match.group(1).strip()

        match = re.search(r"Date:\s*(\d{4}-\d{2}-\d{2})", bot_reply)
        if match: info["date"] = normalize_date(match.group(1).strip())

        match = re.search(r"Time:\s*([0-9]{1,2}:[0-9]{2}\s*[APMapm]{2})", bot_reply)
        if match: info["time"] = normalize_time(match.group(1).strip())

        if all(k in info for k in ["name", "email", "date", "time"]):
            available = get_available_slots(info["date"])
            print("🕐 Available:", available)
            print("🔍 Requested time:", info["time"])
            if info["time"] in available:
                print(f"📌 Booking {info['name']}, {info['email']}, {info['date']}, {info['time']}")
                success = book_appointment(info["name"], info["email"], info["date"], info["time"])
                if success:
                    print(f"✅ Successfully booked for {info['name']} on {info['date']} at {info['time']}")
                else:
                    print("⚠️ Could not book. Please try again.")
            else:
                if available:
                    pretty = [datetime.strptime(s, "%H:%M:%S").strftime("%I:%M %p") for s in available]
                    print(f"⛔ Slot taken. Available slots on {info['date']}: {', '.join(pretty)}")
                else:
                    print("🚫 No slots available on this date.")
            break

    elif intent == "cancel":
        match = re.search(r"Name:\s*(.+)", bot_reply, re.IGNORECASE)
        if match: info["name"] = match.group(1).strip()

        match = re.search(r"Email:\s*(.+)", bot_reply, re.IGNORECASE)
        if match: info["email"] = match.group(1).strip()

        match = re.search(r"Date:\s*(\d{4}-\d{2}-\d{2})", bot_reply)
        if match: info["date"] = normalize_date(match.group(1).strip())

        match = re.search(r"Time:\s*([0-9]{1,2}:[0-9]{2}\s*[APMapm]{2})", bot_reply)
        if match: info["time"] = normalize_time(match.group(1).strip())

        if all(k in info for k in ["name", "email", "date", "time"]):
            success = cancel_appointment(info["name"], info["email"], info["date"], info["time"])
            print("✅ Appointment cancelled." if success else "❌ Appointment not found.")
            break

    elif intent == "reschedule":
        for field in ["name", "email", "old_date", "old_time", "new_date", "new_time"]:
            if "old_date" in field or "new_date" in field:
                pattern = r"Old Date:\s*(\d{4}-\d{2}-\d{2})" if "old" in field else r"New Date:\s*(\d{4}-\d{2}-\d{2})"
                match = re.search(pattern, bot_reply)
                if match:
                    info[field] = normalize_date(match.group(1).strip())
            elif "old_time" in field or "new_time" in field:
                pattern = r"Old Time:\s*([0-9]{1,2}:[0-9]{2}\s*[APMapm]{2})" if "old" in field else r"New Time:\s*([0-9]{1,2}:[0-9]{2}\s*[APMapm]{2})"
                match = re.search(pattern, bot_reply)
                if match:
                    info[field] = normalize_time(match.group(1).strip())
            else:
                match = re.search(fr"{field.capitalize()}:\s*(.+)", bot_reply)
                if match:
                    info[field] = match.group(1).strip()

        if all(k in info for k in ["name", "email", "old_date", "old_time", "new_date", "new_time"]):
            result = reschedule_appointment(
                info["name"], info["email"],
                info["old_date"], info["old_time"],
                info["new_date"], info["new_time"]
            )
            if result == "success":
                print("✅ Appointment rescheduled.")
            elif result == "not_found":
                print("❌ Old appointment not found.")
            else:
                available = get_available_slots(info["new_date"])
                pretty = [datetime.strptime(s, "%H:%M:%S").strftime("%I:%M %p") for s in available]
                print(f"⛔ New slot taken. Available on {info['new_date']}: {', '.join(pretty)}")
            break
