import sqlite3
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN, ADMIN_GROUP_ID

# =========================
# DATABASE
# =========================

conn = sqlite3.connect("real_estate.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY,
    created_at TEXT,
    updated_at TEXT,
    deal TEXT,
    property TEXT,
    city TEXT,
    status TEXT,
    username TEXT
)
""")
conn.commit()

# =========================
# GLOBALS
# =========================

users = {}
REQUEST_COUNTER = 0

STATUS_MAP = {
    "search": "🟡 В пошуках",
    "reserve": "🟢 Мають резервацію",
    "deal_closed": "🔴 Закрили угоду",
    "self_found": "🔵 Самі знайшли",
    "other_broker": "🟠 Знайшов чужий маклер",
    "not_looking": "⚫️ Не шукають вже",
}

# =========================
# HELPERS
# =========================

def status_keyboard(req_id: int):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🟡 В пошуках", callback_data=f"status_search_{req_id}"),
                InlineKeyboardButton("🟢 Мають резервацію", callback_data=f"status_reserve_{req_id}"),
            ],
            [
                InlineKeyboardButton("🔵 Самі знайшли", callback_data=f"status_self_found_{req_id}"),
                InlineKeyboardButton("🟠 Чужий маклер", callback_data=f"status_other_broker_{req_id}"),
            ],
            [
                InlineKeyboardButton("⚫️ Не шукають", callback_data=f"status_not_looking_{req_id}"),
                InlineKeyboardButton("🔴 Закрили угоду", callback_data=f"status_deal_closed_{req_id}"),
            ],
        ]
    )


def build_summary(u):
    username = f"@{u['username']}" if u["username"] else "—"

    return (
        f"📋 *Запит №{u['req_id']}*\n"
        f"📌 Статус: {STATUS_MAP['search']}\n\n"
        f"👤 Імʼя: {u['name']}\n"
        f"🆔 Telegram: {username}\n"
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

# =========================
# START / RESET
# =========================

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users.pop(update.effective_user.id, None)

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🏠 Оренда", callback_data="deal_rent")],
            [InlineKeyboardButton("🏡 Купівля", callback_data="deal_buy")],
        ]
    )

    await update.message.reply_text(
        "👋 Вітаємо!\n\nЩо вас цікавить?",
        reply_markup=kb,
    )


async def reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users.pop(update.effective_user.id, None)
    await update.message.reply_text(
        "🔄 Запит скинуто.\nНатисніть /start щоб почати заново.",
        reply_markup=ReplyKeyboardRemove(),
    )

# =========================
# DEAL / PROPERTY
# =========================

async def deal_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(None)

    users[q.from_user.id] = {
        "deal": "Оренда" if q.data == "deal_rent" else "Купівля",
        "step": "property",
        "username": q.from_user.username,
    }

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛏 Ліжко-місце", callback_data="prop_Ліжко-місце")],
            [InlineKeyboardButton("🏢 Студія", callback_data="prop_Студія")],
            [InlineKeyboardButton("1️⃣ 1-кімнатна", callback_data="prop_1-кімнатна")],
            [InlineKeyboardButton("2️⃣ 2-кімнатна", callback_data="prop_2-кімнатна")],
            [InlineKeyboardButton("3️⃣ 3-кімнатна", callback_data="prop_3-кімнатна")],
            [InlineKeyboardButton("🏠 Будинок", callback_data="prop_Будинок")],
            [InlineKeyboardButton("✍️ Свій варіант", callback_data="prop_custom")],
        ]
    )

    await q.message.reply_text("🏡 Тип житла:", reply_markup=kb)


async def property_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(None)

    u = users[q.from_user.id]

    if q.data == "prop_custom":
        u["step"] = "property_custom"
        await q.message.reply_text("✍️ Напишіть тип житла вручну:")
    else:
        u["property"] = q.data.replace("prop_", "")
        u["step"] = "city"
        await q.message.reply_text("📍 В якому місті шукаєте житло?")

# =========================
# TEXT FLOW (АНКЕТА)
# =========================

async def text_handler(update: Update, ctx):
    uid = update.effective_user.id
    if uid not in users:
        return

    u = users[uid]
    t = update.message.text

    step = u["step"]

    if step == "property_custom":
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
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Так", callback_data="park_yes")],
                [InlineKeyboardButton("Ні", callback_data="park_no")],
                [InlineKeyboardButton("Пізніше", callback_data="park_later")],
            ]
        )
        await update.message.reply_text("🚗 Чи потрібне паркування?", reply_markup=kb)

    elif step == "move_in":
        u["move_in"] = t
        u["step"] = "budget"
        await update.message.reply_text("💶 Який бюджет на оренду в місяць (від–до €)?")

    elif step == "budget":
        u["budget"] = t
        u["step"] = "view_time"
        await update.message.reply_text("⏰ Коли ви доступні для оглядів?")

    elif step == "view_time":
        u["view_time"] = t
        u["step"] = "location"
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc_ua")],
                [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc_sk")],
                [InlineKeyboardButton("✍️ Інша країна", callback_data="loc_custom")],
            ]
        )
        await update.message.reply_text("🌍 Де ви зараз?", reply_markup=kb)

    elif step == "custom_location":
        u["location"] = t
        u["step"] = "view_format"
        await ask_view_format(update.message)

    elif step == "name":
        global REQUEST_COUNTER
        REQUEST_COUNTER += 1
        u["req_id"] = REQUEST_COUNTER
        u["name"] = t

        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("✅ Так", callback_data="confirm_yes")],
                [InlineKeyboardButton("❌ Ні", callback_data="confirm_no")],
            ]
        )

        await update.message.reply_text(
            build_summary(u) + "\n\nВсе вірно?",
            parse_mode="Markdown",
            reply_markup=kb,
        )

# =========================
# INLINE HANDLERS
# =========================

async def parking_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(None)

    u = users[q.from_user.id]
    u["parking"] = {"park_yes": "Так", "park_no": "Ні", "park_later": "Пізніше"}[q.data]
    u["step"] = "move_in"

    await q.message.reply_text("📅 Яка найкраща дата для заїзду?")


async def location_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(None)

    u = users[q.from_user.id]

    if q.data == "loc_custom":
        u["step"] = "custom_location"
        await q.message.reply_text("✍️ Напишіть країну:")
    else:
        u["location"] = "Україна" if q.data == "loc_ua" else "Словаччина"
        u["step"] = "view_format"
        await ask_view_format(q.message)


async def ask_view_format(msg):
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💻 Онлайн", callback_data="view_online")],
            [InlineKeyboardButton("🚶 Фізичний", callback_data="view_offline")],
            [InlineKeyboardButton("🔁 Обидва", callback_data="view_both")],
        ]
    )
    await msg.reply_text("👀 Формат огляду?", reply_markup=kb)


async def view_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(None)

    u = users[q.from_user.id]
    u["view_format"] = {
        "view_online": "Онлайн",
        "view_offline": "Фізичний",
        "view_both": "Обидва",
    }[q.data]

    u["step"] = "contact"

    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Поділитись контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await q.message.reply_text("📞 Поділіться контактом:", reply_markup=kb)


async def contact_handler(update: Update, ctx):
    u = users[update.effective_user.id]
    u["phone"] = update.message.contact.phone_number
    u["step"] = "name"

    await update.message.reply_text("👤 Як до вас можемо звертатись?")

# =========================
# CONFIRM / SAVE
# =========================

async def confirm_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(None)

    if q.data == "confirm_no":
        users.pop(q.from_user.id, None)
        await q.message.reply_text("❌ Запит скасовано.")
        return

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Так", callback_data="terms_yes")],
            [InlineKeyboardButton("❌ Ні", callback_data="terms_no")],
        ]
    )

    await q.message.reply_text(
        "ℹ️ *Умови співпраці:*\n\n"
        "• депозит може дорівнювати орендній платі\n"
        "• оплачується повна або часткова комісія ріелтору\n"
        "• можливий подвійний депозит при дітях або тваринах\n\n"
        "Чи погоджуєтесь?",
        parse_mode="Markdown",
        reply_markup=kb,
    )


async def terms_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(None)

    u = users[q.from_user.id]

    # SAVE TO DB
    cursor.execute(
        """
        INSERT INTO requests (
            id, created_at, updated_at,
            deal, property, city, status, username
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            u["req_id"],
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            u["deal"],
            u["property"],
            u["city"],
            STATUS_MAP["search"],
            u["username"],
        ),
    )
    conn.commit()

    await ctx.bot.send_message(
        ADMIN_GROUP_ID,
        build_summary(u),
        parse_mode="Markdown",
        reply_markup=status_keyboard(u["req_id"]),
    )

    await q.message.reply_text(
        "✅ Запит відправлено маклеру.\n"
        "Ми звʼяжемось з вами протягом **24–48 годин**.",
        parse_mode="Markdown",
    )

    users.pop(q.from_user.id, None)

