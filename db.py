import sqlite3

conn = sqlite3.connect("leads.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    phone TEXT,
    deal_type TEXT,
    property_type TEXT,
    city TEXT,
    district TEXT,
    budget TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()


def save_lead(data: dict):
    cursor.execute("""
    INSERT INTO leads 
    (user_id, username, phone, deal_type, property_type, city, district, budget)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["user_id"],
        data["username"],
        data["phone"],
        data["deal_type"],
        data["property_type"],
        data["city"],
        data["district"],
        data["budget"]
    ))
    conn.commit()
