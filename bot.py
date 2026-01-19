import os
import sqlite3
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ================== CONFIG ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_GROUP_ID = os.environ.get("ADMIN_GROUP_ID")

if BOT_TOKEN is None:
    raise RuntimeError("BOT_TOKEN не заданий у Variables")

if ADMIN_GROUP_ID is None:
    raise RuntimeError("ADMIN_GROUP_ID не заданий у Variables")

ADMIN_GROUP_ID = int(ADMIN_GROUP_ID)

# ================== DATABASE ==================
conn = sqlite3.connect("real_estate.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property TEXT,
    status TEXT,
    created_at TEXT
)
""")
conn.commit()

# ================== STATE ==================
users = {}
REQUEST_COUNTER = 0

STATUS_MAP = {
    "search": "🟡 В пошуках",
    "reserve": "🟢 Мають резервацію",
    "self": "🔵 Самі знайшли",
    "other": "🟠 Знайшов чужий маклер",
    "stop": "⚫ Не шукають",
    "closed": "🔴 Закрили угоду",
}

# ================== HELPERS ==================
def reset_user(uid):
    users.pop(uid, None)

def status_keyboard(req_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟡 В пошуках", callback_data=f"status:search:{req_id}"),
            InlineKeyboardButton("🟢 Резервація", callback_data=f"status:reserve:{req_id}")
        ],
        [
            InlineKeyboardButton("🔵 Самі знайшли", callback_data=f"status:self:{req_id}"),
            InlineKeyboardButton("🟠 Чужий маклер", callback_data=f"status:other:{req_id}")
        ],
        [
            InlineKeyboardButton("⚫ Не шукають", callback_data=f"status:stop:{req_id}"),
            InlineKeyboardButton("🔴 Закрили угоду", callback_data=f"status:closed:{req_id}")
        ]
    ])

def build_summary(u, req_id):
    tg = f"@{u.get('username')}" if u.get("username") else "—"
    return (
        f"📋 *Запит №{req_id}*\n"
        f"📌 Статус: {STATUS_MAP['search']}\n\n"
        f"👤 Імʼя: {u['name']}\n"
        f"🆔 Telegram: {tg}\n"
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
        f"⏰ Огляди: {u['view_time']}\n"
        f"✨ Побажання: {u['wishes']}\n"
        f"💶 Бюджет оренда: {u['budget']}\n"
        f"🌍 Зараз в: {u['location']}\n"
        f"👀 Формат огляду: {u['view_format']}"
    )

# ================== START ==================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    reset_user(update.effective_user.id)
    users[update.effective_user.id] = {
        "step": "deal",
        "username": update.effective_user.username or ""
    }

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Оренда", callback_data="deal:rent")],
        [InlineKeyboardButton("🏡 Купівля", callback_data="deal:buy")]
    ])
    await update.message.reply_text("👋 Вітаємо! Що вас цікавить?", reply_markup=kb)

# ================== DEAL ==================
async def deal_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    u["deal"] = "Оренда" if "rent" in q.data else "Купівля"
    u["step"] = "property"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛏 Ліжко-місце", callback_data="prop:Ліжко-місце")],
        [InlineKeyboardButton("🏢 Студія", callback_data="prop:Студія")],
        [InlineKeyboardButton("1️⃣ 1-кімнатна", callback_data="prop:1-кімнатна")],
        [InlineKeyboardButton("2️⃣ 2-кімнатна", callback_data="prop:2-кімнатна")],
        [InlineKeyboardButton("3️⃣ 3-кімнатна", callback_data="prop:3-кімнатна")],
        [InlineKeyboardButton("🏡 Будинок", callback_data="prop:Будинок")],
        [InlineKeyboardButton("✍️ Свій варіант", callback_data="prop:custom")]
    ])
    await q.message.reply_text("🏡 Який тип житла?", reply_markup=kb)

# ================== PROPERTY ==================
async def property_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    val = q.data.split(":")[1]
    if val == "custom":
        u["step"] = "property_custom"
        await q.message.reply_text("✍️ Напишіть тип житла:")
    else:
        u["property"] = val
        u["step"] = "city"
        await q.message.reply_text("📍 В якому місті шукаєте житло?")

# ================== TEXT FLOW ==================
async def text_handler(update: Update, ctx):
    uid = update.effective_user.id
    if uid not in users:
        return
    u = users[uid]
    t = update.message.text

    if u["step"] == "property_custom":
        u["property"] = t
        u["step"] = "city"
        await update.message.reply_text("📍 В якому місті шукаєте житло?")

    elif u["step"] == "city":
        u["city"] = t
        u["step"] = "district"
        await update.message.reply_text("🗺 Який район?")

    elif u["step"] == "district":
        u["district"] = t
        u["step"] = "for_whom"
        await update.message.reply_text("👥 Для кого шукаєте житло?")

    elif u["step"] == "for_whom":
        u["for_whom"] = t
        u["step"] = "job"
        await update.message.reply_text("💼 Чим ви займаєтесь?")

    elif u["step"] == "job":
        u["job"] = t
        u["step"] = "children"
        await update.message.reply_text("🧒 Чи маєте дітей? Якщо ні — «Ні»")

    elif u["step"] == "children":
        u["children"] = t
        u["step"] = "pets"
        await update.message.reply_text(
            "🐾 Чи маєте тваринок?\n"
            "Якщо так — напишіть яку і трохи про неї.\n"
            "Якщо ні — «Ні»"
        )

    elif u["step"] == "pets":
        u["pets"] = t
        u["step"] = "parking"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Так", callback_data="park:Так")],
            [InlineKeyboardButton("Ні", callback_data="park:Ні")],
            [InlineKeyboardButton("Пізніше", callback_data="park:Пізніше")]
        ])
        await update.message.reply_text("🚗 Чи потрібне паркування?", reply_markup=kb)

    elif u["step"] == "move_in":
        u["move_in"] = t
        u["step"] = "view_time"
        await update.message.reply_text("⏰ Коли ви доступні для оглядів?")

    elif u["step"] == "view_time":
        u["view_time"] = t
        u["step"] = "wishes"
        await update.message.reply_text("✨ Напишіть особливі побажання до житла")

    elif u["step"] == "wishes":
        u["wishes"] = t
        u["step"] = "budget"
        await update.message.reply_text("💶 Який бюджет на оренду в місяць (від–до €)?")

    elif u["step"] == "budget":
        u["budget"] = t
        u["step"] = "location"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc:ua")],
            [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc:sk")],
            [InlineKeyboardButton("✍️ Інша країна", callback_data="loc:custom")]
        ])
        await update.message.reply_text("🌍 Де ви зараз?", reply_markup=kb)

    elif u["step"] == "location_custom":
        u["location"] = t
        u["step"] = "view_format"
        await ask_view_format(update)

    elif u["step"] == "name":
        global REQUEST_COUNTER
        REQUEST_COUNTER += 1
        u["name"] = t
        u["req_id"] = REQUEST_COUNTER

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Так", callback_data="confirm:yes")],
            [InlineKeyboardButton("❌ Ні", callback_data="confirm:no")]
        ])
        await update.message.reply_text(
            build_summary(u, REQUEST_COUNTER) + "\n\nВсе вірно?",
            reply_markup=kb,
            parse_mode="Markdown"
        )

# ================== CALLBACKS ==================
async def parking_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["parking"] = q.data.split(":")[1]
    u["step"] = "move_in"
    await q.message.reply_text("📅 Яка найкраща дата для заїзду?")

async def location_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    val = q.data.split(":")[1]

    if val == "custom":
        u["step"] = "location_custom"
        await q.message.reply_text("✍️ Напишіть країну:")
    else:
        u["location"] = "Україна" if val == "ua" else "Словаччина"
        u["step"] = "view_format"
        await ask_view_format(update)

async def ask_view_format(update: Update):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💻 Онлайн", callback_data="view:Онлайн")],
        [InlineKeyboardButton("🚶 Фізичний", callback_data="view:Фізичний")],
        [InlineKeyboardButton("🔁 Обидва варіанти", callback_data="view:Обидва")]
    ])
    await update.message.reply_text("👀 Який формат огляду?", reply_markup=kb)

async def view_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["view_format"] = q.data.split(":")[1]
    u["step"] = "contact"

    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Поділитись контактом для пошуку житла", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await q.message.reply_text("📞 Поділіться контактом для пошуку житла", reply_markup=kb)

async def contact_handler(update: Update, ctx):
    u = users[update.effective_user.id]
    u["phone"] = update.message.contact.phone_number
    u["step"] = "name"
    await update.message.reply_text("👤 Як до вас можемо звертатись?", reply_markup=ReplyKeyboardRemove())

async def confirm_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    if "no" in q.data:
        reset_user(q.from_user.id)
        await q.message.reply_text("❌ Запит скасовано")
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Так", callback_data="terms:yes")],
        [InlineKeyboardButton("❌ Ні", callback_data="terms:no")]
    ])
    await q.message.reply_text(
        "ℹ️ *Умови співпраці:*\n"
        "• депозит за квартиру в розмірі орендної плати\n"
        "• повна або часткова комісія ріелтору\n"
        "• можливий подвійний депозит у випадку, якщо маєте дітей або тваринок\n\n"
        "Чи погоджуєтесь?",
        reply_markup=kb,
        parse_mode="Markdown"
    )

async def terms_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    if "no" in q.data:
        reset_user(q.from_user.id)
        await q.message.reply_text("❌ Дякуємо")
        return

    u = users[q.from_user.id]

    cursor.execute(
        "INSERT INTO requests (property, status, created_at) VALUES (?,?,?)",
        (u["property"], STATUS_MAP["search"], datetime.now().isoformat())
    )
    conn.commit()

    await ctx.bot.send_message(
        ADMIN_GROUP_ID,
        build_summary(u, u["req_id"]),
        reply_markup=status_keyboard(u["req_id"]),
        parse_mode="Markdown"
    )

    await q.message.reply_text(
        "✅ Запит відправлено маклеру.\n"
        "Ми звʼяжемось з вами протягом *24–48 годин*.\n\n"
        "🔔 Долучайтесь до нашої групи — тут актуальні пропозиції житла в Братиславі:\n"
        "👉 https://t.me/+IhcJixOP1_QyNjM0",
        parse_mode="Markdown"
    )

    reset_user(q.from_user.id)

# ================== STATUS ==================
async def status_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()

    _, status_key, req_id = q.data.split(":")
    new_status = STATUS_MAP[status_key]

    cursor.execute(
        "UPDATE requests SET status=? WHERE id=?",
        (new_status, req_id)
    )
    conn.commit()

    text = q.message.text.split("📌 Статус:")[0] + f"📌 Статус: {new_status}"
    await q.message.edit_text(
        text,
        reply_markup=status_keyboard(req_id),
        parse_mode="Markdown"
    )

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(deal_handler, pattern="^deal:"))
    app.add_handler(CallbackQueryHandler(property_handler, pattern="^prop:"))
    app.add_handler(CallbackQueryHandler(parking_handler, pattern="^park:"))
    app.add_handler(CallbackQueryHandler(location_handler, pattern="^loc:"))
    app.add_handler(CallbackQueryHandler(view_handler, pattern="^view:"))
    app.add_handler(CallbackQueryHandler(confirm_handler, pattern="^confirm:"))
    app.add_handler(CallbackQueryHandler(terms_handler, pattern="^terms:"))
    app.add_handler(CallbackQueryHandler(status_handler, pattern="^status:"))

    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
