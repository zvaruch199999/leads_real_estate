import os
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================== ENV ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID")

if not BOT_TOKEN or not ADMIN_GROUP_ID:
    raise RuntimeError("BOT_TOKEN або ADMIN_GROUP_ID не задані")

ADMIN_GROUP_ID = int(ADMIN_GROUP_ID)

# ================== STORAGE ==================
users = {}
REQUEST_COUNTER = 0
stats_requests = []

# ================== MAPS ==================
PARKING_MAP = {
    "park_yes": "Так",
    "park_no": "Ні",
    "park_later": "Пізніше",
}

VIEW_MAP = {
    "view_online": "Онлайн",
    "view_offline": "Фізичний",
    "view_both": "Обидва варіанти",
}

LOCATION_MAP = {
    "loc_ua": "Україна",
    "loc_sk": "Словаччина",
}

STATUS_MAP = {
    "status_search": "🟡 В пошуках",
    "status_reserved": "🟢 Мають резервацію",
    "status_self": "🔵 Самі знайшли",
    "status_other": "🟠 Знайшов чужий маклер",
    "status_stop": "⚫ Не шукають",
    "status_closed": "🔴 Закрили угоду",
}

# ================== HELPERS ==================
def build_summary(u, req_id, status="🟡 В пошуках"):
    tg = f"@{u['username']}" if u.get("username") else "—"
    return (
        f"📋 **Запит №{req_id}**\n"
        f"📌 Статус: {status}\n\n"
        f"👤 Імʼя: {u['name']}\n"
        f"🆔 Telegram: {tg}\n"
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

def status_keyboard(req_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟡 В пошуках", callback_data=f"status_search|{req_id}"),
            InlineKeyboardButton("🟢 Резервація", callback_data=f"status_reserved|{req_id}"),
        ],
        [
            InlineKeyboardButton("🔵 Самі знайшли", callback_data=f"status_self|{req_id}"),
            InlineKeyboardButton("🟠 Чужий маклер", callback_data=f"status_other|{req_id}"),
        ],
        [
            InlineKeyboardButton("⚫ Не шукають", callback_data=f"status_stop|{req_id}"),
            InlineKeyboardButton("🔴 Закрили угоду", callback_data=f"status_closed|{req_id}"),
        ],
    ])

# ================== START ==================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id] = {
        "step": "deal",
        "username": update.effective_user.username,
    }
    kb = [
        [InlineKeyboardButton("🏠 Оренда", callback_data="deal_rent")],
        [InlineKeyboardButton("🏡 Купівля", callback_data="deal_buy")],
    ]
    await update.message.reply_text("👋 Що вас цікавить?", reply_markup=InlineKeyboardMarkup(kb))

# ================== DEAL ==================
async def deal_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["deal"] = "Оренда" if q.data == "deal_rent" else "Купівля"
    u["step"] = "property"

    kb = [
        [InlineKeyboardButton("🛏 Ліжко-місце", callback_data="prop_Ліжко-місце")],
        [InlineKeyboardButton("🏢 Студія", callback_data="prop_Студія")],
        [InlineKeyboardButton("1️⃣ 1-кімнатна", callback_data="prop_1-кімнатна")],
        [InlineKeyboardButton("2️⃣ 2-кімнатна", callback_data="prop_2-кімнатна")],
        [InlineKeyboardButton("3️⃣ 3-кімнатна", callback_data="prop_3-кімнатна")],
        [InlineKeyboardButton("✍️ Свій варіант", callback_data="prop_custom")],
    ]
    await q.message.reply_text("🏡 Тип житла:", reply_markup=InlineKeyboardMarkup(kb))

# ================== PROPERTY ==================
async def property_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
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

# ================== TEXT FLOW ==================
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
        await update.message.reply_text("🧒 Чи маєте дітей? Якщо ні — «Ні»")

    elif step == "children":
        u["children"] = t
        u["step"] = "pets"
        await update.message.reply_text(
            "🐾 Чи маєте тваринок?\n"
            "Якщо так — напишіть яку і коротко.\n"
            "Якщо ні — «Ні»"
        )

    elif step == "pets":
        u["pets"] = t
        u["step"] = "parking"
        kb = [
            [InlineKeyboardButton("Так", callback_data="park_yes")],
            [InlineKeyboardButton("Ні", callback_data="park_no")],
            [InlineKeyboardButton("Пізніше", callback_data="park_later")],
        ]
        await update.message.reply_text("🚗 Чи потрібне паркування?", reply_markup=InlineKeyboardMarkup(kb))

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
            [InlineKeyboardButton("✍️ Інша країна", callback_data="loc_custom")],
        ]
        await update.message.reply_text("🌍 Де ви зараз?", reply_markup=InlineKeyboardMarkup(kb))

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
            [InlineKeyboardButton("❌ Ні", callback_data="confirm_no")],
        ]
        await update.message.reply_text(
            build_summary(u, u["req_id"]),
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )

