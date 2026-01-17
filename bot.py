import os
import sqlite3
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== CONFIG ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = -1001234567890  # <-- заміни на ID своєї групи

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set in environment variables")

# ================== DATABASE ==================

conn = sqlite3.connect("real_estate.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    phone TEXT,
    deal TEXT,
    property TEXT,
    city TEXT,
    district TEXT,
    for_whom TEXT,
    job TEXT,
    children TEXT,
    pets TEXT,
    parking TEXT,
    move_in TEXT,
    budget TEXT,
    view_time TEXT,
    location TEXT,
    view_format TEXT,
    status TEXT,
    created_at TEXT
)
""")
conn.commit()

# ================== STATE ==================

users = {}

PARKING_MAP = {
    "park_yes": "Так",
    "park_no": "Ні",
    "park_later": "Пізніше",
}

VIEW_MAP = {
    "view_online": "Онлайн",
    "view_offline": "Фізичний",
    "view_both": "Обидва варіанти",
}

LOCATION_MAP = {
    "loc_ua": "Україна",
    "loc_sk": "Словаччина",
}

# ================== HELPERS ==================

def build_summary(u, req_id):
    return (
        f"📋 **Запит №{req_id}**\n\n"
        f"👤 Імʼя: {u['name']}\n"
        f"📞 Телефон: {u['phone']}\n\n"
        f"🏠 Тип угоди: {u['deal']}\n"
        f"🏡 Тип житла: {u['property']}\n"
        f"📍 Місто: {u['city']} / {u['district']}\n"
        f"👥 Для кого: {u['for_whom']}\n"
        f"💼 Діяльність: {u['job']}\n"
        f"🧒 Діти: {u['children']}\n"
        f"🐾 Тваринки: {u['pets']}\n"
        f"🚗 Паркування: {u['parking']}\n"
        f"📅 Заїзд: {u['move_in']}\n"
        f"💶 Бюджет: {u['budget']}\n"
        f"⏰ Огляди: {u['view_time']}\n"
        f"🌍 Зараз: {u['location']}\n"
        f"👀 Формат огляду: {u['view_format']}\n\n"
        f"🔄 **Статус:** {u['status']}"
    )

def save_request(u):
    cur.execute(
        """
        INSERT INTO requests (
            user_id, name, phone, deal, property, city, district,
            for_whom, job, children, pets, parking, move_in,
            budget, view_time, location, view_format, status, created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            u["user_id"], u["name"], u["phone"], u["deal"], u["property"],
            u["city"], u["district"], u["for_whom"], u["job"],
            u["children"], u["pets"], u["parking"], u["move_in"],
            u["budget"], u["view_time"], u["location"],
            u["view_format"], u["status"],
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ),
    )
    conn.commit()
    return cur.lastrowid

# ================== START ==================

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id] = {
        "user_id": update.effective_user.id,
        "step": "deal",
    }

    kb = [
        [InlineKeyboardButton("🏠 Оренда", callback_data="deal_rent")],
        [InlineKeyboardButton("🏡 Купівля", callback_data="deal_buy")],
    ]
    await update.message.reply_text(
        "👋 Вітаємо!\nЩо вас цікавить?",
        reply_markup=InlineKeyboardMarkup(kb),
    )

# ================== CALLBACKS ==================

async def deal_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    u["deal"] = "Оренда" if q.data == "deal_rent" else "Купівля"
    u["step"] = "property"

    kb = [
        [InlineKeyboardButton("Студія", callback_data="prop_Студія")],
        [InlineKeyboardButton("1-кімнатна", callback_data="prop_1")],
        [InlineKeyboardButton("2-кімнатна", callback_data="prop_2")],
        [InlineKeyboardButton("3-кімнатна", callback_data="prop_3")],
        [InlineKeyboardButton("Будинок", callback_data="prop_Будинок")],
        [InlineKeyboardButton("✍️ Свій варіант", callback_data="prop_custom")],
    ]
    await q.message.reply_text(
        "🏡 Який тип житла?",
        reply_markup=InlineKeyboardMarkup(kb),
    )

async def property_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "prop_custom":
        u["step"] = "property_text"
        await q.message.reply_text("✍️ Напишіть тип житла:")
    else:
        u["property"] = q.data.replace("prop_", "")
        u["step"] = "city"
        await q.message.reply_text("📍 В якому місті шукаєте житло?")

