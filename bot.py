from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
import os

from config import BOT_TOKEN, ADMIN_GROUP_ID

# =========================
# ГЛОБАЛЬНІ ДАНІ
# =========================
users = {}
REQUEST_COUNTER = 0

STATUS_LABELS = {
    "search": "🟡 В пошуках",
    "reserved": "🟢 Мають резервацію",
    "self_found": "🔵 Самі знайшли",
    "other_agent": "🟠 Знайшов чужий маклер",
    "not_searching": "⚫ Не шукають",
    "closed": "🔴 Закрили угоду"
}

PROPERTY_TYPES = [
    "🛏 Ліжко-місце",
    "🏠 Студія",
    "🏢 1-кімнатна",
    "🏢 2-кімнатна",
    "🏢 3-кімнатна",
    "🏡 Будинок",
    "✍️ Свій варіант"
]

# =========================
# ДОПОМІЖНІ
# =========================
def reset_user(uid):
    users.pop(uid, None)

def build_summary(u):
    return (
        f"📋 **Запит №{u['req_id']}**\n"
        f"📌 Статус: {STATUS_LABELS[u['status']]}\n\n"
        f"👤 Імʼя: {u['name']}\n"
        f"🆔 Telegram: @{u['username']}\n"
        f"📞 Телефон: {u['phone']}\n\n"
        f"🏠 Тип угоди: {u['deal']}\n"
        f"🏡 Тип житла: {u['property']}\n"
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

def status_keyboard(req_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟡 В пошуках", callback_data=f"status:search:{req_id}"),
            InlineKeyboardButton("🟢 Мають резервацію", callback_data=f"status:reserved:{req_id}")
        ],
        [
            InlineKeyboardButton("🔵 Самі знайшли", callback_data=f"status:self_found:{req_id}"),
            InlineKeyboardButton("🟠 Чужий маклер", callback_data=f"status:other_agent:{req_id}")
        ],
        [
            InlineKeyboardButton("⚫ Не шукають", callback_data=f"status:not_searching:{req_id}"),
            InlineKeyboardButton("🔴 Закрили угоду", callback_data=f"status:closed:{req_id}")
        ]
    ])

# =========================
# START / RESET
# =========================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    reset_user(update.effective_user.id)
    users[update.effective_user.id] = {
        "step": "deal",
        "status": "search",
        "username": update.effective_user.username or "немає"
    }

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Оренда", callback_data="deal:rent")],
        [InlineKeyboardButton("🏡 Купівля", callback_data="deal:buy")]
    ])
    await update.message.reply_text("👋 Що вас цікавить?", reply_markup=kb)

# =========================
# CALLBACK HANDLERS
# =========================
async def deal_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["deal"] = "Оренда" if "rent" in q.data else "Купівля"
    u["step"] = "property"

    kb = InlineKeyboardMarkup([[InlineKeyboardButton(p, callback_data=f"property:{p}")] for p in PROPERTY_TYPES])
    await q.message.reply_text("🏡 Тип житла:", reply_markup=kb)

async def property_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    value = q.data.split(":", 1)[1]
    if "Свій" in value:
        u["step"] = "property_custom"
        await q.message.reply_text("✍️ Напишіть свій варіант житла:")
    else:
        u["property"] = value
        u["step"] = "city"
        await q.message.reply_text("📍 В якому місті шукаєте житло?")

