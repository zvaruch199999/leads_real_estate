from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN, ADMIN_GROUP_ID

users = {}
REQUEST_COUNTER = 0

# =========================
# MAPS
# =========================

PROPERTY_MAP = {
    "bed": "Ліжко-місце",
    "studio": "Студія",
    "1": "1-кімнатна",
    "2": "2-кімнатна",
    "3": "3-кімнатна",
    "house": "Будинок",
}

STATUS_MAP = {
    "search": "🟡 В пошуках",
    "reserve": "🟢 Мають резервацію",
    "deal_closed": "🔴 Закрили угоду",
    "self_found": "🔵 Самі знайшли",
    "other_broker": "🟠 Знайшов чужий маклер",
    "not_looking": "⚫️ Не шукають вже",
}

# =========================
# HELPERS
# =========================

def status_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🟡 В пошуках", callback_data="status_search"),
                InlineKeyboardButton("🟢 Мають резервацію", callback_data="status_reserve"),
            ],
            [
                InlineKeyboardButton("🔵 Самі знайшли", callback_data="status_self_found"),
                InlineKeyboardButton("🟠 Чужий маклер", callback_data="status_other_broker"),
            ],
            [
                InlineKeyboardButton("⚫️ Не шукають", callback_data="status_not_looking"),
                InlineKeyboardButton("🔴 Закрили угоду", callback_data="status_deal_closed"),
            ],
        ]
    )


def build_summary(u):
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
        f"🌍 Зараз в: {u['location']}\n"
        f"👀 Формат огляду: {u['view_format']}"
    )

# =========================
# START
# =========================

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id] = {
        "step": "deal",
        "username": update.effective_user.username or "немає",
    }

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🏠 Оренда", callback_data="rent")],
            [InlineKeyboardButton("🏡 Купівля", callback_data="buy")],
        ]
    )

    await update.message.reply_text(
        "👋 Вітаємо!\nЩо вас цікавить?",
        reply_markup=kb,
    )

# =========================
# DEAL
# =========================

async def deal_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(None)

    u = users[q.from_user.id]
    u["deal"] = "Оренда" if q.data == "rent" else "Купівля"
    u["step"] = "property"

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛏 Ліжко-місце", callback_data="prop_bed")],
            [InlineKeyboardButton("Студія", callback_data="prop_studio")],
            [InlineKeyboardButton("1-кімнатна", callback_data="prop_1")],
            [InlineKeyboardButton("2-кімнатна", callback_data="prop_2")],
            [InlineKeyboardButton("3-кімнатна", callback_data="prop_3")],
            [InlineKeyboardButton("Будинок", callback_data="prop_house")],
            [InlineKeyboardButton("✍️ Свій варіант", callback_data="prop_custom")],
        ]
    )

    await q.message.reply_text("🏡 Тип житла:", reply_markup=kb)

# =========================
# PROPERTY
# =========================

async def property_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    await q.message.edit_reply_markup(None)

    u = users[q.from_user.id]

    if q.data == "prop_custom":
        u["step"] = "property_custom"
        await q.message.reply_text("✍️ Напишіть свій варіант житла:")
        return

    key = q.data.replace("prop_", "")
    u["property"] = PROPERTY_MAP[key]
    u["step"] = "city"

    await q.message.reply_text("📍 В якому місті шукаєте житло?")

# =========================
# TEXT FLOW
# =========================

async def text_handler(update: Update, ctx):
    uid = update.effective_user.id
    if uid not in users:
        return

    u = users[uid]
    t = update.message.text

    if u["step"] == "property_custom":
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
        await update.message.reply_text("👥 Для кого шукаєте житло?")

    elif u["step"] == "for_whom":
        u["for_whom"] = t
        u["step"] = "job"
        await update.message.reply_text("💼 Чим ви займаєтесь?")

    elif u["step"] == "job":
        u["job"] = t
        u["step"] = "children"
        await update.message.reply_text("🧒 Чи маєте дітей? Якщо ні — напишіть «Ні».")

    elif u["step"] == "children":
        u["children"] = t
        u["step"] = "pets"
        await update.message.reply_text(
            "🐾 Чи маєте тваринок?\n"
            "Якщо так — напишіть яку і коротко про неї.\n"
            "Якщо ні — напишіть «Ні»."
        )

    elif u["step"] == "pets":
        u["pets"] = t
        u["step"] = "parking"

        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Так", callback_data="park_yes")],
                [InlineKeyboardButton("Ні", callback_data="park_no")],
                [InlineKeyboardButton("Пізніше", callback_data="park_later")],
            ]
        )
        await update.message.reply_text("🚗 Чи потрібне паркування?", reply_markup=kb)

    elif u["step"] == "move_in":
        u["move_in"] = t
        u["step"] = "budget"
        await update.message.reply_text("💶 Який бюджет на оренду в місяць (від–до €)?")

    elif u["step"] == "budget":
        u["budget"] = t
        u["step"] = "view_time"
        await update.message.reply_text("⏰ Коли ви доступні для оглядів?")

    elif u["step"] == "view_time":
        u["view_time"] = t
        u["step"] = "location"

        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc_ua")],
                [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc_sk")],
                [InlineKeyboardButton("✍️ Інша країна", callback_data="loc_custom")],
            ]
        )
        await update.message.reply_text("🌍 Ви в країні?", reply_markup=kb)

    elif u["step"] == "custom_location":
        u["location"] = t
        u["step"] = "view_format"
        await ask_view_format(update.message)

# =========================
# ДАЛІ КОД БЕЗ ЗМІН
# (паркування, локація, формат огляду, підтвердження,
#  статуси, main — залишаються такими ж)
# =========================
