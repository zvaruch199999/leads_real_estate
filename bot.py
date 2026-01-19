import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID")

if not BOT_TOKEN or not ADMIN_GROUP_ID:
    raise RuntimeError("BOT_TOKEN або ADMIN_GROUP_ID не задані")

ADMIN_GROUP_ID = int(ADMIN_GROUP_ID)

users = {}
REQUEST_ID = 0

# ================== HELPERS ==================
def summary(u, req_id):
    return (
        f"📋 Запит №{req_id}\n\n"
        f"👤 Імʼя: {u['name']}\n"
        f"📞 Телефон: {u['phone']}\n"
        f"🆔 Telegram: @{u['username']}\n\n"
        f"🏠 Тип угоди: {u['deal']}\n"
        f"🏡 Житло: {u['property']}\n"
        f"📍 Місто: {u['city']}\n"
        f"👥 Для кого: {u['for_whom']}\n"
        f"💼 Діяльність: {u['job']}\n"
        f"🧒 Діти: {u['children']}\n"
        f"🐾 Тваринки: {u['pets']}\n"
        f"🚗 Паркування: {u['parking']}\n"
        f"📅 Заїзд: {u['move_in']}\n"
        f"⏰ Огляди: {u['view_time']}\n"
        f"✨ Побажання: {u['wishes']}\n"
        f"💶 Бюджет оренда: {u['budget']}\n"
        f"🌍 Зараз в: {u['location']}\n"
        f"👀 Формат огляду: {u['view_format']}"
    )

# ================== START ==================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id] = {
        "step": "deal",
        "username": update.effective_user.username or "—"
    }
    kb = [
        [InlineKeyboardButton("🏠 Оренда", callback_data="deal_rent")],
        [InlineKeyboardButton("🏡 Купівля", callback_data="deal_buy")]
    ]
    await update.message.reply_text(
        "👋 Що вас цікавить?",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================== CALLBACK ==================
async def callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = users[uid]
    data = q.data

    # DEAL
    if data.startswith("deal_"):
        u["deal"] = "Оренда" if data == "deal_rent" else "Купівля"
        u["step"] = "property"
        kb = [
            [InlineKeyboardButton("🛏 Ліжко-місце", callback_data="prop_Ліжко-місце")],
            [InlineKeyboardButton("🏢 Студія", callback_data="prop_Студія")],
            [InlineKeyboardButton("1️⃣ 1-кімнатна", callback_data="prop_1-кімнатна")],
            [InlineKeyboardButton("2️⃣ 2-кімнатна", callback_data="prop_2-кімнатна")],
            [InlineKeyboardButton("3️⃣ 3-кімнатна", callback_data="prop_3-кімнатна")],
            [InlineKeyboardButton("✍️ Свій варіант", callback_data="prop_custom")]
        ]
        await q.message.reply_text("🏡 Тип житла:", reply_markup=InlineKeyboardMarkup(kb))

    # PROPERTY
    elif data.startswith("prop_"):
        if data == "prop_custom":
            u["step"] = "property_text"
            await q.message.reply_text("✍️ Напишіть тип житла:")
        else:
            u["property"] = data.replace("prop_", "")
            u["step"] = "city"
            await q.message.reply_text("📍 В якому місті шукаєте житло?")

    # PARKING
    elif data.startswith("park_"):
        u["parking"] = {
            "park_yes": "Так",
            "park_no": "Ні",
            "park_later": "Пізніше"
        }[data]
        u["step"] = "move_in"
        await q.message.reply_text("📅 Яка найкраща дата для заїзду?")

    # LOCATION
    elif data.startswith("loc_"):
        if data == "loc_custom":
            u["step"] = "location_text"
            await q.message.reply_text("✍️ Напишіть країну:")
        else:
            u["location"] = "Україна" if data == "loc_ua" else "Словаччина"
            u["step"] = "view_format"
            await ask_view_format(q.message)

    # VIEW FORMAT
    elif data.startswith("view_"):
        u["view_format"] = {
            "view_online": "Онлайн",
            "view_offline": "Фізичний",
            "view_both": "Обидва варіанти"
        }[data]
        u["step"] = "contact"
        kb = ReplyKeyboardMarkup(
            [[KeyboardButton("📞 Поділитись контактом для пошуку житла", request_contact=True)]],
            resize_keyboard=True
        )
        await q.message.reply_text("📞 Поділіться контактом:", reply_markup=kb)

    # TERMS
    elif data == "terms_yes":
        global REQUEST_ID
        REQUEST_ID += 1
        await ctx.bot.send_message(
            ADMIN_GROUP_ID,
            summary(u, REQUEST_ID),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🟡 В пошуках", callback_data=f"status_search_{REQUEST_ID}"),
                    InlineKeyboardButton("🟢 Мають резервацію", callback_data=f"status_reserve_{REQUEST_ID}")
                ],
                [
                    InlineKeyboardButton("🔵 Самі знайшли", callback_data=f"status_self_{REQUEST_ID}"),
                    InlineKeyboardButton("🟠 Чужий маклер", callback_data=f"status_other_{REQUEST_ID}")
                ],
                [
                    InlineKeyboardButton("⚫ Не шукають", callback_data=f"status_stop_{REQUEST_ID}"),
                    InlineKeyboardButton("🔴 Закрили угоду", callback_data=f"status_closed_{REQUEST_ID}")
                ]
            ])
        )
        await q.message.reply_text(
            "✅ Запит відправлено маклеру.\n"
            "Ми звʼяжемось з вами протягом 24–48 годин.\n\n"
            "👉 Долучайтесь до нашої групи з пропозиціями:\n"
            "https://t.me/+IhcJixOP1_QyNjM0",
            reply_markup=ReplyKeyboardRemove()
        )
        users.pop(uid, None)

    elif data == "terms_no":
        users.pop(uid, None)
        await q.message.reply_text("❌ Запит скасовано.")