# ================== TEXT FLOW ==================

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if uid not in users:
        return

    u = users[uid]
    t = update.message.text
    step = u["step"]

    if step == "property_text":
        u["property"] = t
        u["step"] = "city"
        await update.message.reply_text("📍 В якому місті шукаєте житло?")

    elif step == "city":
        u["city"] = t
        u["step"] = "district"
        await update.message.reply_text("🗺 Який район?")

    elif step == "district":
        u["district"] = t
        u["step"] = "for_whom"
        await update.message.reply_text("👥 Для кого шукаєте житло?")

    elif step == "for_whom":
        u["for_whom"] = t
        u["step"] = "job"
        await update.message.reply_text("💼 Чим ви займаєтесь?")

    elif step == "job":
        u["job"] = t
        u["step"] = "children"
        await update.message.reply_text("🧒 Чи маєте дітей? Якщо ні — напишіть «Ні».")

    elif step == "children":
        u["children"] = t
        u["step"] = "pets"
        await update.message.reply_text(
            "🐾 Чи маєте тваринок?\n"
            "Якщо так — напишіть яку і коротко про неї.\n"
            "Якщо ні — напишіть «Ні»."
        )

    elif step == "pets":
        u["pets"] = t
        u["step"] = "parking"
        kb = [
            [InlineKeyboardButton("Так", callback_data="park_yes")],
            [InlineKeyboardButton("Ні", callback_data="park_no")],
            [InlineKeyboardButton("Пізніше", callback_data="park_later")],
        ]
        await update.message.reply_text(
            "🚗 Чи потрібне паркування?",
            reply_markup=InlineKeyboardMarkup(kb),
        )

    elif step == "move_in":
        u["move_in"] = t
        u["step"] = "budget"
        await update.message.reply_text("💶 Який бюджет (від–до) €?")

    elif step == "budget":
        u["budget"] = t
        u["step"] = "view_time"
        await update.message.reply_text("⏰ Коли ви доступні для оглядів?")

    elif step == "view_time":
        u["view_time"] = t
        u["step"] = "location"
        kb = [
            [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc_ua")],
            [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc_sk")],
            [InlineKeyboardButton("✍️ Інша країна", callback_data="loc_custom")],
        ]
        await update.message.reply_text(
            "🌍 Де ви зараз знаходитесь?",
            reply_markup=InlineKeyboardMarkup(kb),
        )

    elif step == "custom_location":
        u["location"] = t
        u["step"] = "view_format"
        await ask_view_format(update.message)

    elif step == "name":
        u["name"] = t
        u["status"] = "🟡 В пошуках"
        req_id = save_request(u)

        kb = [
            [InlineKeyboardButton("🔵 В роботу", callback_data=f"status_work_{req_id}")],
            [InlineKeyboardButton("✅ Знайдено", callback_data=f"status_done_{req_id}")],
            [InlineKeyboardButton("❌ Неактуально", callback_data=f"status_cancel_{req_id}")],
        ]

        await ctx.bot.send_message(
            ADMIN_GROUP_ID,
            build_summary(u, req_id),
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )

        await update.message.reply_text(
            "✅ Запит відправлено маклеру.\n"
            "Ми звʼяжемось з вами протягом **24–48 годин**.",
            parse_mode="Markdown",
        )

        users.pop(uid)

# ================== PARKING / LOCATION / VIEW ==================

async def parking_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["parking"] = PARKING_MAP[q.data]
    u["step"] = "move_in"
    await q.message.reply_text("📅 Коли плануєте заїзд?")

async def location_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "loc_custom":
        u["step"] = "custom_location"
        await q.message.reply_text("✍️ Напишіть країну:")
    else:
        u["location"] = LOCATION_MAP[q.data]
        u["step"] = "view_format"
        await ask_view_format(q.message)

async def ask_view_format(msg):
    kb = [
        [InlineKeyboardButton("💻 Онлайн", callback_data="view_online")],
        [InlineKeyboardButton("🚶 Фізичний", callback_data="view_offline")],
        [InlineKeyboardButton("🔁 Обидва варіанти", callback_data="view_both")],
    ]
    await msg.reply_text(
        "👀 Який формат огляду вам підходить?",
        reply_markup=InlineKeyboardMarkup(kb),
    )

async def view_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["view_format"] = VIEW_MAP[q.data]
    u["step"] = "contact"

    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Поділитись контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await q.message.reply_text("📞 Поділіться контактом:", reply_markup=kb)

# ================== CONTACT ==================

async def contact_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = users[update.message.from_user.id]
    u["phone"] = update.message.contact.phone_number
    u["step"] = "name"
    await update.message.reply_text("👤 Як до вас можемо звертатись?")

# ================== STATUS ==================

async def status_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cur.execute(
        """
        SELECT id, city, district, status
        FROM requests
        WHERE user_id=?
        ORDER BY id DESC LIMIT 1
        """,
        (update.effective_user.id,),
    )
    row = cur.fetchone()

    if not row:
        await update.message.reply_text("❌ У вас немає активних запитів.")
        return

    await update.message.reply_text(
        f"📋 Запит №{row[0]}\n"
        f"📍 {row[1]} / {row[2]}\n\n"
        f"🔄 Статус: {row[3]}"
    )

async def status_update_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    _, action, req_id = q.data.split("_")
    status_map = {
        "work": "🔵 Опрацьовується",
        "done": "✅ Житло знайдено",
        "cancel": "❌ Неактуально",
    }

    cur.execute(
        "UPDATE requests SET status=? WHERE id=?",
        (status_map[action], int(req_id)),
    )
    conn.commit()

    await q.message.edit_text(
        f"📋 Запит №{req_id}\n\n🔄 Статус: {status_map[action]}"
    )

# ================== MAIN ==================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_command))

    app.add_handler(CallbackQueryHandler(deal_handler, pattern="^deal_"))
    app.add_handler(CallbackQueryHandler(property_handler, pattern="^prop_"))
    app.add_handler(CallbackQueryHandler(parking_handler, pattern="^park_"))
    app.add_handler(CallbackQueryHandler(location_handler, pattern="^loc_"))
    app.add_handler(CallbackQueryHandler(view_handler, pattern="^view_"))
    app.add_handler(CallbackQueryHandler(status_update_handler, pattern="^status_"))

    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
