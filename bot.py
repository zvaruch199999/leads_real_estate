from telegram import *
from telegram.ext import *
from config import BOT_TOKEN, ADMIN_GROUP_ID

users = {}
REQUESTS = {}
REQUEST_COUNTER = 0

STATUS_MAP = {
    "search": "🟡 В пошуках",
    "done": "🟢 Знайдено",
    "closed": "🔴 Закрито"
}

PARKING_MAP = {
    "yes": "Так",
    "no": "Ні",
    "later": "Пізніше"
}

VIEW_MAP = {
    "online": "Онлайн",
    "offline": "Фізичний",
    "both": "Обидва варіанти"
}

LOCATION_MAP = {
    "ua": "Україна",
    "sk": "Словаччина"
}


def build_summary(u):
    return (
        f"📋 **Запит №{u['id']}**\n"
        f"📌 Статус: {u['status']}\n\n"
        f"👤 Імʼя: {u['name']}\n"
        f"🆔 Telegram: {u['tg']}\n"
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


async def start(update: Update, ctx):
    users[update.effective_user.id] = {
        "tg": f"@{update.effective_user.username}"
        if update.effective_user.username else f"id:{update.effective_user.id}",
        "step": "deal"
    }

    kb = [
        [InlineKeyboardButton("🏠 Оренда", callback_data="rent")],
        [InlineKeyboardButton("🏡 Купівля", callback_data="buy")]
    ]
    await update.message.reply_text("👋 Що вас цікавить?", reply_markup=InlineKeyboardMarkup(kb))


async def deal_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    u["deal"] = "Оренда" if q.data == "rent" else "Купівля"
    u["step"] = "property"

    kb = [
        [InlineKeyboardButton("🛏 Ліжко-місце", callback_data="bed")],
        [InlineKeyboardButton("Студія", callback_data="studio")],
        [InlineKeyboardButton("1-кімнатна", callback_data="1")],
        [InlineKeyboardButton("2-кімнатна", callback_data="2")],
        [InlineKeyboardButton("3-кімнатна", callback_data="3")],
        [InlineKeyboardButton("Будинок", callback_data="house")]
    ]
    await q.message.reply_text("🏡 Тип житла:", reply_markup=InlineKeyboardMarkup(kb))


async def text_handler(update: Update, ctx):
    uid = update.effective_user.id
    if uid not in users:
        return

    u = users[uid]
    t = update.message.text

    match u["step"]:
        case "city":
            u["city"] = t
            u["step"] = "district"
            await update.message.reply_text("🗺 Район?")

        case "district":
            u["district"] = t
            u["step"] = "for_whom"
            await update.message.reply_text("👥 Для кого житло?")

        case "for_whom":
            u["for_whom"] = t
            u["step"] = "job"
            await update.message.reply_text("💼 Ваша діяльність?")

        case "job":
            u["job"] = t
            u["step"] = "children"
            await update.message.reply_text("🧒 Чи є діти?")

        case "children":
            u["children"] = t
            u["step"] = "pets"
            await update.message.reply_text("🐾 Чи є тваринки?")

        case "pets":
            u["pets"] = t
            u["step"] = "parking"
            kb = [
                [InlineKeyboardButton("Так", callback_data="yes")],
                [InlineKeyboardButton("Ні", callback_data="no")],
                [InlineKeyboardButton("Пізніше", callback_data="later")]
            ]
            await update.message.reply_text("🚗 Паркування?", reply_markup=InlineKeyboardMarkup(kb))

        case "move_in":
            u["move_in"] = t
            u["step"] = "budget"
            await update.message.reply_text("💶 Бюджет?")

        case "budget":
            u["budget"] = t
            u["step"] = "view_time"
            await update.message.reply_text("⏰ Коли огляди?")

        case "view_time":
            u["view_time"] = t
            u["step"] = "name"
            await update.message.reply_text("👤 Як до вас звертатись?")


async def final_save(u, ctx):
    global REQUEST_COUNTER
    REQUEST_COUNTER += 1

    u["id"] = REQUEST_COUNTER
    u["status"] = STATUS_MAP["search"]
    REQUESTS[u["id"]] = u

    kb = [
        [
            InlineKeyboardButton("🟡 В пошуках", callback_data=f"status_search_{u['id']}"),
            InlineKeyboardButton("🟢 Знайдено", callback_data=f"status_done_{u['id']}")
        ],
        [InlineKeyboardButton("🔴 Закрито", callback_data=f"status_closed_{u['id']}")]
    ]

    msg = await ctx.bot.send_message(
        ADMIN_GROUP_ID,
        build_summary(u),
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

    u["msg_id"] = msg.message_id


async def status_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()

    _, key, req_id = q.data.split("_")
    req_id = int(req_id)

    if req_id not in REQUESTS:
        return

    u = REQUESTS[req_id]
    u["status"] = STATUS_MAP[key]

    await ctx.bot.edit_message_text(
        chat_id=ADMIN_GROUP_ID,
        message_id=u["msg_id"],
        text=build_summary(u),
        reply_markup=q.message.reply_markup,
        parse_mode="Markdown"
    )


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(deal_handler))
    app.add_handler(CallbackQueryHandler(status_handler, pattern="^status_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
