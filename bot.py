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

# ================= DB =================
conn = sqlite3.connect("real_estate.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
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
    created_at TEXT,
    updated_at TEXT
)
""")
conn.commit()

users = {}

STATUS_MAP = {
    "searching": "🟡 В пошуках",
    "reserved": "🟢 Мають резервацію",
    "self_found": "🔵 Самі знайшли",
    "other_broker": "🟠 Чужий маклер",
    "not_looking": "⚫ Не шукають",
    "deal_closed": "🔴 Закрили угоду",
}

# ================= HELPERS =================
def reset_user(uid):
    users.pop(uid, None)

def build_summary(u, req_id, with_status=True):
    status_line = f"📌 Статус: {u['status']}\n\n" if with_status else ""
    tg = f"@{u['username']}" if u.get("username") else "—"

    return (
        f"📋 **Запит №{req_id}**\n"
        f"{status_line}"
        f"👤 Імʼя: {u['name']}\n"
        f"🆔 Telegram: {tg}\n"
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
        f"💶 Бюджет оренда: {u['budget']}\n"
        f"⏰ Огляди: {u['view_time']}\n"
        f"🌍 Зараз в: {u['location']}\n"
        f"👀 Формат огляду: {u['view_format']}"
    )

def status_keyboard(req_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟡 В пошуках", callback_data=f"status_searching_{req_id}"),
            InlineKeyboardButton("🟢 Мають резервацію", callback_data=f"status_reserved_{req_id}")
        ],
        [
            InlineKeyboardButton("🔵 Самі знайшли", callback_data=f"status_self_found_{req_id}"),
            InlineKeyboardButton("🟠 Чужий маклер", callback_data=f"status_other_broker_{req_id}")
        ],
        [
            InlineKeyboardButton("⚫ Не шукають", callback_data=f"status_not_looking_{req_id}"),
            InlineKeyboardButton("🔴 Закрили угоду", callback_data=f"status_deal_closed_{req_id}")
        ]
    ])

# ================= START / RESET =================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    reset_user(update.effective_user.id)
    kb = [
        [InlineKeyboardButton("🏠 Оренда", callback_data="deal_rent")],
        [InlineKeyboardButton("🏡 Купівля", callback_data="deal_buy")]
    ]
    await update.message.reply_text(
        "👋 Вітаємо!\nЩо вас цікавить?",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================= FLOW =================
async def deal_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()

    users[q.from_user.id] = {
        "step": "property",
        "deal": "Оренда" if q.data == "deal_rent" else "Купівля",
        "username": q.from_user.username,
    }

    kb = [
        [InlineKeyboardButton("🛏 Ліжко-місце", callback_data="prop_Ліжко-місце")],
        [InlineKeyboardButton("🏢 Студія", callback_data="prop_Студія")],
        [InlineKeyboardButton("1-кімнатна", callback_data="prop_1-кімнатна")],
        [InlineKeyboardButton("2-кімнатна", callback_data="prop_2-кімнатна")],
        [InlineKeyboardButton("3-кімнатна", callback_data="prop_3-кімнатна")],
        [InlineKeyboardButton("🏠 Будинок", callback_data="prop_Будинок")],
        [InlineKeyboardButton("✍️ Свій варіант", callback_data="prop_custom")]
    ]
    await q.message.reply_text("🏡 Тип житла:", reply_markup=InlineKeyboardMarkup(kb))

async def property_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "prop_custom":
        u["step"] = "property_text"
        await q.message.reply_text("✍️ Напишіть свій варіант житла:")
    else:
        u["property"] = q.data.replace("prop_", "")
        u["step"] = "city"
        await q.message.reply_text("📍 В якому місті шукаєте житло?")

async def text_handler(update: Update, ctx):
    uid = update.effective_user.id
    if uid not in users:
        return

    u = users[uid]
    t = update.message.text

    match u["step"]:
        case "property_text":
            u["property"] = t
            u["step"] = "city"
            await update.message.reply_text("📍 В якому місті шукаєте житло?")

        case "city":
            u["city"] = t
            u["step"] = "district"
            await update.message.reply_text("🗺 Який район?")

        case "district":
            u["district"] = t
            u["step"] = "for_whom"
            await update.message.reply_text("👥 Для кого шукаєте житло?")

        case "for_whom":
            u["for_whom"] = t
            u["step"] = "job"
            await update.message.reply_text("💼 Чим ви займаєтесь?")

        case "job":
            u["job"] = t
            u["step"] = "children"
            await update.message.reply_text("🧒 Чи маєте дітей? Якщо ні — напишіть «Ні».")

        case "children":
            u["children"] = t
            u["step"] = "pets"
            await update.message.reply_text(
                "🐾 Чи маєте тваринок?\n"
                "Якщо так — напишіть яку і коротко про неї.\n"
                "Якщо ні — напишіть «Ні»."
            )

        case "pets":
            u["pets"] = t
            u["step"] = "parking"
            kb = [
                [InlineKeyboardButton("Так", callback_data="park_yes")],
                [InlineKeyboardButton("Ні", callback_data="park_no")],
                [InlineKeyboardButton("Пізніше", callback_data="park_later")]
            ]
            await update.message.reply_text("🚗 Чи потрібне паркування?", reply_markup=InlineKeyboardMarkup(kb))

        case "move_in":
            u["move_in"] = t
            u["step"] = "budget"
            await update.message.reply_text("💶 Який бюджет на оренду в місяць (від–до€)?")

        case "budget":
            u["budget"] = t
            u["step"] = "view_time"
            await update.message.reply_text("⏰ Коли ви доступні для оглядів?")

        case "view_time":
            u["view_time"] = t
            u["step"] = "location"
            kb = [
                [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc_ua")],
                [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc_sk")],
                [InlineKeyboardButton("✍️ Інша країна", callback_data="loc_custom")]
            ]
            await update.message.reply_text("🌍 Ви в країні?", reply_markup=InlineKeyboardMarkup(kb))

        case "custom_location":
            u["location"] = t
            u["step"] = "view_format"
            await ask_view_format(update.message)

        case "name":
            u["name"] = t
            u["status"] = STATUS_MAP["searching"]

            cursor.execute("""
            INSERT INTO requests VALUES (
                NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
            )
            """, (
                uid, u["username"], u["name"], u["phone"], u["deal"],
                u["property"], u["city"], u["district"], u["for_whom"],
                u["job"], u["children"], u["pets"], u["parking"],
                u["move_in"], u["budget"], u["view_time"],
                u["location"], u["view_format"], u["status"],
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
            conn.commit()

            req_id = cursor.lastrowid

            await ctx.bot.send_message(
                ADMIN_GROUP_ID,
                build_summary(u, req_id),
                parse_mode="Markdown",
                reply_markup=status_keyboard(req_id)
            )

            await update.message.reply_text(
                "✅ Запит відправлено маклеру.\n"
                "Ми звʼяжемось з вами протягом **24–48 годин**.\n\n"
                "🔔 Долучайтесь до нашої групи з пропозиціями житла в Братиславі:\n"
                "👉 https://t.me/+IhcJixOP1_QyNjM0",
                parse_mode="Markdown"
            )
            reset_user(uid)

async def parking_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["parking"] = {"park_yes":"Так","park_no":"Ні","park_later":"Пізніше"}[q.data]
    u["step"] = "move_in"
    await q.message.reply_text("📅 Яка найкраща дата для заїзду?")

async def location_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "loc_custom":
        u["step"] = "custom_location"
        await q.message.reply_text("✍️ Напишіть країну:")
    else:
        u["location"] = "Україна" if q.data == "loc_ua" else "Словаччина"
        u["step"] = "view_format"
        await ask_view_format(q.message)

async def ask_view_format(msg):
    kb = [
        [InlineKeyboardButton("💻 Онлайн", callback_data="view_online")],
        [InlineKeyboardButton("🚶 Фізичний", callback_data="view_offline")],
        [InlineKeyboardButton("🔁 Обидва варіанти", callback_data="view_both")]
    ]
    await msg.reply_text("👀 Формат огляду?", reply_markup=InlineKeyboardMarkup(kb))

async def view_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["view_format"] = {"view_online":"Онлайн","view_offline":"Фізичний","view_both":"Обидва варіанти"}[q.data]
    u["step"] = "contact"

    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Поділитись контактом для пошуку житла", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await q.message.reply_text("📞 Поділіться контактом для пошуку житла 👇", reply_markup=kb)

async def contact_handler(update: Update, ctx):
    u = users[update.effective_user.id]
    u["phone"] = update.message.contact.phone_number
    u["step"] = "name"
    await update.message.reply_text("👤 Як до вас можемо звертатись?")

# ================= STATUS HANDLER =================
async def status_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()

    parts = q.data.split("_")
    req_id = int(parts[-1])
    status_key = "_".join(parts[1:-1])
    new_status = STATUS_MAP[status_key]

    cursor.execute(
        "UPDATE requests SET status=?, updated_at=? WHERE id=?",
        (new_status, datetime.now().isoformat(), req_id)
    )
    conn.commit()

    lines = q.message.text.split("\n")
    for i, l in enumerate(lines):
        if l.startswith("📌 Статус:"):
            lines[i] = f"📌 Статус: {new_status}"
            break

    await q.message.edit_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=q.message.reply_markup
    )

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(deal_handler, pattern="^deal_"))
    app.add_handler(CallbackQueryHandler(property_handler, pattern="^prop_"))
    app.add_handler(CallbackQueryHandler(parking_handler, pattern="^park_"))
    app.add_handler(CallbackQueryHandler(location_handler, pattern="^loc_"))
    app.add_handler(CallbackQueryHandler(view_handler, pattern="^view_"))
    app.add_handler(CallbackQueryHandler(status_handler, pattern="^status_"))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
