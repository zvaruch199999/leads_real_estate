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
from db import save_lead

user_data = {}


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

    user_data[query.from_user.id] = {
        "user_id": query.from_user.id,
        "username": f"@{query.from_user.username}" if query.from_user.username else "немає",
        "deal_type": query.data
    }

    keyboard = [
        [InlineKeyboardButton("Студія", callback_data="Студія")],
        [InlineKeyboardButton("1-кімнатна", callback_data="1к")],
        [InlineKeyboardButton("2-кімнатна", callback_data="2к")],
        [InlineKeyboardButton("Дім", callback_data="Дім")]
    ]

    await query.message.reply_text(
        "Який тип житла вас цікавить?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def property_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_data[query.from_user.id]["property_type"] = query.data
    await query.message.reply_text("В якому місті шукаєте житло?")


async def city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.message.from_user.id]["city"] = update.message.text
    await update.message.reply_text("Який район?")


async def district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.message.from_user.id]["district"] = update.message.text
    await update.message.reply_text("Який бюджет (від–до)?")


async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.message.from_user.id]["budget"] = update.message.text

    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Поділитись номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await update.message.reply_text(
        "Будь ласка, поділіться номером телефону для звʼязку:",
        reply_markup=keyboard
    )


async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    uid = update.message.from_user.id

    user_data[uid]["phone"] = contact.phone_number

    save_lead(user_data[uid])

    text = (
        "📥 НОВИЙ ЗАПИТ\n\n"
        f"👤 Клієнт: {user_data[uid]['username']}\n"
        f"📞 Телефон: {contact.phone_number}\n"
        f"🏠 Тип: {user_data[uid]['property_type']}\n"
        f"📍 Локація: {user_data[uid]['city']} / {user_data[uid]['district']}\n"
        f"💰 Бюджет: {user_data[uid]['budget']}"
    )

    await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=text)

    await update.message.reply_text(
        "Дякуємо! 🙌\nМи зв’яжемося з вами протягом 24–48 годин.",
        reply_markup=None
    )


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(deal_type, pattern="^(rent|buy)$"))
    app.add_handler(CallbackQueryHandler(property_type))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, city))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, district))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, budget))
    app.add_handler(MessageHandler(filters.CONTACT, contact))

    app.run_polling()


if __name__ == "__main__":
    main()
