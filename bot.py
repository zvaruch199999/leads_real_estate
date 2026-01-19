import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ===== ENV =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID")

if not BOT_TOKEN or not ADMIN_GROUP_ID:
    raise RuntimeError("BOT_TOKEN або ADMIN_GROUP_ID не задані")

ADMIN_GROUP_ID = int(ADMIN_GROUP_ID)

# ===== STORAGE =====
users = {}
REQUEST_COUNTER = 0

# ===== MAPS =====
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

# ===== SUMMARY =====
def build_summary(u):
    return (
        f"📋 **Запит №{u['req_id']}**\n\n"
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
        f"⏰ Огляди: {u['view_time']}\n"
        f"✨ Побажання: {u['wishes']}\n"
        f"💶 Бюджет оренда: {u['budget']}\n"
        f"🌍 Зараз в: {u['location']}\n"
        f"👀 Формат огляду: {u['view_format']}"
    )

# ===== START =====
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id] = {
        "step": "deal",
        "username": update.effective_user.username or "немає"
    }

    await update.message.reply_text(
        "👋 Вітаємо!\nЩо вас цікавить?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Оренда", callback_data="deal_rent")],
            [InlineKeyboardButton("🏡 Купівля", callback_data="deal_buy")]
        ])
    )

# ===== DEAL =====
async def deal_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    u = users[q.from_user.id]
    u["deal"] = "Оренда" if q.data == "deal_rent" else "Купівля"
    u["step"] = "property"

    await q.message.reply_text(
        "🏡 Тип житла:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛏 Ліжко-місце", callback_data="prop_Ліжко-місце")],
            [InlineKeyboardButton("🏢 Студія", callback_data="prop_Студія")],
            [InlineKeyboardButton("1️⃣ 1-кімнатна", callback_data="prop_1-кімнатна")],
            [InlineKeyboardButton("2️⃣ 2-кімнатна", callback_data="prop_2-кімнатна")],
            [InlineKeyboardButton("3️⃣ 3-кімнатна", callback_data="prop_3-кімнатна")],
            [InlineKeyboardButton("✍️ Свій варіант", callback_data="prop_custom")]
        ])
    )

# ===== PROPERTY =====
async def property_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "prop_custom":
        u["step"] = "property_text"
        await q.message.reply_text("✍️ Напишіть тип житла:")
        return

    u["property"] = q.data.replace("prop_", "")
    u["step"] = "city"
    await q.message.reply_text("📍 В якому місті шукаєте житло?")