# =========================
# STATUS UPDATE
# =========================

async def status_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()

    _, status_key, req_id = q.data.split("_")
    new_status = STATUS_MAP.get(status_key)
    if not new_status:
        return

    # update DB
    cursor.execute(
        """
        UPDATE requests
        SET status = ?, updated_at = ?
        WHERE id = ?
        """,
        (new_status, datetime.now().isoformat(), int(req_id)),
    )
    conn.commit()

    # update message
    lines = q.message.text.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("📌 Статус:"):
            lines[i] = f"📌 Статус: {new_status}"
            break

    await q.message.edit_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=q.message.reply_markup,
    )

# =========================
# STATISTICS
# =========================

def get_stats(days: int):
    since = datetime.now() - timedelta(days=days)

    cursor.execute(
        """
        SELECT property, COUNT(*)
        FROM requests
        WHERE created_at >= ?
          AND status = ?
        GROUP BY property
        ORDER BY COUNT(*) DESC
        """,
        (since.isoformat(), STATUS_MAP["search"]),
    )

    rows = cursor.fetchall()
    total = sum(count for _, count in rows)
    return rows, total


async def stats_today(update: Update, ctx):
    rows, total = get_stats(1)
    text = "📊 *Статистика (сьогодні)*\n\n"
    for prop, count in rows:
        text += f"🏠 {prop} — {count}\n"
    text += f"\n🟡 Активних запитів: {total}"
    await update.message.reply_text(text, parse_mode="Markdown")


