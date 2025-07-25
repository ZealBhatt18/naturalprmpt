# File: database.py
import mysql.connector

# --- DB Setup ---
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Zeal@94269",
    database="appointments_db"
)
cursor = conn.cursor()

def book_appointment(name, email, date, time):
    print(f"📌 Booking {name}, {email}, {date}, {time}")
    cursor.execute("SELECT * FROM natappoit WHERE date=%s AND time=%s", (date, time))
    if cursor.fetchone():
        return False
    cursor.execute("INSERT INTO natappoit (name, email, date, time) VALUES (%s, %s, %s, %s)", (name, email, date, time))
    conn.commit()
    return True

def cancel_appointment(name, email, date, time):
    cursor.execute("DELETE FROM natappoit WHERE name=%s AND email=%s AND date=%s AND time=%s",
                   (name, email, date, time))
    conn.commit()
    return cursor.rowcount > 0

def reschedule_appointment(name, email, old_date, old_time, new_date, new_time):
    cursor.execute("SELECT * FROM natappoit WHERE name=%s AND email=%s AND date=%s AND time=%s",
                   (name, email, old_date, old_time))
    if not cursor.fetchone():
        return "not_found"
    cursor.execute("SELECT * FROM natappoit WHERE date=%s AND time=%s", (new_date, new_time))
    if cursor.fetchone():
        return "slot_taken"
    cursor.execute("UPDATE natappoit SET date=%s, time=%s WHERE name=%s AND email=%s AND date=%s AND time=%s",
                   (new_date, new_time, name, email, old_date, old_time))
    conn.commit()
    return "success"

def get_available_slots(date):
    all_slots = ["09:00:00", "10:00:00", "11:00:00", "12:00:00", "14:00:00", "15:00:00", "16:00:00", "17:00:00"]
    cursor.execute("SELECT time FROM natappoit WHERE date=%s", (date,))
    booked = [row[0] for row in cursor.fetchall()]
    return [slot for slot in all_slots if slot not in booked]