# ===== TEXT FLOW =====
async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in users:
        return

    u = users[uid]
    t = update.message.text

    match u["step"]:
        case "property_text":
            u["property"] = t
            u["step"] = "city"
            await update.message.reply_text("📍 В якому місті шукаєте житло?")

        case "city":
            u["city"] = t
            u["step"] = "district"
            await update.message.reply_text("🗺 Який район?")

        case "district":
            u["district"] = t
            u["step"] = "for_whom"
            await update.message.reply_text("👥 Для кого шукаєте житло?")

        case "for_whom":
            u["for_whom"] = t
            u["step"] = "job"
            await update.message.reply_text("💼 Чим ви займаєтесь?")

        case "job":
            u["job"] = t
            u["step"] = "children"
            await update.message.reply_text("🧒 Чи маєте дітей? Якщо ні — напишіть «Ні».")

        case "children":
            u["children"] = t
            u["step"] = "pets"
            await update.message.reply_text(
                "🐾 Чи маєте тваринок?\n"
                "Якщо так — напишіть яку і коротко про неї.\n"
                "Якщо ні — напишіть «Ні»."
            )

        case "pets":
            u["pets"] = t
            u["step"] = "parking"
            await update.message.reply_text(
                "🚗 Чи потрібне паркування?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Так", callback_data="park_yes")],
                    [InlineKeyboardButton("Ні", callback_data="park_no")],
                    [InlineKeyboardButton("Пізніше", callback_data="park_later")]
                ])
            )

        case "move_in":
            u["move_in"] = t
            u["step"] = "view_time"
            await update.message.reply_text("⏰ Коли ви доступні для оглядів?")

        case "view_time":
            u["view_time"] = t
            u["step"] = "wishes"
            await update.message.reply_text("✨ Напишіть особливі побажання до житла")

        case "wishes":
            u["wishes"] = t
            u["step"] = "budget"
            await update.message.reply_text("💶 Який бюджет на оренду в місяць (від–до €)?")

        case "budget":
            u["budget"] = t
            u["step"] = "location"
            await update.message.reply_text(
                "🌍 Де ви зараз?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc_ua")],
                    [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc_sk")],
                    [InlineKeyboardButton("✍️ Інша країна", callback_data="loc_custom")]
                ])
            )

        case "custom_location":
            u["location"] = t
            u["step"] = "view_format"
            await ask_view_format(update.message)

        case "name":
            global REQUEST_COUNTER
            REQUEST_COUNTER += 1
            u["name"] = t
            u["req_id"] = REQUEST_COUNTER
            u["step"] = "terms"

            await update.message.reply_text(
                "ℹ️ **Умови співпраці:**\n\n"
                "• депозит може дорівнювати орендній платі\n"
                "• оплачується повна або часткова комісія ріелтору\n"
                "• можливий подвійний депозит при дітях або тваринах\n\n"
                "Чи погоджуєтесь?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Так", callback_data="terms_yes")],
                    [InlineKeyboardButton("❌ Ні", callback_data="terms_no")]
                ]),
                parse_mode="Markdown"
            )

# ===== CALLBACKS =====
async def parking_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["parking"] = PARKING_MAP[q.data]
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
        u["location"] = LOCATION_MAP[q.data]
        u["step"] = "view_format"
        await ask_view_format(q.message)

async def ask_view_format(msg):
    await msg.reply_text(
        "👀 Який формат огляду?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💻 Онлайн", callback_data="view_online")],
            [InlineKeyboardButton("🚶 Фізичний", callback_data="view_offline")],
            [InlineKeyboardButton("🔁 Обидва варіанти", callback_data="view_both")]
        ])
    )

async def view_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["view_format"] = VIEW_MAP[q.data]
    u["step"] = "contact"

    await q.message.reply_text(
        "📞 Поділіться контактом для пошуку житла:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📞 Поділитись контактом", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )

async def contact_handler(update: Update, ctx):
    u = users[update.effective_user.id]
    u["phone"] = update.message.contact.phone_number
    u["step"] = "name"

    await update.message.reply_text(
        "👤 Як до вас можемо звертатись?",
        reply_markup=ReplyKeyboardRemove()
    )

async def terms_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == "terms_no":
        await q.message.reply_text("❌ Запит скасовано.")
        users.pop(uid, None)
        return

    u = users[uid]

    await ctx.bot.send_message(
        ADMIN_GROUP_ID,
        build_summary(u),
        parse_mode="Markdown"
    )

    await q.message.reply_text(
        "✅ Запит відправлено маклеру.\n"
        "Маклер звʼяжеться з вами протягом **24–48 годин**.\n\n"
        "🔗 Долучайтесь до нашої групи з пропозиціями житла в Братиславі:\n"
        "https://t.me/+IhcJixOP1_QyNjM0",
        parse_mode="Markdown"
    )

    users.pop(uid, None)

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(deal_handler, pattern="^deal_"))
    app.add_handler(CallbackQueryHandler(property_handler, pattern="^prop_"))
    app.add_handler(CallbackQueryHandler(parking_handler, pattern="^park_"))
    app.add_handler(CallbackQueryHandler(location_handler, pattern="^loc_"))
    app.add_handler(CallbackQueryHandler(view_handler, pattern="^view_"))
    app.add_handler(CallbackQueryHandler(terms_handler, pattern="^terms_"))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