# ================== CALLBACKS ==================
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
    kb = [
        [InlineKeyboardButton("💻 Онлайн", callback_data="view_online")],
        [InlineKeyboardButton("🚶 Фізичний", callback_data="view_offline")],
        [InlineKeyboardButton("🔁 Обидва варіанти", callback_data="view_both")],
    ]
    await msg.reply_text("👀 Який формат огляду?", reply_markup=InlineKeyboardMarkup(kb))

async def view_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["view_format"] = VIEW_MAP[q.data]
    u["step"] = "contact"

    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Поділитись контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await q.message.reply_text("📞 Поділіться контактом для пошуку житла:", reply_markup=kb)

async def contact_handler(update: Update, ctx):
    u = users[update.effective_user.id]
    u["phone"] = update.message.contact.phone_number
    u["step"] = "name"
    await update.message.reply_text("👤 Як до вас можемо звертатись?")

async def confirm_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "confirm_yes":
        kb = [
            [InlineKeyboardButton("✅ Так", callback_data="terms_yes")],
            [InlineKeyboardButton("❌ Ні", callback_data="terms_no")],
        ]
        await q.message.reply_text(
            "ℹ️ **Умови співпраці:**\n\n"
            "• депозит може дорівнювати орендній платі\n"
            "• оплачується повна або часткова комісія ріелтору\n"
            "• можливий подвійний депозит при дітях або тваринах\n\n"
            "Чи погоджуєтесь?",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )
    else:
        users.pop(q.from_user.id, None)
        await q.message.reply_text("❌ Запит скасовано.")

async def terms_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "terms_yes":
        text = build_summary(u, u["req_id"])
        msg = await ctx.bot.send_message(
            ADMIN_GROUP_ID,
            text,
            parse_mode="Markdown",
            reply_markup=status_keyboard(u["req_id"]),
        )

        stats_requests.append({
            "date": datetime.now(),
            "property": u["property"],
            "status": "В пошуках",
        })

        await q.message.reply_text(
            "✅ Запит відправлено маклеру.\n\n"
            "📞 Маклер звʼяжеться з вами протягом **24–48 годин**.\n\n"
            "🏘 Долучайтесь до групи з актуальними пропозиціями:\n"
            "https://t.me/+IhcJixOP1_QyNjM0",
            parse_mode="Markdown",
        )

    users.pop(q.from_user.id, None)

# ================== STATUS CHANGE ==================
async def status_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()

    data, req_id = q.data.split("|")
    status = STATUS_MAP[data]

    text = q.message.text.split("\n")
    text[1] = f"📌 Статус: {status}"
    new_text = "\n".join(text)

    await q.message.edit_text(
        new_text,
        parse_mode="Markdown",
        reply_markup=status_keyboard(req_id),
    )

# ================== STATS ==================
def build_stats(days):
    since = datetime.now() - timedelta(days=days)
    filtered = [r for r in stats_requests if r["date"] >= since]

    active = [r for r in filtered if r["status"] in ["В пошуках", "Мають резервацію"]]
    by_prop = {}

    for r in active:
        by_prop[r["property"]] = by_prop.get(r["property"], 0) + 1

    text = f"📊 Статистика за {days} днів\n\n"
    text += f"📌 Всього запитів: {len(filtered)}\n"
    text += f"🟢 Активних: {len(active)}\n\n"
    text += "🏡 Попит по типу житла:\n"

    for k, v in sorted(by_prop.items(), key=lambda x: x[1], reverse=True):
        text += f"• {k}: {v}\n"

    return text

async def stats_today(update: Update, ctx):
    await update.message.reply_text(build_stats(1))

async def stats_week(update: Update, ctx):
    await update.message.reply_text(build_stats(7))

async def stats_month(update: Update, ctx):
    await update.message.reply_text(build_stats(30))

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats_today", stats_today))
    app.add_handler(CommandHandler("stats_week", stats_week))
    app.add_handler(CommandHandler("stats_month", stats_month))

    app.add_handler(CallbackQueryHandler(deal_handler, pattern="^deal_"))
    app.add_handler(CallbackQueryHandler(property_handler, pattern="^prop_"))
    app.add_handler(CallbackQueryHandler(parking_handler, pattern="^park_"))
    app.add_handler(CallbackQueryHandler(location_handler, pattern="^loc_"))
    app.add_handler(CallbackQueryHandler(view_handler, pattern="^view_"))
    app.add_handler(CallbackQueryHandler(confirm_handler, pattern="^confirm_"))
    app.add_handler(CallbackQueryHandler(terms_handler, pattern="^terms_"))
    app.add_handler(CallbackQueryHandler(status_handler, pattern="^status_"))

    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
