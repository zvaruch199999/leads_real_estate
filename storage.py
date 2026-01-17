import json
from datetime import datetime

FILE = "requests.json"

def load_data():
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"counter": 0, "requests": []}

def save_data(data):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def new_request(payload):
    data = load_data()
    data["counter"] += 1
    payload["id"] = data["counter"]
    payload["date"] = datetime.now().strftime("%Y-%m-%d")
    payload["status"] = "В роботі"
    data["requests"].append(payload)
    save_data(data)
    return payload["id"]

def stats(period="day"):
    data = load_data()
    today = datetime.now().strftime("%Y-%m-%d")
    month = today[:7]

    if period == "day":
        return len([r for r in data["requests"] if r["date"] == today])
    if period == "month":
        return len([r for r in data["requests"] if r["date"].startswith(month)])
    if period == "closed":
        return len([r for r in data["requests"] if r["status"] == "Закрито"])
