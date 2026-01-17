from telegram import *
from telegram.ext import *
from config import BOT_TOKEN, ADMIN_GROUP_ID
import storage

users = {}

# ---------- HELPERS ----------

def summary(u, req_id):
    return (
        f"📋 **Запит №{req_id}**\n\n"
        f"👤 Імʼя: {u['name']}\n"
        f"📞 Телефон: {u['phone']}\n\n"
        f"🏠 Тип угоди: {u['deal']}\n"
        f"🏡 Житло: {u['property']}\n"
        f"📍 Місто: {u['city']} / {u['district']}\n"
        f"👨‍👩‍👧 Для кого: {u['for_whom']}\n"
        f"💼 Діяльність: {u['job']}\n"
        f"🧒 Діти: {u['children']}\n"
        f"🐾 Тваринки: {u['pets']}\n"
        f"🚗 Паркування: {u['parking']}\n"
        f"📅 Заїзд: {u['move_in']}\n"
        f"💶 Бюджет: {u['budget']}\n"
        f"⏰ Огляди: {u['view_time']}\n"
        f"🌍 Зараз: {u['location']}\n"
        f"👀 Формат: {u['view_format']}"
    )

# ---------- START ----------

async def start(update: Update, ctx):
    kb = [
        [InlineKeyboardButton("🏠 Оренда", callback_data="rent")],
        [InlineKeyboardButton("🏡 Купівля", callback_data="buy")]
    ]
    await update.message.reply_text(
        "👋 Вітаємо!\nЩо вас цікавить?",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ---------- CALLBACKS ----------

async def deal(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    users[q.from_user.id] = {"deal": "Оренда" if q.data == "rent" else "Купівля", "step": "property"}
    kb = [
        [InlineKeyboardButton("Студія", callback_data="p_Студія")],
        [InlineKeyboardButton("1-кімнатна", callback_data="p_1")],
        [InlineKeyboardButton("2-кімнатна", callback_data="p_2")],
        [InlineKeyboardButton("Будинок", callback_data="p_Будинок")],
        [InlineKeyboardButton("✍️ Свій варіант", callback_data="p_custom")]
    ]
    await q.message.reply_text("🏡 Тип житла?", reply_markup=InlineKeyboardMarkup(kb))

async def property_cb(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    if q.data == "p_custom":
        u["step"] = "property_text"
        await q.message.reply_text("✍️ Опишіть тип житла:")
    else:
        u["property"] = q.data.replace("p_", "")
        u["step"] = "city"
        await q.message.reply_text("📍 В якому місті шукаєте житло?")

# ---------- TEXT FLOW ----------

async def text(update: Update, ctx):
    uid = update.message.from_user.id
    if uid not in users:
        return
    u = users[uid]
    t = update.message.text

    if u["step"] == "property_text":
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
        await update.message.reply_text("👨‍👩‍👧 Для кого шукаєте житло?")

    elif u["step"] == "for_whom":
        u["for_whom"] = t
        u["step"] = "job"
        await update.message.reply_text("💼 Чим ви займаєтесь?")

    elif u["step"] == "job":
        u["job"] = t
        u["step"] = "children"
        await update.message.reply_text("🧒 Чи маєте дітей? (вік / стать або «Ні»)")

    elif u["step"] == "children":
        u["children"] = t
        u["step"] = "pets"
        await update.message.reply_text(
            "🐾 Чи маєте тваринок?\n"
            "Якщо так — напишіть яку і трохи про неї.\n"
            "Якщо ні — напишіть «Ні»."
        )

    elif u["step"] == "pets":
        u["pets"] = t
        u["step"] = "parking"
        kb = [
            [InlineKeyboardButton("Так", callback_data="park_yes")],
            [InlineKeyboardButton("Ні", callback_data="park_no")],
            [InlineKeyboardButton("Пізніше", callback_data="park_later")]
        ]
        await update.message.reply_text("🚗 Чи потрібне паркування?", reply_markup=InlineKeyboardMarkup(kb))

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
        kb = [
            [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc_ua")],
            [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc_sk")],
            [InlineKeyboardButton("✍️ Інша країна", callback_data="loc_custom")]
        ]
        await update.message.reply_text("🌍 Де ви зараз знаходитесь?", reply_markup=InlineKeyboardMarkup(kb))

    elif u["step"] == "custom_location":
        u["location"] = t
        u["step"] = "view_format"
        await ask_view_format(update, ctx)

    elif u["step"] == "name":
        u["name"] = t
        req_id = storage.new_request(u)
        u["req_id"] = req_id
        kb = [
            [InlineKeyboardButton("✅ Так", callback_data="confirm_data_yes")],
            [InlineKeyboardButton("❌ Ні", callback_data="confirm_data_no")]
        ]
        await update.message.reply_text(
            summary(u, req_id) + "\n\nВсе вірно?",
            reply_markup=InlineKeyboardMarkup(kb)
        )

# ---------- PARK / LOCATION / VIEW ----------

async def parking(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["parking"] = q.data.replace("park_", "")
    u["step"] = "move_in"
    await q.message.reply_text("📅 Яка найкраща дата для заїзду?")

async def location(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    if q.data == "loc_custom":
        u["step"] = "custom_location"
        await q.message.reply_text("✍️ Напишіть країну:")
    else:
        u["location"] = "Україна" if q.data == "loc_ua" else "Словаччина"
        u["step"] = "view_format"
        await ask_view_format(q, ctx)

async def ask_view_format(src, ctx):
    kb = [
        [InlineKeyboardButton("💻 Онлайн", callback_data="view_online")],
        [InlineKeyboardButton("🚶 Фізичний", callback_data="view_offline")],
        [InlineKeyboardButton("🔁 Обидва", callback_data="view_both")]
    ]
    await src.message.reply_text("👀 Формат огляду?", reply_markup=InlineKeyboardMarkup(kb))

async def view_format(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["view_format"] = q.data.replace("view_", "")
    u["step"] = "contact"
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Поділитись контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await q.message.reply_text("📞 Поділіться контактом:", reply_markup=kb)

async def contact(update: Update, ctx):
    u = users[update.message.from_user.id]
    u["phone"] = update.message.contact.phone_number
    u["step"] = "name"
    await update.message.reply_text("👤 Як до вас можемо звертатись?")

# ---------- CONFIRM TERMS ----------

async def confirm_data(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "confirm_data_yes":
        kb = [
            [InlineKeyboardButton("✅ Так", callback_data="terms_yes")],
            [InlineKeyboardButton("❌ Ні", callback_data="terms_no")]
        ]
        await q.message.reply_text(
            "ℹ️ **Умови співпраці:**\n\n"
            "• стандартно оплачується депозит за квартиру в розмірі орендної плати\n"
            "• повна або часткова комісія ріелтору в розмірі орендної плати\n"
            "• можливий подвійний депозит при дітях або тваринах\n\n"
            "Чи погоджуєтесь?",
            reply_markup=InlineKeyboardMarkup(kb)
        )
    else:
        users.pop(q.from_user.id)

async def confirm_terms(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "terms_yes":
        await ctx.bot.send_message(ADMIN_GROUP_ID, summary(u, u["req_id"]))
        await q.message.reply_text(
            "✅ Запит відправлено маклеру.\n"
            "Ми звʼяжемось з вами протягом **24–48 годин**."
        )
    users.pop(q.from_user.id)

# ---------- MAIN ----------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(deal, pattern="^(rent|buy)$"))
    app.add_handler(CallbackQueryHandler(property_cb, pattern="^p_"))
    app.add_handler(CallbackQueryHandler(parking, pattern="^park_"))
    app.add_handler(CallbackQueryHandler(location, pattern="^loc_"))
    app.add_handler(CallbackQueryHandler(view_format, pattern="^view_"))
    app.add_handler(CallbackQueryHandler(confirm_data, pattern="^confirm_data_"))
    app.add_handler(CallbackQueryHandler(confirm_terms, pattern="^terms_"))
    app.add_handler(MessageHandler(filters.CONTACT, contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))

    app.run_polling()

if __name__ == "__main__":
    main()