async def status_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    _, status, req_id = q.data.split(":")
    for u in users.values():
        if str(u.get("req_id")) == req_id:
            u["status"] = status
            await q.message.edit_text(
                build_summary(u),
                reply_markup=status_keyboard(req_id),
                parse_mode="Markdown"
            )
            break

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
        await update.message.reply_text("🐾 Чи маєте тваринок? Якщо так — опишіть, якщо ні — «Ні».")

    elif u["step"] == "pets":
        u["pets"] = t
        u["step"] = "parking"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Так", callback_data="parking:Так")],
            [InlineKeyboardButton("Ні", callback_data="parking:Ні")],
            [InlineKeyboardButton("Пізніше", callback_data="parking:Пізніше")]
        ])
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
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇺🇦 В Україні", callback_data="location:Україна")],
            [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="location:Словаччина")],
            [InlineKeyboardButton("✍️ Інша країна", callback_data="location:custom")]
        ])
        await update.message.reply_text("🌍 Ви в країні?", reply_markup=kb)

    elif u["step"] == "location_custom":
        u["location"] = t
        u["step"] = "view_format"
        await ask_view_format(update)

    elif u["step"] == "name":
        global REQUEST_COUNTER
        REQUEST_COUNTER += 1
        u["name"] = t
        u["req_id"] = REQUEST_COUNTER

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Так", callback_data="confirm:yes")],
            [InlineKeyboardButton("❌ Ні", callback_data="confirm:no")]
        ])
        await update.message.reply_text(
            build_summary(u) + "\n\nВсе вірно?",
            reply_markup=kb,
            parse_mode="Markdown"
        )

# =========================
# ІНШІ CALLBACKS
# =========================
async def parking_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["parking"] = q.data.split(":")[1]
    u["step"] = "move_in"
    await q.message.reply_text("📅 Яка найкраща дата для заїзду?")

async def location_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    value = q.data.split(":")[1]
    if value == "custom":
        u["step"] = "location_custom"
        await q.message.reply_text("✍️ Напишіть країну:")
    else:
        u["location"] = value
        u["step"] = "view_format"
        await ask_view_format(update)

async def ask_view_format(update: Update):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💻 Онлайн", callback_data="view:Онлайн")],
        [InlineKeyboardButton("🚶 Фізичний", callback_data="view:Фізичний")],
        [InlineKeyboardButton("🔁 Обидва варіанти", callback_data="view:Обидва")]
    ])
    await update.message.reply_text("👀 Формат огляду?", reply_markup=kb)

async def view_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["view_format"] = q.data.split(":")[1]
    u["step"] = "contact"

    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Поділитись контактом для пошуку житла", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
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
    if "no" in q.data:
        reset_user(q.from_user.id)
        await q.message.reply_text("❌ Запит скасовано.")
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Так", callback_data="terms:yes")],
        [InlineKeyboardButton("❌ Ні", callback_data="terms:no")]
    ])
    await q.message.reply_text(
        "ℹ️ **Умови співпраці:**\n"
        "• депозит може дорівнювати орендній платі\n"
        "• оплачується повна або часткова комісія ріелтору\n"
        "• можливий подвійний депозит при дітях або тваринах\n\n"
        "Чи погоджуєтесь?",
        reply_markup=kb,
        parse_mode="Markdown"
    )

async def terms_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    if "no" in q.data:
        reset_user(q.from_user.id)
        await q.message.reply_text("❌ Дякуємо за відповідь.")
        return

    u = users[q.from_user.id]
    msg = await ctx.bot.send_message(
        ADMIN_GROUP_ID,
        build_summary(u),
        reply_markup=status_keyboard(u["req_id"]),
        parse_mode="Markdown"
    )

    await q.message.reply_text(
        "✅ Запит відправлено маклеру.\n"
        "Ми звʼяжемось з вами протягом **24–48 годин**.\n\n"
        "👉 Долучайтесь до нашої групи з пропозиціями житла в Братиславі:\n"
        "https://t.me/+IhcJixOP1_QyNjM0",
        parse_mode="Markdown"
    )
    reset_user(q.from_user.id)

# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(deal_handler, pattern="^deal"))
    app.add_handler(CallbackQueryHandler(property_handler, pattern="^property"))
    app.add_handler(CallbackQueryHandler(parking_handler, pattern="^parking"))
    app.add_handler(CallbackQueryHandler(location_handler, pattern="^location"))
    app.add_handler(CallbackQueryHandler(view_handler, pattern="^view"))
    app.add_handler(CallbackQueryHandler(confirm_handler, pattern="^confirm"))
    app.add_handler(CallbackQueryHandler(terms_handler, pattern="^terms"))
    app.add_handler(CallbackQueryHandler(status_handler, pattern="^status"))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
