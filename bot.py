import os
from datetime import datetime
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

# ===================== ENV =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID")

if not BOT_TOKEN or not ADMIN_GROUP_ID:
    raise RuntimeError("BOT_TOKEN або ADMIN_GROUP_ID не задані")

ADMIN_GROUP_ID = int(ADMIN_GROUP_ID)

# ===================== STORAGE =====================
users = {}
REQUEST_COUNTER = 0
STATS = []

# ===================== MAPS =====================
LOCATION_MAP = {
    "loc_ua": "Україна",
    "loc_sk": "Словаччина",
}

VIEW_MAP = {
    "view_online": "Онлайн",
    "view_offline": "Фізичний",
    "view_both": "Обидва варіанти",
}

STATUS_MAP = {
    "status_search": "🟡 В пошуках",
    "status_reserved": "🟢 Мають резервацію",
    "status_self": "🔵 Самі знайшли",
    "status_other": "🟠 Чужий маклер",
    "status_stop": "⚫ Не шукають",
    "status_closed": "🔴 Закрили угоду",
}

# ===================== HELPERS =====================
def status_keyboard(req_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟡 В пошуках", callback_data=f"status_search|{req_id}"),
            InlineKeyboardButton("🟢 Мають резервацію", callback_data=f"status_reserved|{req_id}")
        ],
        [
            InlineKeyboardButton("🔵 Самі знайшли", callback_data=f"status_self|{req_id}"),
            InlineKeyboardButton("🟠 Чужий маклер", callback_data=f"status_other|{req_id}")
        ],
        [
            InlineKeyboardButton("⚫ Не шукають", callback_data=f"status_stop|{req_id}"),
            InlineKeyboardButton("🔴 Закрили угоду", callback_data=f"status_closed|{req_id}")
        ]
    ])

def summary(u):
    return (
        f"📋 **Запит №{u['req_id']}**\n"
        f"📌 Статус: {u['status']}\n\n"
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
        f"💶 Бюджет оренда: {u['budget']}\n"
        f"⏰ Огляди: {u['view_time']}\n"
        f"✨ Побажання: {u['wishes']}\n"
        f"🌍 Зараз в: {u['location']}\n"
        f"👀 Формат огляду: {u['view_format']}"
    )

# ===================== START =====================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users.pop(update.effective_user.id, None)
    await update.message.reply_text(
        "👋 Що вас цікавить?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Оренда", callback_data="deal_rent")],
            [InlineKeyboardButton("🏡 Купівля", callback_data="deal_buy")]
        ])
    )

# ===================== CALLBACKS =====================
async def deal_cb(update: Update, ctx):
    q = update.callback_query
    await q.answer()

    users[q.from_user.id] = {
        "deal": "Оренда" if q.data == "deal_rent" else "Купівля",
        "step": "property",
        "username": q.from_user.username or "—",
        "status": "🟡 В пошуках",
        "created": datetime.now()
    }

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

async def property_cb(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "prop_custom":
        u["step"] = "property_custom"
        await q.message.reply_text("✍️ Напишіть тип житла:")
    else:
        u["property"] = q.data.replace("prop_", "")
        u["step"] = "city"
        await q.message.reply_text("📍 В якому місті шукаєте житло?")

async def location_cb(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "loc_custom":
        u["step"] = "location_custom"
        await q.message.reply_text("✍️ Напишіть країну:")
    else:
        u["location"] = LOCATION_MAP[q.data]
        u["step"] = "view_format"
        await ask_view_format(q.message)

async def view_cb(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    u["view_format"] = VIEW_MAP[q.data]
    u["step"] = "contact"

    await q.message.reply_text(
        "📞 Поділіться контактом для пошуку житла:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📲 Поділитись контактом", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )

async def status_cb(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    status_key, req_id = q.data.split("|")

    for u in users.values():
        if u.get("req_id") == req_id:
            u["status"] = STATUS_MAP[status_key]
            await q.message.edit_text(
                summary(u),
                reply_markup=status_keyboard(req_id),
                parse_mode="Markdown"
            )
            break

# ===================== TEXT HANDLER =====================
async def text_handler(update: Update, ctx):
    uid = update.effective_user.id
    if uid not in users:
        return

    u = users[uid]
    t = update.message.text

    step = u["step"]

    if step == "property_custom":
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
        await update.message.reply_text("🧒 Чи маєте дітей? (якщо ні — напишіть Ні)")

    elif step == "children":
        u["children"] = t
        u["step"] = "pets"
        await update.message.reply_text("🐾 Чи маєте тваринок? Якщо так — напишіть яку і коротко.")

    elif step == "pets":
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
        await update.message.reply_text(
            "🌍 Де ви зараз?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc_ua")],
                [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc_sk")],
                [InlineKeyboardButton("✍️ Інша країна", callback_data="loc_custom")]
            ])
        )

    elif step == "location_custom":
        u["location"] = t
        u["step"] = "view_format"
        await ask_view_format(update.message)

    elif step == "name":
        global REQUEST_COUNTER
        REQUEST_COUNTER += 1

        u["name"] = t
        u["req_id"] = str(REQUEST_COUNTER)

        msg = await ctx.bot.send_message(
            ADMIN_GROUP_ID,
            summary(u),
            reply_markup=status_keyboard(u["req_id"]),
            parse_mode="Markdown"
        )

        await update.message.reply_text(
            "✅ Запит відправлено маклеру.\n"
            "Ми звʼяжемось з вами протягом **24–48 годин**.\n\n"
            "🔗 Долучайтесь до нашої групи з пропозиціями житла:\n"
            "https://t.me/+IhcJixOP1_QyNjM0",
            parse_mode="Markdown"
        )

        STATS.append(u.copy())
        users.pop(uid, None)

async def ask_view_format(msg):
    await msg.reply_text(
        "👀 Який формат огляду?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💻 Онлайн", callback_data="view_online")],
            [InlineKeyboardButton("🚶 Фізичний", callback_data="view_offline")],
            [InlineKeyboardButton("🔁 Обидва варіанти", callback_data="view_both")]
        ])
    )

async def contact_handler(update: Update, ctx):
    u = users[update.effective_user.id]
    u["phone"] = update.message.contact.phone_number
    u["step"] = "name"
    await update.message.reply_text("👤 Як до вас можемо звертатись?")

# ===================== PARKING =====================
async def parking_cb(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["parking"] = q.data.replace("park_", "").capitalize()
    u["step"] = "move_in"
    await q.message.reply_text("📅 Яка найкраща дата для заїзду?")

# ===================== MAIN =====================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(deal_cb, pattern="^deal_"))
    app.add_handler(CallbackQueryHandler(property_cb, pattern="^prop_"))
    app.add_handler(CallbackQueryHandler(location_cb, pattern="^loc_"))
    app.add_handler(CallbackQueryHandler(view_cb, pattern="^view_"))
    app.add_handler(CallbackQueryHandler(status_cb, pattern="^status_"))
    app.add_handler(CallbackQueryHandler(parking_cb, pattern="^park_"))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
