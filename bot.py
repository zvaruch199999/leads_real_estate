import os
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
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

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID")

if not BOT_TOKEN or not ADMIN_GROUP_ID:
    raise RuntimeError("BOT_TOKEN або ADMIN_GROUP_ID не задані")

ADMIN_GROUP_ID = int(ADMIN_GROUP_ID)

# ================== STORAGE ==================
users = {}
REQUEST_COUNTER = 0

STATUS_MAP = {
    "search": "🟡 В пошуках",
    "reserve": "🟢 Мають резервацію",
    "self": "🔵 Самі знайшли",
    "other": "🟠 Знайшов чужий маклер",
    "stop": "⚫ Не шукають",
    "deal": "🔴 Закрили угоду",
}

# ================== HELPERS ==================
def summary(u, rid):
    return (
        f"📋 **Запит №{rid}**\n"
        f"📌 Статус: {STATUS_MAP[u['status']]}\n\n"
        f"👤 Імʼя: {u['name']}\n"
        f"🆔 Telegram: @{u['username']}\n"
        f"📞 Телефон: {u['phone']}\n\n"
        f"🏠 Тип угоди: {u['deal']}\n"
        f"🏡 Житло: {u['property']}\n"
        f"📍 Місто: {u['city']} / {u['district']}\n"
        f"👥 Для кого: {u['for_whom']}\n"
        f"💼 Діяльність: {u['job']}\n"
        f"🧒 Діти: {u['children']}\n"
        f"🐾 Тварини: {u['pets']}\n"
        f"🚗 Паркування: {u['parking']}\n"
        f"📅 Заїзд: {u['move_in']}\n"
        f"⏰ Огляди: {u['view_time']}\n"
        f"✨ Побажання: {u['wishes']}\n"
        f"💶 Бюджет оренда: {u['budget']}\n"
        f"🌍 Зараз в: {u['location']}\n"
        f"👀 Формат огляду: {u['view_format']}"
    )

def status_keyboard(rid):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟡 В пошуках", callback_data=f"status:{rid}:search"),
            InlineKeyboardButton("🟢 Мають резервацію", callback_data=f"status:{rid}:reserve"),
        ],
        [
            InlineKeyboardButton("🔵 Самі знайшли", callback_data=f"status:{rid}:self"),
            InlineKeyboardButton("🟠 Чужий маклер", callback_data=f"status:{rid}:other"),
        ],
        [
            InlineKeyboardButton("⚫ Не шукають", callback_data=f"status:{rid}:stop"),
            InlineKeyboardButton("🔴 Закрили угоду", callback_data=f"status:{rid}:deal"),
        ],
    ])

# ================== START ==================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id] = {
        "step": "deal",
        "status": "search",
        "username": update.effective_user.username or "—",
        "created": datetime.now(),
    }

    await update.message.reply_text(
        "👋 Що вас цікавить?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Оренда", callback_data="deal:rent")],
            [InlineKeyboardButton("🏡 Купівля", callback_data="deal:buy")],
        ])
    )

# ================== CALLBACK HANDLERS ==================
async def callback_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = users.get(uid)

    if not u:
        return

    data = q.data

    # DEAL
    if data.startswith("deal:"):
        u["deal"] = "Оренда" if "rent" in data else "Купівля"
        u["step"] = "property"
        await q.message.reply_text(
            "🏡 Тип житла:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛏 Ліжко-місце", callback_data="prop:bed")],
                [InlineKeyboardButton("🏢 Студія", callback_data="prop:studio")],
                [InlineKeyboardButton("1️⃣ 1-кімнатна", callback_data="prop:1")],
                [InlineKeyboardButton("2️⃣ 2-кімнатна", callback_data="prop:2")],
                [InlineKeyboardButton("3️⃣ 3-кімнатна", callback_data="prop:3")],
                [InlineKeyboardButton("✍️ Свій варіант", callback_data="prop:custom")],
            ])
        )
        return

    # PROPERTY
    if data.startswith("prop:"):
        if data.endswith("custom"):
            u["step"] = "property_custom"
            await q.message.reply_text("✍️ Напишіть тип житла:")
        else:
            u["property"] = data.split(":")[1]
            u["step"] = "city"
            await q.message.reply_text("📍 В якому місті шукаєте житло?")
        return

    # LOCATION BUTTONS (FIXED)
    if data.startswith("loc:") and u["step"] == "location":
        val = data.split(":")[1]
        if val == "custom":
            u["step"] = "location_custom"
            await q.message.reply_text("✍️ Напишіть країну:")
        else:
            u["location"] = "Україна" if val == "ua" else "Словаччина"
            u["step"] = "view_format"
            await q.message.reply_text(
                "👀 Формат огляду?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💻 Онлайн", callback_data="view:online")],
                    [InlineKeyboardButton("🚶 Фізичний", callback_data="view:offline")],
                    [InlineKeyboardButton("🔁 Обидва", callback_data="view:both")],
                ])
            )
        return

    # VIEW FORMAT
    if data.startswith("view:"):
        u["view_format"] = data.split(":")[1]
        u["step"] = "contact"
        await q.message.reply_text(
            "📞 Поділіться контактом для пошуку житла",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📞 Поділитись контактом", request_contact=True)]],
                resize_keyboard=True,
                one_time_keyboard=True,
            )
        )
        return

    # STATUS CHANGE (INLINE)
    if data.startswith("status:"):
        _, rid, st = data.split(":")
        u["status"] = st
        await q.edit_message_text(
            summary(u, rid),
            reply_markup=status_keyboard(rid),
            parse_mode="Markdown"
        )

