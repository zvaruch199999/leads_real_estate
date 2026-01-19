import os
from datetime import datetime, timedelta
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, ContextTypes, filters
)

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))
ADMIN_ID = 1057216609
COOLDOWN_HOURS = 2

if not BOT_TOKEN or not ADMIN_GROUP_ID:
    raise RuntimeError("BOT_TOKEN або ADMIN_GROUP_ID не задані")

# ================== STATES ==================
(
    CHOOSE_FLOW,

    # RENT
    RENT_TYPE, RENT_CITY, RENT_DISTRICT, RENT_FOR_WHOM,
    RENT_JOB, RENT_CHILDREN, RENT_PETS, RENT_PARKING,
    RENT_MOVEIN, RENT_BUDGET, RENT_VIEWTIME, RENT_LOCATION,
    RENT_VIEWFORMAT, RENT_CONTACT, RENT_NAME, RENT_CONFIRM,

    # BUY
    BUY_TYPE, BUY_DETAILS, BUY_CITY, BUY_PRICE,
    BUY_FINANCE, BUY_TIME, BUY_VIEW, BUY_CONTACT,
    BUY_NAME, BUY_CONFIRM
) = range(26)

# ================== STORAGE ==================
LEADS = {}
LAST_REQUEST = {}

def can_create(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    last = LAST_REQUEST.get(user_id)
    if not last:
        return True
    return datetime.now() - last > timedelta(hours=COOLDOWN_HOURS)

def mark_request(user_id: int):
    LAST_REQUEST[user_id] = datetime.now()

def status_keyboard(lead_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟡 В пошуках", callback_data=f"status|{lead_id}|search"),
            InlineKeyboardButton("🟢 Резервація", callback_data=f"status|{lead_id}|reserve"),
        ],
        [
            InlineKeyboardButton("🔵 Самі знайшли", callback_data=f"status|{lead_id}|self"),
            InlineKeyboardButton("🟠 Чужий маклер", callback_data=f"status|{lead_id}|other"),
        ],
        [
            InlineKeyboardButton("⚫ Не шукають", callback_data=f"status|{lead_id}|stop"),
            InlineKeyboardButton("🔴 Закрили угоду", callback_data=f"status|{lead_id}|deal"),
        ]
    ])

# ================== START ==================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not can_create(uid):
        await update.message.reply_text(
            "⚠️ У вас вже є активна заявка і вона опрацьовується.\n"
            "Будь ласка, дочекайтесь її вирішення."
        )
        return ConversationHandler.END

    kb = ReplyKeyboardMarkup(
        [["🏠 Оренда", "🏡 Купівля"]],
        resize_keyboard=True
    )
    await update.message.reply_text(
        "Вітаємо! Що вас цікавить?",
        reply_markup=kb
    )
    return CHOOSE_FLOW

