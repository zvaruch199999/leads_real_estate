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

# тимчасове сховище станів
users = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏠 Оренда", callback_data="rent")],
        [InlineKeyboardButton("🏡 Купівля", callback_data="buy")]
    ]
    await update.message.reply_text(
        "Привіт! 👋\nВи шукаєте житло:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def deal_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    users[uid] = {
        "user_id": uid,
        "username": f"@{query.from_user.username}" if query.from_user.username else "немає",
        "deal_type": "Оренда" if query.data == "rent" else "Купівля",
        "step": "property_type"
    }

    keyboard = [
        [InlineKeyboardButton("Студія", callback_data="Студія")],
        [InlineKeyboardButton("1-кімнатна", callback_data="1-кімнатна")],
        [InlineKeyboardButton("2-кімнатна", callback_data="2-кімнатна")],
        [InlineKeyboardButton("Дім", callback_data="Дім")]
    ]

    await query.message.reply_text(
        "Який тип житла вас цікавить?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def property_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    users[uid]["property_type"] = query.data
    users[uid]["step"] = "city"

    await query.message.reply_text("В якому місті шукаєте житло?")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text

    if uid not in users:
        return

    step = users[uid]["step"]

    if step == "city":
        users[uid]["city"] = text
        users[uid]["step"] = "district"
        await update.message.reply_text("Який район?")

    elif step == "district":
        users[uid]["district"] = text
        users[uid]["step"] = "budget"
        await update.message.reply_text("Який бюджет (від–до)?")

    elif step == "budget":
        users[uid]["budget"] = text
        users[uid]["step"] = "contact"

        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("📞 Поділитись номером", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await update.message.reply_text(
            "Поділіться номером телефону для звʼязку:",
            reply_markup=keyboard
        )


async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    contact = update.message.contact.phone_number

    users[uid]["phone"] = contact

    text = (
        "📥 НОВИЙ ЗАПИТ\n\n"
        f"👤 Клієнт: {users[uid]['username']}\n"
        f"📞 Телефон: {contact}\n"
        f"📌 Тип: {users[uid]['deal_type']}\n"
        f"🏠 Житло: {users[uid]['property_type']}\n"
        f"📍 Локація: {users[uid]['city']} / {users[uid]['district']}\n"
        f"💰 Бюджет: {users[uid]['budget']}"
    )

    await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=text)

    await update.message.reply_text(
        "Дякуємо! 🙌\nМи зв’яжемося з вами протягом 24–48 годин.",
        reply_markup=None
    )

    users.pop(uid, None)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(deal_type, pattern="^(rent|buy)$"))
    app.add_handler(CallbackQueryHandler(property_type))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