# ================== TEXT HANDLER ==================
async def text_handler(update: Update, ctx):
    uid = update.effective_user.id
    if uid not in users:
        return

    u = users[uid]
    t = update.message.text

    if u["step"] == "property_custom":
        u["property"] = t
        u["step"] = "city"
        await update.message.reply_text("📍 Місто?")
    elif u["step"] == "city":
        u["city"] = t
        u["step"] = "district"
        await update.message.reply_text("🗺 Район?")
    elif u["step"] == "district":
        u["district"] = t
        u["step"] = "for_whom"
        await update.message.reply_text("👥 Для кого житло?")
    elif u["step"] == "for_whom":
        u["for_whom"] = t
        u["step"] = "job"
        await update.message.reply_text("💼 Ваша діяльність?")
    elif u["step"] == "job":
        u["job"] = t
        u["step"] = "children"
        await update.message.reply_text("🧒 Діти? (Ні / вік)")
    elif u["step"] == "children":
        u["children"] = t
        u["step"] = "pets"
        await update.message.reply_text("🐾 Тварини? Якщо так — опишіть")
    elif u["step"] == "pets":
        u["pets"] = t
        u["step"] = "parking"
        await update.message.reply_text("🚗 Паркування? (Так / Ні / Пізніше)")
    elif u["step"] == "parking":
        u["parking"] = t
        u["step"] = "move_in"
        await update.message.reply_text("📅 Дата заїзду?")
    elif u["step"] == "move_in":
        u["move_in"] = t
        u["step"] = "view_time"
        await update.message.reply_text("⏰ Коли доступні для оглядів?")
    elif u["step"] == "view_time":
        u["view_time"] = t
        u["step"] = "wishes"
        await update.message.reply_text("✨ Напишіть особливі побажання до житла")
    elif u["step"] == "wishes":
        u["wishes"] = t
        u["step"] = "budget"
        await update.message.reply_text("💶 Який бюджет на оренду в місяць (від–до €)?")
    elif u["step"] == "budget":
        u["budget"] = t
        u["step"] = "location"
        await update.message.reply_text(
            "🌍 Де ви зараз?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc:ua")],
                [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc:sk")],
                [InlineKeyboardButton("✍️ Інша країна", callback_data="loc:custom")],
            ])
        )
    elif u["step"] == "location_custom":
        u["location"] = t
        u["step"] = "view_format"
        await update.message.reply_text(
            "👀 Формат огляду?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💻 Онлайн", callback_data="view:online")],
                [InlineKeyboardButton("🚶 Фізичний", callback_data="view:offline")],
                [InlineKeyboardButton("🔁 Обидва", callback_data="view:both")],
            ])
        )

# ================== CONTACT ==================
async def contact_handler(update: Update, ctx):
    uid = update.effective_user.id
    u = users[uid]
    u["phone"] = update.message.contact.phone_number
    u["step"] = "name"
    await update.message.reply_text("👤 Як до вас звертатись?")

# ================== NAME + SEND ==================
async def name_handler(update: Update, ctx):
    global REQUEST_COUNTER
    uid = update.effective_user.id
    u = users[uid]

    REQUEST_COUNTER += 1
    rid = str(REQUEST_COUNTER)
    u["name"] = update.message.text
    u["req_id"] = rid

    msg = await ctx.bot.send_message(
        ADMIN_GROUP_ID,
        summary(u, rid),
        reply_markup=status_keyboard(rid),
        parse_mode="Markdown"
    )

    u["msg_id"] = msg.message_id

    await update.message.reply_text(
        "✅ Запит відправлено маклеру.\n"
        "Ми звʼяжемось з вами протягом 24–48 годин.\n\n"
        "🔗 Долучайтесь до нашої групи з пропозиціями житла:\n"
        "https://t.me/+IhcJixOP1_QyNjM0"
    )

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, name_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