# ================== FLOW SELECT ==================
async def choose_flow(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    ctx.user_data.clear()

    if "Оренда" in text:
        await update.message.reply_text("1️⃣ Який тип житла шукаєте?")
        return RENT_TYPE

    if "Купівля" in text:
        await update.message.reply_text("1️⃣ Яку нерухомість шукаєте для купівлі?")
        return BUY_TYPE

    await update.message.reply_text("Оберіть варіант кнопкою ⬇️")
    return CHOOSE_FLOW

# ================== RENT FLOW ==================
async def rent_type(u, c): c.user_data["type"]=u.message.text; await u.message.reply_text("2️⃣ В якому місті?"); return RENT_CITY
async def rent_city(u,c): c.user_data["city"]=u.message.text; await u.message.reply_text("3️⃣ Який район?"); return RENT_DISTRICT
async def rent_district(u,c): c.user_data["district"]=u.message.text; await u.message.reply_text("4️⃣ Для кого житло?"); return RENT_FOR_WHOM
async def rent_for_whom(u,c): c.user_data["for"]=u.message.text; await u.message.reply_text("5️⃣ Чим ви займаєтесь?"); return RENT_JOB
async def rent_job(u,c): c.user_data["job"]=u.message.text; await u.message.reply_text("6️⃣ Чи є діти?"); return RENT_CHILDREN
async def rent_children(u,c): c.user_data["children"]=u.message.text; await u.message.reply_text("7️⃣ Чи є тваринки?"); return RENT_PETS
async def rent_pets(u,c): c.user_data["pets"]=u.message.text; await u.message.reply_text("8️⃣ Чи потрібне паркування?"); return RENT_PARKING
async def rent_parking(u,c): c.user_data["parking"]=u.message.text; await u.message.reply_text("9️⃣ Коли заїзд?"); return RENT_MOVEIN
async def rent_movein(u,c): c.user_data["movein"]=u.message.text; await u.message.reply_text("🔟 Бюджет оренди (від–до €)?"); return RENT_BUDGET
async def rent_budget(u,c): c.user_data["budget"]=u.message.text; await u.message.reply_text("1️⃣1️⃣ Коли доступні для оглядів?"); return RENT_VIEWTIME
async def rent_viewtime(u,c): c.user_data["viewtime"]=u.message.text; await u.message.reply_text("1️⃣2️⃣ Ви зараз в якій країні?"); return RENT_LOCATION
async def rent_location(u,c): c.user_data["location"]=u.message.text; await u.message.reply_text("1️⃣3️⃣ Формат огляду?"); return RENT_VIEWFORMAT
async def rent_viewformat(u,c):
    c.user_data["viewformat"]=u.message.text
    kb = ReplyKeyboardMarkup([[KeyboardButton("📞 Поділитись контактом", request_contact=True)]], resize_keyboard=True)
    await u.message.reply_text("1️⃣4️⃣ Контакт для звʼязку:", reply_markup=kb)
    return RENT_CONTACT

async def rent_contact(u,c):
    c.user_data["phone"] = u.message.contact.phone_number if u.message.contact else u.message.text
    await u.message.reply_text("1️⃣5️⃣ Як до вас звертатись?")
    return RENT_NAME

async def rent_name(u,c):
    c.user_data["name"]=u.message.text
    summary = "\n".join([f"{k}: {v}" for k,v in c.user_data.items()])
    await u.message.reply_text(f"📋 Перевірте дані:\n\n{summary}\n\nВсе вірно? (Так/Ні)")
    return RENT_CONFIRM

async def rent_confirm(u,c):
    if "Так" not in u.message.text:
        await u.message.reply_text("Заявку скасовано.")
        return ConversationHandler.END

    uid = u.from_user.id
    mark_request(uid)
    lead_id = f"RENT-{uid}-{int(datetime.now().timestamp())}"

    await c.bot.send_message(
        ADMIN_GROUP_ID,
        f"🏠 ОРЕНДА\n{c.user_data}\n@{u.from_user.username}",
        reply_markup=status_keyboard(lead_id)
    )

    await u.message.reply_text(
        "✅ Запит прийнято!\n"
        "Маклер звʼяжеться з вами протягом 24–48 годин.\n\n"
        "👉 Група з пропозиціями:\nhttps://t.me/+IhcJixOP1_QyNjM0"
    )
    return ConversationHandler.END

# ================== BUY FLOW ==================
async def buy_type(u,c): c.user_data["type"]=u.message.text; await u.message.reply_text("2️⃣ Опишіть очікування"); return BUY_DETAILS
async def buy_details(u,c): c.user_data["details"]=u.message.text; await u.message.reply_text("3️⃣ Де купівля?"); return BUY_CITY
async def buy_city(u,c): c.user_data["city"]=u.message.text; await u.message.reply_text("4️⃣ Бюджет?"); return BUY_PRICE
async def buy_price(u,c): c.user_data["price"]=u.message.text; await u.message.reply_text("5️⃣ Фінансування?"); return BUY_FINANCE
async def buy_finance(u,c): c.user_data["finance"]=u.message.text; await u.message.reply_text("6️⃣ Коли купівля?"); return BUY_TIME
async def buy_time(u,c): c.user_data["time"]=u.message.text; await u.message.reply_text("7️⃣ Формат оглядів?"); return BUY_VIEW

async def buy_view(u,c):
    c.user_data["view"]=u.message.text
    kb = ReplyKeyboardMarkup([[KeyboardButton("📞 Поділитись контактом", request_contact=True)]], resize_keyboard=True)
    await u.message.reply_text("8️⃣ Контакт:", reply_markup=kb)
    return BUY_CONTACT

async def buy_contact(u,c):
    c.user_data["phone"]=u.message.contact.phone_number if u.message.contact else u.message.text
    await u.message.reply_text("9️⃣ Як до вас звертатись?")
    return BUY_NAME

async def buy_name(u,c):
    c.user_data["name"]=u.message.text
    await u.message.reply_text(f"📋 Перевірте дані:\n{c.user_data}\n\nВсе вірно? (Так/Ні)")
    return BUY_CONFIRM

async def buy_confirm(u,c):
    if "Так" not in u.message.text:
        return ConversationHandler.END

    uid = u.from_user.id
    mark_request(uid)
    lead_id = f"BUY-{uid}-{int(datetime.now().timestamp())}"

    await c.bot.send_message(
        ADMIN_GROUP_ID,
        f"🏡 КУПІВЛЯ\n{c.user_data}\n@{u.from_user.username}",
        reply_markup=status_keyboard(lead_id)
    )

    await u.message.reply_text(
        "✅ Запит прийнято!\n"
        "Ми звʼяжемось з вами протягом 24–48 годин.\n\n"
        "👉 https://t.me/+IhcJixOP1_QyNjM0"
    )
    return ConversationHandler.END

# ================== STATUS ==================
async def status_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Статус оновлено")

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_FLOW: [MessageHandler(filters.TEXT, choose_flow)],

            RENT_TYPE: [MessageHandler(filters.TEXT, rent_type)],
            RENT_CITY: [MessageHandler(filters.TEXT, rent_city)],
            RENT_DISTRICT: [MessageHandler(filters.TEXT, rent_district)],
            RENT_FOR_WHOM: [MessageHandler(filters.TEXT, rent_for_whom)],
            RENT_JOB: [MessageHandler(filters.TEXT, rent_job)],
            RENT_CHILDREN: [MessageHandler(filters.TEXT, rent_children)],
            RENT_PETS: [MessageHandler(filters.TEXT, rent_pets)],
            RENT_PARKING: [MessageHandler(filters.TEXT, rent_parking)],
            RENT_MOVEIN: [MessageHandler(filters.TEXT, rent_movein)],
            RENT_BUDGET: [MessageHandler(filters.TEXT, rent_budget)],
            RENT_VIEWTIME: [MessageHandler(filters.TEXT, rent_viewtime)],
            RENT_LOCATION: [MessageHandler(filters.TEXT, rent_location)],
            RENT_VIEWFORMAT: [MessageHandler(filters.TEXT, rent_viewformat)],
            RENT_CONTACT: [MessageHandler(filters.ALL, rent_contact)],
            RENT_NAME: [MessageHandler(filters.TEXT, rent_name)],
            RENT_CONFIRM: [MessageHandler(filters.TEXT, rent_confirm)],

            BUY_TYPE: [MessageHandler(filters.TEXT, buy_type)],
            BUY_DETAILS: [MessageHandler(filters.TEXT, buy_details)],
            BUY_CITY: [MessageHandler(filters.TEXT, buy_city)],
            BUY_PRICE: [MessageHandler(filters.TEXT, buy_price)],
            BUY_FINANCE: [MessageHandler(filters.TEXT, buy_finance)],
            BUY_TIME: [MessageHandler(filters.TEXT, buy_time)],
            BUY_VIEW: [MessageHandler(filters.TEXT, buy_view)],
            BUY_CONTACT: [MessageHandler(filters.ALL, buy_contact)],
            BUY_NAME: [MessageHandler(filters.TEXT, buy_name)],
            BUY_CONFIRM: [MessageHandler(filters.TEXT, buy_confirm)],
        },
        fallbacks=[]
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(status_cb, pattern="^status\\|"))
    app.run_polling()

if __name__ == "__main__":
    main()
