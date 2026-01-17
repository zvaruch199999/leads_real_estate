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

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏠 Оренда", callback_data="rent")],
        [InlineKeyboardButton("🏡 Купівля", callback_data="buy")]
    ]
    await update.message.reply_text(
        "Привіт! 👋\nВи шукаєте житло:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- DEAL TYPE ----------
async def deal_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    users[uid] = {
        "username": f"@{q.from_user.username}" if q.from_user.username else "немає",
        "deal_type": "Оренда" if q.data == "rent" else "Купівля",
        "step": "property_type"
    }

    keyboard = [
        [InlineKeyboardButton("Ліжко-місце", callback_data="Ліжко-місце")],
        [InlineKeyboardButton("Кімната", callback_data="Кімната")],
        [InlineKeyboardButton("Студія", callback_data="Студія")],
        [InlineKeyboardButton("1-кімнатна", callback_data="1-кімнатна")],
        [InlineKeyboardButton("2-кімнатна", callback_data="2-кімнатна")],
        [InlineKeyboardButton("3-кімнатна", callback_data="3-кімнатна")],
        [InlineKeyboardButton("4-кімнатна", callback_data="4-кімнатна")],
        [InlineKeyboardButton("5-кімнатна", callback_data="5-кімнатна")],
        [InlineKeyboardButton("Будинок", callback_data="Будинок")],
        [InlineKeyboardButton("✍️ Свій варіант", callback_data="custom")]
    ]

    await q.message.reply_text(
        "Який тип житла вас цікавить?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- PROPERTY TYPE ----------
async def property_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == "custom":
        users[uid]["step"] = "custom_property"
        await q.message.reply_text("Опишіть тип житла:")
    else:
        users[uid]["property_type"] = q.data
        users[uid]["step"] = "city"
        await q.message.reply_text("В якому місті шукаєте житло?")

# ---------- PARKING ----------
async def parking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    users[uid]["parking"] = q.data.replace("parking_", "")
    users[uid]["step"] = "move_in"

    # ❗ ВАЖЛИВО: одразу наступне питання
    await q.message.reply_text("Яка найкраща дата для вашого заїзду?")

# ---------- VIEWING FORMAT ----------
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

# ---------- CONTACT ----------
async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    users[uid]["phone"] = update.message.contact.phone_number
    users[uid]["step"] = "summary"

    await update.message.reply_text(
        "Все вірно? Напишіть **Так** або **Ні**."
    )

# ---------- TEXT HANDLER ----------
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
            "Чи маєте дітей?\nЯкщо так — напишіть вік та стать.\nЯкщо ні — напишіть «Ні»."
        )

    elif step == "children":
        users[uid]["children"] = text
        users[uid]["step"] = "parking"
        keyboard = [
            [InlineKeyboardButton("Так", callback_data="parking_yes")],
            [InlineKeyboardButton("Ні", callback_data="parking_no")],
            [InlineKeyboardButton("Пізніше", callback_data="parking_later")]
        ]
        await update.message.reply_text(
            "Чи потрібне паркування?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

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
        users[uid]["step"] = "viewing_format"
        keyboard = [
            [InlineKeyboardButton("💻 Онлайн", callback_data="online")],
            [InlineKeyboardButton("🚶 Фізичний", callback_data="offline")],
            [InlineKeyboardButton("🔁 Обидва", callback_data="both")]
        ]
        await update.message.reply_text(
            "Який формат огляду вам підходить?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif step == "summary":
        if text.lower().startswith("так"):
            await context.bot.send_message(
                ADMIN_GROUP_ID,
                f"📥 НОВИЙ ЗАПИТ\n"
                f"👤 {users[uid]['username']}\n"
                f"📞 {users[uid]['phone']}"
            )
            await update.message.reply_text(
                "✅ Запит відправлено маклеру.\n"
                "Ми звʼяжемося з вами протягом 24–48 годин."
            )
        else:
            await update.message.reply_text("Запит скасовано.")

        users.pop(uid, None)

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(deal_type, pattern="^(rent|buy)$"))
    app.add_handler(CallbackQueryHandler(property_type))
    app.add_handler(CallbackQueryHandler(parking, pattern="^parking_"))
    app.add_handler(CallbackQueryHandler(viewing_format, pattern="^(online|offline|both)$"))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling()

if __name__ == "__main__":
    main()
