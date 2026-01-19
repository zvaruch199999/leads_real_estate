import os
import sqlite3
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID")

if not BOT_TOKEN or not ADMIN_GROUP_ID:
    raise RuntimeError("BOT_TOKEN або ADMIN_GROUP_ID не задані")

ADMIN_GROUP_ID = int(ADMIN_GROUP_ID)

# ================== DB ==================
db = sqlite3.connect("stats.db", check_same_thread=False)
cur = db.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    property TEXT,
    status TEXT
)
""")
db.commit()

# ================== GLOBAL ==================
users = {}
REQUEST_ID = 0

STATUS_MAP = {
    "search": "🟡 В пошуках",
    "reserve": "🟢 Мають резервацію",
    "self": "🔵 Самі знайшли",
    "other": "🟠 Чужий маклер",
    "stop": "⚫ Не шукають",
    "closed": "🔴 Закрили угоду"
}

# ================== START ==================
async def start(update: Update, ctx):
    users[update.effective_user.id] = {"step": "deal"}
    kb = [
        [InlineKeyboardButton("🏠 Оренда", callback_data="deal_rent")],
        [InlineKeyboardButton("🏡 Купівля", callback_data="deal_buy")]
    ]
    await update.message.reply_text(
        "👋 Що вас цікавить?",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================== DEAL ==================
async def deal_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["deal"] = "Оренда" if q.data == "deal_rent" else "Купівля"
    u["step"] = "property"

    kb = [
        [InlineKeyboardButton("🛏 Ліжко-місце", callback_data="prop_Ліжко-місце")],
        [InlineKeyboardButton("🏢 Студія", callback_data="prop_Студія")],
        [InlineKeyboardButton("1️⃣ 1-кімнатна", callback_data="prop_1-кімнатна")],
        [InlineKeyboardButton("2️⃣ 2-кімнатна", callback_data="prop_2-кімнатна")],
        [InlineKeyboardButton("3️⃣ 3-кімнатна", callback_data="prop_3-кімнатна")],
        [InlineKeyboardButton("✍️ Свій варіант", callback_data="prop_custom")]
    ]
    await q.message.reply_text("🏠 Тип житла:", reply_markup=InlineKeyboardMarkup(kb))

# ================== PROPERTY ==================
async def property_handler(update: Update, ctx):
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
async def text_handler(update: Update, ctx):
    uid = update.message.from_user.id
    if uid not in users:
        return

    u = users[uid]
    text = update.message.text

    if u["step"] == "property_text":
        u["property"] = text
        u["step"] = "city"
        await update.message.reply_text("📍 В якому місті шукаєте житло?")

    elif u["step"] == "city":
        u["city"] = text
        u["step"] = "district"
        await update.message.reply_text("🗺 Який район?")

    elif u["step"] == "district":
        u["district"] = text
        u["step"] = "for_whom"
        await update.message.reply_text("👥 Для кого шукаєте житло?")

    elif u["step"] == "for_whom":
        u["for_whom"] = text
        u["step"] = "job"
        await update.message.reply_text("💼 Чим ви займаєтесь?")

    elif u["step"] == "job":
        u["job"] = text
        u["step"] = "children"
        await update.message.reply_text("🧒 Чи є діти?")

    elif u["step"] == "children":
        u["children"] = text
        u["step"] = "pets"
        await update.message.reply_text(
            "🐾 Чи є тваринки?\nЯкщо так — напишіть які."
        )

    elif u["step"] == "pets":
        u["pets"] = text
        u["step"] = "parking"
        kb = [
            [InlineKeyboardButton("Так", callback_data="park_yes")],
            [InlineKeyboardButton("Ні", callback_data="park_no")],
            [InlineKeyboardButton("Пізніше", callback_data="park_later")]
        ]
        await update.message.reply_text(
            "🚗 Паркування?",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif u["step"] == "move_in":
        u["move_in"] = text
        u["step"] = "view_time"
        await update.message.reply_text("⏰ Коли зручні огляди?")

    elif u["step"] == "view_time":
        u["view_time"] = text
        u["step"] = "wishes"
        await update.message.reply_text("✨ Особливі побажання до житла?")

    elif u["step"] == "wishes":
        u["wishes"] = text
        u["step"] = "budget"
        await update.message.reply_text(
            "💶 Який бюджет на оренду в місяць (від–до €)?"
        )

    elif u["step"] == "budget":
        u["budget"] = text
        u["step"] = "location"
        kb = [
            [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc_ua")],
            [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc_sk")],
            [InlineKeyboardButton("✍️ Інша країна", callback_data="loc_other")]
        ]
        await update.message.reply_text(
            "🌍 Де ви зараз?",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif u["step"] == "custom_location":
        u["location"] = text
        await ask_view_format(update.message, u)

    elif u["step"] == "name":
        u["name"] = text
        await show_terms(update, u)

# ================== PARKING ==================
async def parking_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    u["parking"] = {
        "park_yes": "Так",
        "park_no": "Ні",
        "park_later": "Пізніше"
    }[q.data]

    u["step"] = "move_in"
    await q.message.reply_text("📅 Коли плануєте заїзд?")

# ================== LOCATION ==================
async def location_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "loc_other":
        u["step"] = "custom_location"
        await q.message.reply_text("✍️ Напишіть країну:")
    else:
        u["location"] = "Україна" if q.data == "loc_ua" else "Словаччина"
        await ask_view_format(q.message, u)

# ================== VIEW FORMAT ==================
async def ask_view_format(msg, u):
    u["step"] = "view_format"
    kb = [
        [InlineKeyboardButton("💻 Онлайн", callback_data="view_online")],
        [InlineKeyboardButton("🚶 Фізичний", callback_data="view_offline")],
        [InlineKeyboardButton("🔁 Обидва варіанти", callback_data="view_both")]
    ]
    await msg.reply_text(
        "👀 Який формат огляду?",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def view_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    u["view_format"] = {
        "view_online": "Онлайн",
        "view_offline": "Фізичний",
        "view_both": "Обидва варіанти"
    }[q.data]

    u["step"] = "contact"
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Поділитись контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await q.message.reply_text(
        "📞 Поділіться контактом для пошуку житла:",
        reply_markup=kb
    )

# ================== CONTACT ==================
async def contact_handler(update: Update, ctx):
    u = users[update.message.from_user.id]
    u["phone"] = update.message.contact.phone_number
    u["telegram"] = update.message.from_user.username or "-"
    u["step"] = "name"
    await update.message.reply_text("👤 Як до вас можемо звертатись?")

# ================== TERMS ==================
async def show_terms(update: Update, u):
    kb = [
        [InlineKeyboardButton("✅ Так", callback_data="terms_yes")],
        [InlineKeyboardButton("❌ Ні", callback_data="terms_no")]
    ]
    await update.message.reply_text(
        "ℹ️ Умови співпраці:\n\n"
        "• депозит може дорівнювати орендній платі\n"
        "• оплачується повна або часткова комісія ріелтору\n"
        "• можливий подвійний депозит при дітях або тваринах\n\n"
        "Чи погоджуєтесь?",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def terms_handler(update: Update, ctx):
    global REQUEST_ID
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "terms_no":
        users.pop(q.from_user.id, None)
        await q.message.reply_text("❌ Запит скасовано.")
        return

    REQUEST_ID += 1
    status = STATUS_MAP["search"]

    text = (
        f"📋 Запит №{REQUEST_ID}\n"
        f"📌 Статус: {status}\n\n"
        f"👤 Імʼя: {u['name']}\n"
        f"🆔 Telegram: @{u['telegram']}\n"
        f"📞 Телефон: {u['phone']}\n\n"
        f"🏠 Тип угоди: {u['deal']}\n"
        f"🏡 Житло: {u['property']}\n"
        f"📍 Місто: {u['city']} / {u['district']}\n"
        f"👥 Для кого: {u['for_whom']}\n"
        f"💼 Діяльність: {u['job']}\n"
        f"🧒 Діти: {u['children']}\n"
        f"🐾 Тваринки: {u['pets']}\n"
        f"🚗 Паркування: {u['parking']}\n"
        f"📅 Заїзд: {u['move_in']}\n"
        f"⏰ Огляди: {u['view_time']}\n"
        f"✨ Побажання: {u['wishes']}\n"
        f"💶 Бюджет оренда: {u['budget']}\n"
        f"🌍 Зараз в: {u['location']}\n"
        f"👀 Формат огляду: {u['view_format']}"
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟡 В пошуках", callback_data="status_search"),
            InlineKeyboardButton("🟢 Мають резервацію", callback_data="status_reserve")
        ],
        [
            InlineKeyboardButton("🔵 Самі знайшли", callback_data="status_self"),
            InlineKeyboardButton("🟠 Чужий маклер", callback_data="status_other")
        ],
        [
            InlineKeyboardButton("⚫ Не шукають", callback_data="status_stop"),
            InlineKeyboardButton("🔴 Закрили угоду", callback_data="status_closed")
        ]
    ])

    await ctx.bot.send_message(
        ADMIN_GROUP_ID,
        text,
        reply_markup=kb
    )

    cur.execute(
        "INSERT INTO requests (date, property, status) VALUES (?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d"), u["property"], status)
    )
    db.commit()

    await q.message.reply_text(
        "✅ Запит відправлено маклеру.\n"
        "Ми звʼяжемось з вами протягом 24–48 годин.\n\n"
        "👉 Долучайтесь до нашої групи з пропозиціями:\n"
        "https://t.me/+IhcJixOP1_QyNjM0"
    )

    users.pop(q.from_user.id, None)

# ================== STATUS CHANGE ==================
async def status_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()

    status_key = q.data.replace("status_", "")
    new_status = STATUS_MAP[status_key]

    lines = q.message.text.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("📌 Статус:"):
            lines[i] = f"📌 Статус: {new_status}"

    await q.message.edit_text(
        "\n".join(lines),
        reply_markup=q.message.reply_markup
    )

# ================== STATS ==================
async def stats_today(update: Update, ctx):
    today = datetime.now().strftime("%Y-%m-%d")
    cur.execute("SELECT property, COUNT(*) FROM requests WHERE date=? GROUP BY property", (today,))
    rows = cur.fetchall()

    text = "📊 Статистика за сьогодні:\n\n"
    for p, c in rows:
        text += f"🏠 {p}: {c}\n"

    await update.message.reply_text(text)

async def stats_week(update: Update, ctx):
    date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    cur.execute("SELECT property, COUNT(*) FROM requests WHERE date>=? GROUP BY property", (date_from,))
    rows = cur.fetchall()

    text = "📊 Статистика за 7 днів:\n\n"
    for p, c in rows:
        text += f"🏠 {p}: {c}\n"

    await update.message.reply_text(text)

async def stats_month(update: Update, ctx):
    date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    cur.execute("SELECT property, COUNT(*) FROM requests WHERE date>=? GROUP BY property", (date_from,))
    rows = cur.fetchall()

    text = "📊 Статистика за 30 днів:\n\n"
    for p, c in rows:
        text += f"🏠 {p}: {c}\n"

    await update.message.reply_text(text)

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats_today", stats_today))
    app.add_handler(CommandHandler("stats_week", stats_week))
    app.add_handler(CommandHandler("stats_month", stats_month))

    app.add_handler(CallbackQueryHandler(deal_handler, pattern="^deal_"))
    app.add_handler(CallbackQueryHandler(property_handler, pattern="^prop_"))
    app.add_handler(CallbackQueryHandler(parking_handler, pattern="^park_"))
    app.add_handler(CallbackQueryHandler(location_handler, pattern="^loc_"))
    app.add_handler(CallbackQueryHandler(view_handler, pattern="^view_"))
    app.add_handler(CallbackQueryHandler(terms_handler, pattern="^terms_"))
    app.add_handler(CallbackQueryHandler(status_handler, pattern="^status_"))

    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
