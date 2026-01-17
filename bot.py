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

from config import BOT_TOKEN, ADMIN_GROUP_ID

# ================== STORAGE ==================
users = {}
REQUEST_COUNTER = 0

# ================== MAPS ==================
PROPERTY_MAP = {
    "bed": "Ліжко-місце",
    "studio": "Студія",
    "1": "1-кімнатна",
    "2": "2-кімнатна",
    "3": "3-кімнатна",
    "house": "Будинок",
}

PARKING_MAP = {
    "yes": "Так",
    "no": "Ні",
    "later": "Пізніше",
}

VIEW_MAP = {
    "online": "Онлайн",
    "offline": "Фізичний",
    "both": "Обидва варіанти",
}

LOCATION_MAP = {
    "ua": "Україна",
    "sk": "Словаччина",
}

STATUS_MAP = {
    "search": "🟡 В пошуках",
    "found": "🟢 Знайдено",
    "closed": "🔴 Закрито",
}

# ================== HELPERS ==================
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

def status_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🟡 В пошуках", callback_data="status_search"),
                InlineKeyboardButton("🟢 Знайдено", callback_data="status_found"),
            ],
            [InlineKeyboardButton("🔴 Закрито", callback_data="status_closed")],
        ]
    )

# ================== START ==================
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
    await update.message.reply_text("👋 Що вас цікавить?", reply_markup=kb)

# ================== DEAL ==================
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
        ]
    )
    await q.message.reply_text("🏡 Тип житла:", reply_markup=kb)

# ================== PROPERTY ==================
async def property_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(None)

    u = users[q.from_user.id]
    key = q.data.replace("prop_", "")
    u["property"] = PROPERTY_MAP[key]
    u["step"] = "city"

    await q.message.reply_text("📍 В якому місті шукаєте житло?")

# ================== TEXT FLOW ==================
async def text_handler(update: Update, ctx):
    uid = update.effective_user.id
    if uid not in users:
        return

    u = users[uid]
    t = update.message.text

    if u["step"] == "city":
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
            ]
        )
        await update.message.reply_text("🌍 Де ви зараз?", reply_markup=kb)

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

# ================== PARKING ==================
async def parking_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(None)

    u = users[q.from_user.id]
    u["parking"] = PARKING_MAP[q.data.replace("park_", "")]
    u["step"] = "move_in"
    await q.message.reply_text("📅 Коли плануєте заїзд?")

# ================== LOCATION ==================
async def location_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(None)

    u = users[q.from_user.id]
    u["location"] = LOCATION_MAP[q.data.replace("loc_", "")]
    u["step"] = "view_format"

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💻 Онлайн", callback_data="view_online")],
            [InlineKeyboardButton("🚶 Фізичний", callback_data="view_offline")],
            [InlineKeyboardButton("🔁 Обидва", callback_data="view_both")],
        ]
    )
    await q.message.reply_text("👀 Формат огляду?", reply_markup=kb)

# ================== VIEW ==================
async def view_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(None)

    u = users[q.from_user.id]
    u["view_format"] = VIEW_MAP[q.data.replace("view_", "")]
    u["step"] = "contact"

    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Поділитись контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await q.message.reply_text("📞 Поділіться контактом:", reply_markup=kb)

# ================== CONTACT ==================
async def contact_handler(update: Update, ctx):
    u = users[update.effective_user.id]
    u["phone"] = update.message.contact.phone_number
    u["step"] = "name"
    await update.message.reply_text("👤 Як до вас можемо звертатись?")

# ================== CONFIRM ==================
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
        "• депозит = 1 орендна плата\n"
        "• комісія ріелтору\n"
        "• можливий подвійний депозит при дітях або тваринах\n\n"
        "Погоджуєтесь?",
        reply_markup=kb,
        parse_mode="Markdown",
    )

# ================== TERMS ==================
async def terms_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(None)

    if q.data == "terms_no":
        users.pop(q.from_user.id, None)
        await q.message.reply_text("❌ Роботу завершено.")
        return

    u = users[q.from_user.id]

    msg = await ctx.bot.send_message(
        ADMIN_GROUP_ID,
        build_summary(u),
        reply_markup=status_keyboard(),
        parse_mode="Markdown",
    )

    u["admin_msg_id"] = msg.message_id

    await q.message.reply_text(
        "✅ Запит відправлено маклеру.\n"
        "Ми звʼяжемось з вами протягом **24–48 годин**.",
        parse_mode="Markdown",
    )

# ================== STATUS ==================
async def status_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()

    status_key = q.data.replace("status_", "")
    text = STATUS_MAP[status_key]

    await q.message.edit_text(
        q.message.text.split("\n")[0] + f"\n📌 Статус: {text}",
        reply_markup=status_keyboard(),
        parse_mode="Markdown",
    )

# ================== MAIN ==================
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
