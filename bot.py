from telegram import *
from telegram.ext import *
from config import BOT_TOKEN, ADMIN_GROUP_ID

users = {}
REQUEST_COUNTER = 0

STATUS_MAP = {
    "search": "🟡 В пошуках",
    "reserved": "🟢 Мають резервацію",
    "closed": "🔴 Закрили угоду",
    "self": "⚪ Самі знайшли",
    "other": "⚫ Знайшов інший маклер",
    "stop": "❌ Не шукають вже"
}

# ---------- START / RESET ----------

async def start(update: Update, ctx):
    users.pop(update.effective_user.id, None)

    kb = [
        [InlineKeyboardButton("🏠 Оренда", callback_data="deal_rent")],
        [InlineKeyboardButton("🏡 Купівля", callback_data="deal_buy")]
    ]
    await update.message.reply_text(
        "👋 Вітаємо!\n\n1️⃣ Що вас цікавить?",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def reset(update: Update, ctx):
    users.pop(update.effective_user.id, None)
    await update.message.reply_text(
        "🔄 Запит скинуто.\nНатисніть /start щоб почати знову.",
        reply_markup=ReplyKeyboardRemove()
    )

# ---------- SUMMARY ----------

def build_summary(u, req_id):
    username = f"@{u['username']}" if u.get("username") else "—"

    return (
        f"📋 *Запит №{req_id}*\n"
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

# ---------- CALLBACKS ----------

async def deal_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()

    users[q.from_user.id] = {
        "deal": "Оренда" if q.data == "deal_rent" else "Купівля",
        "step": "property",
        "username": q.from_user.username
    }

    kb = [
        [InlineKeyboardButton("🛏 Ліжко-місце", callback_data="prop_Ліжко-місце")],
        [InlineKeyboardButton("🏢 Студія", callback_data="prop_Студія")],
        [InlineKeyboardButton("1️⃣ 1-кімнатна", callback_data="prop_1-кімнатна")],
        [InlineKeyboardButton("2️⃣ 2-кімнатна", callback_data="prop_2-кімнатна")],
        [InlineKeyboardButton("3️⃣ 3-кімнатна", callback_data="prop_3-кімнатна")],
        [InlineKeyboardButton("🏠 Будинок", callback_data="prop_Будинок")],
        [InlineKeyboardButton("✍️ Свій варіант", callback_data="prop_custom")]
    ]

    await q.message.reply_text("2️⃣ Тип житла:", reply_markup=InlineKeyboardMarkup(kb))

async def property_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "prop_custom":
        u["step"] = "property_text"
        await q.message.reply_text("✍️ Напишіть тип житла вручну:")
    else:
        u["property"] = q.data.replace("prop_", "")
        u["step"] = "city"
        await q.message.reply_text("3️⃣ В якому місті шукаєте житло?")

# ---------- TEXT FLOW ----------

async def text_handler(update: Update, ctx):
    uid = update.message.from_user.id
    if uid not in users:
        return

    u = users[uid]
    t = update.message.text

    step = u["step"]

    if step == "property_text":
        u["property"] = t
        u["step"] = "city"
        await update.message.reply_text("3️⃣ В якому місті шукаєте житло?")

    elif step == "city":
        u["city"] = t
        u["step"] = "district"
        await update.message.reply_text("4️⃣ Який район?")

    elif step == "district":
        u["district"] = t
        u["step"] = "for_whom"
        await update.message.reply_text("5️⃣ Для кого шукаєте житло?")

    elif step == "for_whom":
        u["for_whom"] = t
        u["step"] = "job"
        await update.message.reply_text("6️⃣ Чим ви займаєтесь?")

    elif step == "job":
        u["job"] = t
        u["step"] = "children"
        await update.message.reply_text("7️⃣ Чи маєте дітей? Якщо ні — напишіть «Ні».")

    elif step == "children":
        u["children"] = t
        u["step"] = "pets"
        await update.message.reply_text(
            "8️⃣ Чи маєте тваринок?\n"
            "Якщо так — напишіть яку і коротко про неї.\n"
            "Якщо ні — напишіть «Ні»."
        )

    elif step == "pets":
        u["pets"] = t
        u["step"] = "parking"
        kb = [
            [InlineKeyboardButton("Так", callback_data="park_yes")],
            [InlineKeyboardButton("Ні", callback_data="park_no")],
            [InlineKeyboardButton("Пізніше", callback_data="park_later")]
        ]
        await update.message.reply_text("9️⃣ Чи потрібне паркування?", reply_markup=InlineKeyboardMarkup(kb))

    elif step == "move_in":
        u["move_in"] = t
        u["step"] = "budget"
        await update.message.reply_text("🔟 Який бюджет на оренду в місяць (від–до €)?")

    elif step == "budget":
        u["budget"] = t
        u["step"] = "view_time"
        await update.message.reply_text("1️⃣1️⃣ Коли ви доступні для оглядів?")

    elif step == "view_time":
        u["view_time"] = t
        u["step"] = "location"
        kb = [
            [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc_ua")],
            [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc_sk")],
            [InlineKeyboardButton("✍️ Інша країна", callback_data="loc_custom")]
        ]
        await update.message.reply_text("1️⃣2️⃣ Де ви зараз?", reply_markup=InlineKeyboardMarkup(kb))

    elif step == "custom_location":
        u["location"] = t
        u["step"] = "view_format"
        await ask_view_format(update.message)

    elif step == "name":
        global REQUEST_COUNTER
        REQUEST_COUNTER += 1
        u["name"] = t
        u["req_id"] = REQUEST_COUNTER

        kb = [
            [InlineKeyboardButton("✅ Так", callback_data="confirm_yes")],
            [InlineKeyboardButton("❌ Ні", callback_data="confirm_no")]
        ]

        await update.message.reply_text(
            build_summary(u, u["req_id"]) + "\n\nВсе вірно?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )

# ---------- OTHER HANDLERS ----------

async def parking_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["parking"] = {"park_yes": "Так", "park_no": "Ні", "park_later": "Пізніше"}[q.data]
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
    await msg.reply_text("1️⃣3️⃣ Формат огляду?", reply_markup=InlineKeyboardMarkup(kb))

async def view_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["view_format"] = {"view_online": "Онлайн", "view_offline": "Фізичний", "view_both": "Обидва"}[q.data]
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
    await update.message.reply_text("👤 Як до вас можемо звертатись?")

# ---------- CONFIRM ----------

async def confirm_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()

    if q.data == "confirm_yes":
        kb = [
            [InlineKeyboardButton("✅ Так", callback_data="terms_yes")],
            [InlineKeyboardButton("❌ Ні", callback_data="terms_no")]
        ]

        await q.message.reply_text(
            "ℹ️ *Умови співпраці:*\n\n"
            "• депозит може дорівнювати орендній платі\n"
            "• оплачується повна або часткова комісія ріелтору\n"
            "• можливий подвійний депозит при дітях або тваринах\n\n"
            "Чи погоджуєтесь?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )
    else:
        users.pop(q.from_user.id, None)
        await q.message.reply_text("❌ Запит скасовано.")

async def terms_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "terms_yes":
        msg = await ctx.bot.send_message(
            ADMIN_GROUP_ID,
            build_summary(u, u["req_id"]),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🟡 В пошуках", callback_data=f"status_search_{u['req_id']}"),
                    InlineKeyboardButton("🟢 Мають резервацію", callback_data=f"status_reserved_{u['req_id']}")
                ],
                [
                    InlineKeyboardButton("⚪ Самі знайшли", callback_data=f"status_self_{u['req_id']}"),
                    InlineKeyboardButton("⚫ Інший маклер", callback_data=f"status_other_{u['req_id']}")
                ],
                [
                    InlineKeyboardButton("🔴 Закрили угоду", callback_data=f"status_closed_{u['req_id']}"),
                    InlineKeyboardButton("❌ Не шукають", callback_data=f"status_stop_{u['req_id']}")
                ]
            ])
        )

        await q.message.reply_text(
            "✅ Запит відправлено маклеру.\nМи звʼяжемось з вами протягом 24–48 годин."
        )

    users.pop(q.from_user.id, None)

# ---------- MAIN ----------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))

    app.add_handler(CallbackQueryHandler(deal_handler, pattern="^deal_"))
    app.add_handler(CallbackQueryHandler(property_handler, pattern="^prop_"))
    app.add_handler(CallbackQueryHandler(parking_handler, pattern="^park_"))
    app.add_handler(CallbackQueryHandler(location_handler, pattern="^loc_"))
    app.add_handler(CallbackQueryHandler(view_handler, pattern="^view_"))
    app.add_handler(CallbackQueryHandler(confirm_handler, pattern="^confirm_"))
    app.add_handler(CallbackQueryHandler(terms_handler, pattern="^terms_"))

    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
