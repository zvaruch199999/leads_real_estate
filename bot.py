from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from config import BOT_TOKEN, ADMIN_GROUP_ID

users = {}

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏠 Оренда", callback_data="deal_rent")],
        [InlineKeyboardButton("🏡 Купівля", callback_data="deal_buy")]
    ]
    await update.message.reply_text(
        "Привіт 👋\nВи шукаєте житло:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- DEAL TYPE ----------------
async def deal_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    users[uid] = {
        "username": f"@{q.from_user.username}" if q.from_user.username else "немає",
        "deal_type": "Оренда" if q.data == "deal_rent" else "Купівля",
        "step": "property_type"
    }

    keyboard = [
        [InlineKeyboardButton("Ліжко-місце", callback_data="type_Ліжко-місце")],
        [InlineKeyboardButton("Кімната", callback_data="type_Кімната")],
        [InlineKeyboardButton("Студія", callback_data="type_Студія")],
        [InlineKeyboardButton("1-кімнатна", callback_data="type_1-кімнатна")],
        [InlineKeyboardButton("2-кімнатна", callback_data="type_2-кімнатна")],
        [InlineKeyboardButton("3-кімнатна", callback_data="type_3-кімнатна")],
        [InlineKeyboardButton("4-кімнатна", callback_data="type_4-кімнатна")],
        [InlineKeyboardButton("5-кімнатна", callback_data="type_5-кімнатна")],
        [InlineKeyboardButton("Будинок", callback_data="type_Будинок")],
        [InlineKeyboardButton("✍️ Свій варіант", callback_data="type_custom")]
    ]

    await q.message.reply_text(
        "Який тип житла вас цікавить?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- PROPERTY TYPE ----------------
async def property_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == "type_custom":
        users[uid]["step"] = "custom_property"
        await q.message.reply_text("Опишіть тип житла:")
    else:
        users[uid]["property_type"] = q.data.replace("type_", "")
        users[uid]["step"] = "city"
        await q.message.reply_text("В якому місті шукаєте житло?")

# ---------------- PETS ----------------
async def pets_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == "pets_yes":
        users[uid]["pets"] = "Так"
        users[uid]["step"] = "pets_details"
        await q.message.reply_text(
            "Розпишіть, будь ласка, тваринку(и):\n"
            "(вид, кількість, розмір)"
        )
    else:
        users[uid]["pets"] = "Ні"
        users[uid]["step"] = "parking"
        await ask_parking(q.message)

# ---------------- PARKING ----------------
async def parking_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    users[uid]["parking"] = q.data.replace("parking_", "")
    users[uid]["step"] = "move_in"
    await q.message.reply_text("Яка найкраща дата для вашого заїзду?")

async def ask_parking(message):
    keyboard = [
        [InlineKeyboardButton("Так", callback_data="parking_Так")],
        [InlineKeyboardButton("Ні", callback_data="parking_Ні")],
        [InlineKeyboardButton("Пізніше", callback_data="parking_Пізніше")]
    ]
    await message.reply_text(
        "Чи потрібне паркування?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- VIEWING FORMAT ----------------
async def viewing_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    users[uid]["viewing_format"] = q.data
    users[uid]["step"] = "contact"

    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Поділитись контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await q.message.reply_text(
        "Поділіться контактом для звʼязку:",
        reply_markup=keyboard
    )

# ---------------- CONTACT ----------------
async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    users[uid]["phone"] = update.message.contact.phone_number
    users[uid]["step"] = "confirm_data"

    await update.message.reply_text(
        build_summary(users[uid]) +
        "\n\nВсе вірно?\nНапишіть **Так** або **Ні**."
    )

# ---------------- TEXT FLOW ----------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text

    if uid not in users:
        return

    step = users[uid]["step"]

    if step == "custom_property":
        users[uid]["property_type"] = text
        users[uid]["step"] = "city"
        await update.message.reply_text("В якому місті шукаєте житло?")

    elif step == "city":
        users[uid]["city"] = text
        users[uid]["step"] = "district"
        await update.message.reply_text("Який район?")

    elif step == "district":
        users[uid]["district"] = text
        users[uid]["step"] = "for_whom"
        await update.message.reply_text("Розпишіть, для кого шукаєте житло:")

    elif step == "for_whom":
        users[uid]["for_whom"] = text
        users[uid]["step"] = "occupation"
        await update.message.reply_text("Чим ви займаєтесь? Діяльність:")

    elif step == "occupation":
        users[uid]["occupation"] = text
        users[uid]["step"] = "children"
        await update.message.reply_text(
            "Чи маєте дітей?\n"
            "Якщо так — напишіть вік та стать.\n"
            "Якщо ні — напишіть «Ні»."
        )

    elif step == "children":
        users[uid]["children"] = text
        users[uid]["step"] = "pets"
        keyboard = [
            [InlineKeyboardButton("Так", callback_data="pets_yes")],
            [InlineKeyboardButton("Ні", callback_data="pets_no")]
        ]
        await update.message.reply_text(
            "Чи маєте тваринок?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif step == "pets_details":
        users[uid]["pets_details"] = text
        users[uid]["step"] = "parking"
        await ask_parking(update.message)

    elif step == "move_in":
        users[uid]["move_in"] = text
        users[uid]["step"] = "budget"
        await update.message.reply_text("Який бюджет (від–до) €?")

    elif step == "budget":
        users[uid]["budget"] = text
        users[uid]["step"] = "viewing_time"
        await update.message.reply_text("Як зазвичай ви доступні для оглядів?")

    elif step == "viewing_time":
        users[uid]["viewing_time"] = text
        users[uid]["step"] = "location"
        keyboard = [
            [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc_Україна")],
            [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc_Словаччина")],
            [InlineKeyboardButton("✍️ Інша країна", callback_data="loc_custom")]
        ]
        await update.message.reply_text(
            "Де ви зараз знаходитесь?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif step == "custom_location":
        users[uid]["current_location"] = text
        users[uid]["step"] = "viewing_format"
        await ask_viewing_format(update.message)

    elif step == "confirm_data":
        if text.lower().startswith("так"):
            users[uid]["step"] = "confirm_terms"
            await update.message.reply_text(
                "ℹ️ Важливо:\n\n"
                "• при оренді оплачується депозит (зазвичай = орендній платі)\n"
                "• комісія ріелтору — повна або часткова\n"
                "• при дітях або тваринках можливий подвійний депозит\n\n"
                "Чи погоджуєтесь з цими умовами?\n"
                "Напишіть **Так** або **Ні**."
            )
        else:
            await update.message.reply_text("Добре, ви можете почати заново /start")
            users.pop(uid, None)

    elif step == "confirm_terms":
        if text.lower().startswith("так"):
            await context.bot.send_message(
                ADMIN_GROUP_ID,
                build_admin_message(users[uid])
            )
            await update.message.reply_text(
                "✅ Запит відправлено маклеру.\n"
                "Ми звʼяжемося з вами протягом **24–48 годин**, "
                "щоб запропонувати відповідні варіанти."
            )
        else:
            await update.message.reply_text("Добре, без підтвердження ми не можемо працювати.")
        users.pop(uid, None)

# ---------------- HELPERS ----------------
async def ask_viewing_format(message):
    keyboard = [
        [InlineKeyboardButton("💻 Онлайн", callback_data="view_online")],
        [InlineKeyboardButton("🚶 Фізичний", callback_data="view_physical")],
        [InlineKeyboardButton("🔁 Обидва", callback_data="view_both")]
    ]
    await message.reply_text(
        "Який формат огляду вам підходить?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def build_summary(u):
    return (
        "🔎 **Ваш запит:**\n\n"
        f"Тип угоди: {u['deal_type']}\n"
        f"Житло: {u['property_type']}\n"
        f"Місто: {u.get('city','')}\n"
        f"Район: {u.get('district','')}\n"
        f"Для кого: {u.get('for_whom','')}\n"
        f"Діяльність: {u.get('occupation','')}\n"
        f"Діти: {u.get('children','')}\n"
        f"Тварини: {u.get('pets','')} {u.get('pets_details','')}\n"
        f"Паркування: {u.get('parking','')}\n"
        f"Заїзд: {u.get('move_in','')}\n"
        f"Бюджет: {u.get('budget','')}\n"
        f"Огляди: {u.get('viewing_time','')}\n"
    )

def build_admin_message(u):
    return (
        "📥 НОВИЙ ЗАПИТ\n\n" +
        build_summary(u) +
        f"\nКонтакт: {u['phone']}\n"
        f"Username: {u['username']}"
    )

# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(deal_type, pattern="^deal_"))
    app.add_handler(CallbackQueryHandler(property_type, pattern="^type_"))
    app.add_handler(CallbackQueryHandler(pets_handler, pattern="^pets_"))
    app.add_handler(CallbackQueryHandler(parking_handler, pattern="^parking_"))
    app.add_handler(CallbackQueryHandler(viewing_format, pattern="^view_"))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling()

if __name__ == "__main__":
    main()
