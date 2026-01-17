from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
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

users = {}
REQUEST_COUNTER = 0

# =========================
# MAPS
# =========================

PROPERTY_MAP = {
    "bed": "Ліжко-місце",
    "studio": "Студія",
    "1": "1-кімнатна",
    "2": "2-кімнатна",
    "3": "3-кімнатна",
    "house": "Будинок",
}

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

def status_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🟡 В пошуках", callback_data="status_search"),
                InlineKeyboardButton("🟢 Мають резервацію", callback_data="status_reserve"),
            ],
            [
                InlineKeyboardButton("🔵 Самі знайшли", callback_data="status_self_found"),
                InlineKeyboardButton("🟠 Чужий маклер", callback_data="status_other_broker"),
            ],
            [
                InlineKeyboardButton("⚫️ Не шукають", callback_data="status_not_looking"),
                InlineKeyboardButton("🔴 Закрили угоду", callback_data="status_deal_closed"),
            ],
        ]
    )


def build_summary(u):
    return (
        f"📋 **Запит №{u['req_id']}**\n"
        f"📌 Статус: {u['status']}\n\n"
        f"👤 Імʼя: {u['name']}\n"
        f"🆔 Telegram: @{u['username']}\n"
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
        f"💶 Бюджет: {u['budget']}\n"
        f"⏰ Огляди: {u['view_time']}\n"
        f"🌍 Зараз: {u['location']}\n"
        f"👀 Формат огляду: {u['view_format']}"
    )

# =========================
# START
# =========================

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id] = {
        "step": "deal",
        "username": update.effective_user.username or "немає",
    }

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🏠 Оренда", callback_data="rent")],
            [InlineKeyboardButton("🏡 Купівля", callback_data="buy")],
        ]
    )

    await update.message.reply_text(
        "👋 Вітаємо!\nЩо вас цікавить?",
        reply_markup=kb,
    )

# =========================
# DEAL
# =========================

async def deal_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(None)

    u = users[q.from_user.id]
    u["deal"] = "Оренда" if q.data == "rent" else "Купівля"
    u["step"] = "property"

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛏 Ліжко-місце", callback_data="prop_bed")],
            [InlineKeyboardButton("Студія", callback_data="prop_studio")],
            [InlineKeyboardButton("1-кімнатна", callback_data="prop_1")],
            [InlineKeyboardButton("2-кімнатна", callback_data="prop_2")],
            [InlineKeyboardButton("3-кімнатна", callback_data="prop_3")],
            [InlineKeyboardButton("Будинок", callback_data="prop_house")],
            [InlineKeyboardButton("✍️ Свій варіант", callback_data="prop_custom")],
        ]
    )

    await q.message.reply_text("🏡 Тип житла:", reply_markup=kb)

# =========================
# PROPERTY
# =========================

async def property_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(None)

    u = users[q.from_user.id]

    if q.data == "prop_custom":
        u["step"] = "property_custom"
        await q.message.reply_text("✍️ Напишіть свій варіант житла:")
        return

    key = q.data.replace("prop_", "")
    u["property"] = PROPERTY_MAP[key]
    u["step"] = "city"

    await q.message.reply_text("📍 В якому місті шукаєте житло?")

# =========================
# TEXT FLOW
# =========================

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
        await update.message.reply_text("🧒 Чи маєте дітей? Якщо ні — напишіть «Ні».")

    elif u["step"] == "children":
        u["children"] = t
        u["step"] = "pets"
        await update.message.reply_text(
            "🐾 Чи маєте тваринок?\n"
            "Якщо так — напишіть яку і коротко про неї.\n"
            "Якщо ні — напишіть «Ні»."
        )

    elif u["step"] == "pets":
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

    elif u["step"] == "move_in":
        u["move_in"] = t
        u["step"] = "budget"
        await update.message.reply_text("💶 Який бюджет (від–до) €?")

    elif u["step"] == "budget":
        u["budget"] = t
        u["step"] = "view_time"
        await update.message.reply_text("⏰ Коли ви доступні для оглядів?")

    elif u["step"] == "view_time":
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

    elif u["step"] == "custom_location":
        u["location"] = t
        u["step"] = "view_format"
        await ask_view_format(update.message)

    elif u["step"] == "name":
        global REQUEST_COUNTER
        REQUEST_COUNTER += 1

        u["name"] = t
        u["req_id"] = REQUEST_COUNTER
        u["status"] = STATUS_MAP["search"]

        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("✅ Так", callback_data="confirm_yes")],
                [InlineKeyboardButton("❌ Ні", callback_data="confirm_no")],
            ]
        )

        await update.message.reply_text(
            build_summary(u) + "\n\nВсе вірно?",
            reply_markup=kb,
            parse_mode="Markdown",
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
        "ℹ️ **Умови співпраці:**\n\n"
        "• депозит = орендна плата\n"
        "• комісія ріелтору\n"
        "• можливий подвійний депозит при дітях або тваринах\n\n"
        "Чи погоджуєтесь?",
        reply_markup=kb,
        parse_mode="Markdown",
    )


async def terms_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(None)

    u = users[q.from_user.id]

    msg = await ctx.bot.send_message(
        ADMIN_GROUP_ID,
        build_summary(u),
        reply_markup=status_keyboard(),
        parse_mode="Markdown",
    )

    await q.message.reply_text(
        "✅ Запит відправлено маклеру.\n"
        "Ми звʼяжемось з вами протягом **24–48 годин**.",
        parse_mode="Markdown",
    )

# =========================
# STATUS CHANGE
# =========================

async def status_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()

    status_key = q.data.replace("status_", "")
    new_status = STATUS_MAP[status_key]

    lines = q.message.text.split("\n")
    lines[1] = f"📌 Статус: {new_status}"

    await q.message.edit_text(
        "\n".join(lines),
        reply_markup=status_keyboard(),
        parse_mode="Markdown",
    )

# =========================
# MAIN
# =========================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(deal_handler, pattern="^(rent|buy)$"))
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