# ================== TEXT ==================
async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in users:
        return
    u = users[uid]
    t = update.message.text

    step = u["step"]

    if step == "property_text":
        u["property"] = t
        u["step"] = "city"
        await update.message.reply_text("📍 В якому місті шукаєте житло?")

    elif step == "city":
        u["city"] = t
        u["step"] = "for_whom"
        await update.message.reply_text("👥 Для кого шукаєте житло?")

    elif step == "for_whom":
        u["for_whom"] = t
        u["step"] = "job"
        await update.message.reply_text("💼 Чим ви займаєтесь?")

    elif step == "job":
        u["job"] = t
        u["step"] = "children"
        await update.message.reply_text("🧒 Чи є діти?")

    elif step == "children":
        u["children"] = t
        u["step"] = "pets"
        await update.message.reply_text("🐾 Чи є тваринки?")

    elif step == "pets":
        u["pets"] = t
        u["step"] = "parking"
        kb = [
            [InlineKeyboardButton("Так", callback_data="park_yes")],
            [InlineKeyboardButton("Ні", callback_data="park_no")],
            [InlineKeyboardButton("Пізніше", callback_data="park_later")]
        ]
        await update.message.reply_text("🚗 Паркування?", reply_markup=InlineKeyboardMarkup(kb))

    elif step == "move_in":
        u["move_in"] = t
        u["step"] = "view_time"
        await update.message.reply_text("⏰ Коли ви доступні для оглядів?")

    elif step == "view_time":
        u["view_time"] = t
        u["step"] = "wishes"
        await update.message.reply_text("✨ Напишіть особливі побажання до житла")

    elif step == "wishes":
        u["wishes"] = t
        u["step"] = "budget"
        await update.message.reply_text("💶 Який бюджет на оренду в місяць (від–до €)?")

    elif step == "budget":
        u["budget"] = t
        u["step"] = "location"
        kb = [
            [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc_ua")],
            [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc_sk")],
            [InlineKeyboardButton("✍️ Інша країна", callback_data="loc_custom")]
        ]
        await update.message.reply_text("🌍 Де ви зараз?", reply_markup=InlineKeyboardMarkup(kb))

    elif step == "location_text":
        u["location"] = t
        u["step"] = "view_format"
        await ask_view_format(update.message)

    elif step == "name":
        u["name"] = t
        kb = [
            [InlineKeyboardButton("✅ Так", callback_data="terms_yes")],
            [InlineKeyboardButton("❌ Ні", callback_data="terms_no")]
        ]
        await update.message.reply_text(
            "ℹ️ Умови співпраці:\n\n"
            "• депозит може дорівнювати орендній платі\n"
            "• оплачується повна або часткова комісія ріелтору\n"
            "• можливий подвійний депозит при дітях або тваринах\n\n"
            "Чи погоджуєтесь?",
            reply_markup=InlineKeyboardMarkup(kb)
        )

# ================== CONTACT ==================
async def contact_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = users[uid]
    u["phone"] = update.message.contact.phone_number
    u["step"] = "name"
    await update.message.reply_text("👤 Як до вас можемо звертатись?")

# ================== VIEW FORMAT ==================
async def ask_view_format(msg):
    kb = [
        [InlineKeyboardButton("💻 Онлайн", callback_data="view_online")],
        [InlineKeyboardButton("🚶 Фізичний", callback_data="view_offline")],
        [InlineKeyboardButton("🔁 Обидва варіанти", callback_data="view_both")]
    ]
    await msg.reply_text("👀 Який формат огляду?", reply_markup=InlineKeyboardMarkup(kb))

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
