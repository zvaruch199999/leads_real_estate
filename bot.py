import os
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
    MessageHandler,
    CallbackQueryHandler,
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

# ===== HELPERS =====
def summary(u: dict) -> str:
    return (
        f"📋 **Запит №{u['req_id']}**\n"
        f"📌 Статус: 🟡 В пошуках\n\n"

        f"👤 Імʼя: {u['name']}\n"
        f"🆔 Telegram: @{u.get('username','—')}\n"
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
        "username": update.effective_user.username
    }

    await update.message.reply_text(
        "👋 Що вас цікавить?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Оренда", callback_data="deal_rent")],
            [InlineKeyboardButton("🏡 Купівля", callback_data="deal_buy")]
        ])
    )


# ===== CALLBACK HANDLERS =====
async def deal_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    u = users[q.from_user.id]
    u["deal"] = "Оренда" if q.data == "deal_rent" else "Купівля"
    u["step"] = "property"

    await q.message.reply_text(
        "🏡 Тип житла:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛏 Ліжко-місце", callback_data="prop_bed")],
            [InlineKeyboardButton("🏢 Студія", callback_data="prop_studio")],
            [InlineKeyboardButton("1️⃣ 1-кімнатна", callback_data="prop_1")],
            [InlineKeyboardButton("2️⃣ 2-кімнатна", callback_data="prop_2")],
            [InlineKeyboardButton("3️⃣ 3-кімнатна", callback_data="prop_3")],
            [InlineKeyboardButton("✍️ Свій варіант", callback_data="prop_custom")]
        ])
    )


async def property_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "prop_custom":
        u["step"] = "property_custom"
        await q.message.reply_text("✍️ Напишіть тип житла:")
        return

    MAP = {
        "prop_bed": "Ліжко-місце",
        "prop_studio": "Студія",
        "prop_1": "1-кімнатна",
        "prop_2": "2-кімнатна",
        "prop_3": "3-кімнатна",
    }

    u["property"] = MAP[q.data]
    u["step"] = "city"
    await q.message.reply_text("📍 В якому місті шукаєте житло?")


async def parking_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    MAP = {
        "park_yes": "Так",
        "park_no": "Ні",
        "park_later": "Пізніше"
    }

    u["parking"] = MAP[q.data]
    u["step"] = "move_in"
    await q.message.reply_text("📅 Яка найкраща дата для заїзду?")


async def location_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "loc_custom":
        u["step"] = "location_custom"
        await q.message.reply_text("✍️ Напишіть країну:")
        return

    u["location"] = "Україна" if q.data == "loc_ua" else "Словаччина"
    u["step"] = "view_format"

    await ask_view_format(q.message)


async def view_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    MAP = {
        "view_online": "Онлайн",
        "view_offline": "Фізичний",
        "view_both": "Обидва варіанти"
    }

    u["view_format"] = MAP[q.data]
    u["step"] = "contact"

    await q.message.reply_text(
        "📞 Поділіться контактом для пошуку житла:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📞 Поділитись контактом", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )


# ===== TEXT HANDLER (CORE FIX) =====
async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in users:
        return

    u = users[uid]
    text = update.message.text.strip()

    if u["step"] == "property_custom":
        u["property"] = text
        u["step"] = "city"
        await update.message.reply_text("📍 В якому місті шукаєте житло?")
        return

    if u["step"] == "city":
        u["city"] = text
        u["step"] = "district"
        await update.message.reply_text("🗺 В якому районі?")
        return

    if u["step"] == "district":
        u["district"] = text
        u["step"] = "for_whom"
        await update.message.reply_text("👥 Для кого шукаєте житло?")
        return

    if u["step"] == "for_whom":
        u["for_whom"] = text
        u["step"] = "job"
        await update.message.reply_text("💼 Чим ви займаєтесь?")
        return

    if u["step"] == "job":
        u["job"] = text
        u["step"] = "children"
        await update.message.reply_text("🧒 Чи маєте дітей? (Так / Ні)")
        return

    if u["step"] == "children":
        u["children"] = text
        u["step"] = "pets"
        await update.message.reply_text("🐾 Чи маєте тваринок? Якщо так — напишіть які.")
        return

    if u["step"] == "pets":
        u["pets"] = text
        u["step"] = "parking"
        await update.message.reply_text(
            "🚗 Чи потрібне паркування?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Так", callback_data="park_yes")],
                [InlineKeyboardButton("Ні", callback_data="park_no")],
                [InlineKeyboardButton("Пізніше", callback_data="park_later")]
            ])
        )
        return

    if u["step"] == "move_in":
        u["move_in"] = text
        u["step"] = "view_time"
        await update.message.reply_text("⏰ Коли ви доступні для оглядів?")
        return

    if u["step"] == "view_time":
        u["view_time"] = text
        u["step"] = "wishes"
        await update.message.reply_text("✨ Напишіть особливі побажання до житла")
        return

    if u["step"] == "wishes":
        u["wishes"] = text
        u["step"] = "budget"
        await update.message.reply_text("💶 Який бюджет на оренду в місяць (від–до €)?")
        return

    if u["step"] == "budget":
        u["budget"] = text
        u["step"] = "location"
        await update.message.reply_text(
            "🌍 Де ви зараз?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc_ua")],
                [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc_sk")],
                [InlineKeyboardButton("✍️ Інша країна", callback_data="loc_custom")]
            ])
        )
        return

    if u["step"] == "location_custom":
        u["location"] = text
        u["step"] = "view_format"
        await ask_view_format(update.message)
        return

    if u["step"] == "name":
        global REQUEST_COUNTER
        REQUEST_COUNTER += 1

        u["name"] = text
        u["req_id"] = REQUEST_COUNTER

        await ctx.bot.send_message(
            ADMIN_GROUP_ID,
            summary(u),
            parse_mode="Markdown"
        )

        await update.message.reply_text(
            "✅ Запит відправлено маклеру.\n"
            "Маклер звʼяжеться з вами протягом **24–48 годин**.\n\n"
            "🔗 Долучайтесь до нашої групи з пропозиціями житла в Братиславі:\n"
            "https://t.me/+IhcJixOP1_QyNjM0",
            parse_mode="Markdown"
        )

        users.pop(uid, None)
        return


async def ask_view_format(msg):
    await msg.reply_text(
        "👀 Який формат огляду?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💻 Онлайн", callback_data="view_online")],
            [InlineKeyboardButton("🚶 Фізичний", callback_data="view_offline")],
            [InlineKeyboardButton("🔁 Обидва варіанти", callback_data="view_both")]
        ])
    )


async def contact_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = users[update.effective_user.id]
    u["phone"] = update.message.contact.phone_number
    u["step"] = "name"
    await update.message.reply_text("👤 Як до вас можемо звертатись?")


# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
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