async def stats_week(update: Update, ctx):
    rows, total = get_stats(7)
    text = "📊 *Статистика (7 днів)*\n\n"
    for prop, count in rows:
        text += f"🏠 {prop} — {count}\n"
    text += f"\n🟡 Активних запитів: {total}"
    await update.message.reply_text(text, parse_mode="Markdown")


async def stats_month(update: Update, ctx):
    rows, total = get_stats(30)
    text = "📊 *Статистика (30 днів)*\n\n"
    for prop, count in rows:
        text += f"🏠 {prop} — {count}\n"
    text += f"\n🟡 Активних запитів: {total}"
    await update.message.reply_text(text, parse_mode="Markdown")

# =========================
# MAIN
# =========================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))

    app.add_handler(CommandHandler("stats_today", stats_today))
    app.add_handler(CommandHandler("stats_week", stats_week))
    app.add_handler(CommandHandler("stats_month", stats_month))

    app.add_handler(CallbackQueryHandler(deal_handler, pattern="^deal_"))
    app.add_handler(CallbackQueryHandler(property_handler, pattern="^prop_"))
    app.add_handler(CallbackQueryHandler(parking_handler, pattern="^park_"))
    app.add_handler(CallbackQueryHandler(location_handler, pattern="^loc_"))
    app.add_handler(CallbackQueryHandler(view_handler, pattern="^view_"))
    app.add_handler(CallbackQueryHandler(confirm_handler, pattern="^confirm_"))
    app.add_handler(CallbackQueryHandler(terms_handler, pattern="^terms_"))
    app.add_handler(CallbackQueryHandler(status_handler, pattern="^status_"))

    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
