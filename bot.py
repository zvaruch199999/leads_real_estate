from telegram import *
from telegram.ext import *
from config import BOT_TOKEN, ADMIN_GROUP_ID

users = {}
REQUEST_COUNTER = 0

PARKING_MAP = {
    "park_yes": "Так",
    "park_no": "Ні",
    "park_later": "Пізніше"
}

VIEW_MAP = {
    "view_online": "Онлайн",
    "view_offline": "Фізичний",
    "view_both": "Обидва варіанти"
}

LOCATION_MAP = {
    "loc_ua": "Україна",
    "loc_sk": "Словаччина"
}

STATUS_MAP = {
    "search": "🟡 В пошуках",
    "done": "🟢 Житло знайдено",
    "closed": "🔴 Запит закрито"
}


def build_summary(u):
    return (
        f"📋 **Запит №{u['req_id']}**\n"
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
        if update.effective_user.username else f"id:{update.effective_user.id}"
    }

    kb = [
        [InlineKeyboardButton("🏠 Оренда", callback_data="deal_rent")],
        [InlineKeyboardButton("🏡 Купівля", callback_data="deal_buy")]
    ]
    await update.message.reply_text(
        "👋 Вітаємо!\nЩо вас цікавить?",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def deal_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()

    users[q.from_user.id].update({
        "deal": "Оренда" if q.data == "deal_rent" else "Купівля",
        "step": "property"
    })

    kb = [
        [InlineKeyboardButton("🛏 Ліжко-місце", callback_data="prop_Ліжко-місце")],
        [InlineKeyboardButton("Студія", callback_data="prop_Студія")],
        [InlineKeyboardButton("1-кімнатна", callback_data="prop_1-кімнатна")],
        [InlineKeyboardButton("2-кімнатна", callback_data="prop_2-кімнатна")],
        [InlineKeyboardButton("3-кімнатна", callback_data="prop_3-кімнатна")],
        [InlineKeyboardButton("Будинок", callback_data="prop_Будинок")],
        [InlineKeyboardButton("✍️ Свій варіант", callback_data="prop_custom")]
    ]

    await q.message.reply_text("🏡 Який тип житла?", reply_markup=InlineKeyboardMarkup(kb))


async def property_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "prop_custom":
        u["step"] = "property_text"
        await q.message.reply_text("✍️ Напишіть тип житла:")
    else:
        u["property"] = q.data.replace("prop_", "")
        u["step"] = "city"
        await q.message.reply_text("📍 В якому місті шукаєте житло?")


async def text_handler(update: Update, ctx):
    uid = update.message.from_user.id
    if uid not in users:
        return

    u = users[uid]
    t = update.message.text

    step = u.get("step")

    if step == "property_text":
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
        await update.message.reply_text("🧒 Чи маєте дітей?")

    elif step == "children":
        u["children"] = t
        u["step"] = "pets"
        await update.message.reply_text("🐾 Чи маєте тваринок?")

    elif step == "pets":
        u["pets"] = t
        u["step"] = "parking"
        kb = [
            [InlineKeyboardButton("Так", callback_data="park_yes")],
            [InlineKeyboardButton("Ні", callback_data="park_no")],
            [InlineKeyboardButton("Пізніше", callback_data="park_later")]
        ]
        await update.message.reply_text("🚗 Чи потрібне паркування?", reply_markup=InlineKeyboardMarkup(kb))

    elif step == "move_in":
        u["move_in"] = t
        u["step"] = "budget"
        await update.message.reply_text("💶 Який бюджет?")

    elif step == "budget":
        u["budget"] = t
        u["step"] = "view_time"
        await update.message.reply_text("⏰ Коли доступні для оглядів?")

    elif step == "view_time":
        u["view_time"] = t
        u["step"] = "location"
        kb = [
            [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc_ua")],
            [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc_sk")],
        ]
        await update.message.reply_text("🌍 Де ви зараз?", reply_markup=InlineKeyboardMarkup(kb))

    elif step == "name":
        global REQUEST_COUNTER
        REQUEST_COUNTER += 1

        u["name"] = t
        u["req_id"] = REQUEST_COUNTER
        u["status"] = STATUS_MAP["search"]

        kb = [
            [
                InlineKeyboardButton("🟡 В пошуках", callback_data=f"status_search_{u['req_id']}"),
                InlineKeyboardButton("🟢 Знайдено", callback_data=f"status_done_{u['req_id']}")
            ],
            [InlineKeyboardButton("🔴 Закрито", callback_data=f"status_closed_{u['req_id']}")]
        ]

        await ctx.bot.send_message(
            ADMIN_GROUP_ID,
            build_summary(u),
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )

        await update.message.reply_text(
            "✅ Запит відправлено маклеру.\n"
            "Ми звʼяжемось з вами протягом 24–48 годин."
        )

        users.pop(uid, None)


async def parking_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["parking"] = PARKING_MAP[q.data]
    u["step"] = "move_in"
    await q.message.reply_text("📅 Коли плануєте заїзд?")


async def location_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["location"] = LOCATION_MAP[q.data]
    u["step"] = "view_format"
    kb = [
        [InlineKeyboardButton("💻 Онлайн", callback_data="view_online")],
        [InlineKeyboardButton("🚶 Фізичний", callback_data="view_offline")],
        [InlineKeyboardButton("🔁 Обидва", callback_data="view_both")]
    ]
    await q.message.reply_text("👀 Формат огляду?", reply_markup=InlineKeyboardMarkup(kb))


async def view_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["view_format"] = VIEW_MAP[q.data]
    u["step"] = "contact"

    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Поділитись контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await q.message.reply_text("📞 Поділіться контактом:", reply_markup=kb)


async def contact_handler(update: Update, ctx):
    u = users[update.message.from_user.id]
    u["phone"] = update.message.contact.phone_number
    u["step"] = "name"
    await update.message.reply_text(
        "👤 Як до вас можемо звертатись?",
        reply_markup=ReplyKeyboardRemove()
    )


async def status_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()

    _, key, req_id = q.data.split("_")
    new_status = STATUS_MAP[key]

    for u in users.values():
        if str(u.get("req_id")) == req_id:
            u["status"] = new_status
            await q.message.edit_text(
                build_summary(u),
                reply_markup=q.message.reply_markup,
                parse_mode="Markdown"
            )
            break


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(status_handler, pattern="^status_"))
    app.add_handler(CallbackQueryHandler(deal_handler, pattern="^deal_"))
    app.add_handler(CallbackQueryHandler(property_handler, pattern="^prop_"))
    app.add_handler(CallbackQueryHandler(parking_handler, pattern="^park_"))
    app.add_handler(CallbackQueryHandler(location_handler, pattern="^loc_"))
    app.add_handler(CallbackQueryHandler(view_handler, pattern="^view_"))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
