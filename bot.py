import os
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID")

if not BOT_TOKEN or not ADMIN_GROUP_ID:
    raise RuntimeError("BOT_TOKEN або ADMIN_GROUP_ID не задані")

ADMIN_GROUP_ID = int(ADMIN_GROUP_ID)

# ================== STORAGE ==================
users = {}
requests_log = []

# ================== HELPERS ==================
def now():
    return datetime.utcnow()

def summary(u, req_id, status="🟡 В пошуках"):
    return (
        f"📋 **Запит №{req_id}**\n"
        f"📌 Статус: {status}\n\n"
        f"👤 Імʼя: {u['name']}\n"
        f"🆔 Telegram: @{u['username']}\n"
        f"📞 Телефон: {u['phone']}\n\n"
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

def status_keyboard(req_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟡 В пошуках", callback_data=f"status_search_{req_id}"),
            InlineKeyboardButton("🟢 Мають резервацію", callback_data=f"status_reserve_{req_id}")
        ],
        [
            InlineKeyboardButton("🔵 Самі знайшли", callback_data=f"status_self_{req_id}"),
            InlineKeyboardButton("🟠 Чужий маклер", callback_data=f"status_other_{req_id}")
        ],
        [
            InlineKeyboardButton("⚫ Не шукають", callback_data=f"status_stop_{req_id}"),
            InlineKeyboardButton("🔴 Закрили угоду", callback_data=f"status_close_{req_id}")
        ]
    ])

# ================== START ==================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id] = {
        "step": "deal",
        "username": update.effective_user.username or "немає"
    }
    await update.message.reply_text(
        "👋 Що вас цікавить?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Оренда", callback_data="deal_rent")],
            [InlineKeyboardButton("🏡 Купівля", callback_data="deal_buy")]
        ])
    )

# ================== CALLBACK HANDLER ==================
async def callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = users.get(uid)

    if not u:
        return

    data = q.data

    # DEAL
    if data.startswith("deal_"):
        u["deal"] = "Оренда" if data == "deal_rent" else "Купівля"
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

    elif data.startswith("prop_"):
        if data == "prop_custom":
            u["step"] = "property_custom"
            await q.message.reply_text("✍️ Напишіть тип житла:")
        else:
            u["property"] = data.replace("prop_", "")
            u["step"] = "city"
            await q.message.reply_text("📍 В якому місті шукаєте житло?")

    elif data.startswith("loc_"):
        if data == "loc_other":
            u["step"] = "location_custom"
            await q.message.reply_text("✍️ Напишіть країну:")
        else:
            u["location"] = "Україна" if data == "loc_ua" else "Словаччина"
            u["step"] = "view_format"
            await q.message.reply_text(
                "👀 Який формат огляду?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💻 Онлайн", callback_data="view_online")],
                    [InlineKeyboardButton("🚶 Фізичний", callback_data="view_offline")],
                    [InlineKeyboardButton("🔁 Обидва", callback_data="view_both")]
                ])
            )

    elif data.startswith("view_"):
        u["view_format"] = {
            "view_online": "Онлайн",
            "view_offline": "Фізичний",
            "view_both": "Обидва"
        }[data]
        u["step"] = "contact"
        await q.message.reply_text(
            "📞 Поділіться контактом для пошуку житла:",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📞 Поділитись контактом", request_contact=True)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )

    elif data.startswith("confirm_"):
        if data == "confirm_yes":
            await q.message.reply_text(
                "ℹ️ **Умови співпраці:**\n"
                "• депозит може дорівнювати орендній платі\n"
                "• оплачується повна або часткова комісія ріелтору\n"
                "• можливий подвійний депозит при дітях або тваринках\n\n"
                "Чи погоджуєтесь?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Так", callback_data="terms_yes")],
                    [InlineKeyboardButton("❌ Ні", callback_data="terms_no")]
                ])
            )
        else:
            users.pop(uid, None)
            await q.message.reply_text("❌ Запит скасовано.")

    elif data.startswith("terms_"):
        if data == "terms_yes":
            req_id = len(requests_log) + 1
            msg = summary(u, req_id)
            sent = await ctx.bot.send_message(
                ADMIN_GROUP_ID,
                msg,
                parse_mode="Markdown",
                reply_markup=status_keyboard(req_id)
            )
            requests_log.append({
                "id": req_id,
                "date": now(),
                "property": u["property"]
            })

            await ctx.bot.send_message(
                chat_id=uid,
                text=(
                    "✅ **Запит успішно відправлено маклеру!**\n\n"
                    "📞 Маклер звʼяжеться з вами протягом **24–48 годин**.\n\n"
                    "🏘 Долучайтесь до нашої групи з актуальними пропозиціями житла в Братиславі:\n"
                    "👉 https://t.me/+IhcJixOP1_QyNjM0"
                ),
                parse_mode="Markdown"
            )
        users.pop(uid, None)

    # STATUS UPDATE
    elif data.startswith("status_"):
        parts = data.split("_")
        status_map = {
            "search": "🟡 В пошуках",
            "reserve": "🟢 Мають резервацію",
            "self": "🔵 Самі знайшли",
            "other": "🟠 Чужий маклер",
            "stop": "⚫ Не шукають",
            "close": "🔴 Закрили угоду"
        }
        status = status_map.get(parts[1])
        req_id = parts[2]
        await q.message.edit_text(
            q.message.text.split("\n📌")[0] + f"\n📌 Статус: {status}",
            parse_mode="Markdown",
            reply_markup=status_keyboard(req_id)
        )

# ================== TEXT HANDLER ==================
async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in users:
        return
    u = users[uid]
    text = update.message.text

    step = u["step"]

    if step == "property_custom":
        u["property"] = text
        u["step"] = "city"
        await update.message.reply_text("📍 В якому місті шукаєте житло?")

    elif step == "city":
        u["city"] = text
        u["step"] = "for_whom"
        await update.message.reply_text("👥 Для кого шукаєте житло?")

    elif step == "for_whom":
        u["for_whom"] = text
        u["step"] = "job"
        await update.message.reply_text("💼 Чим ви займаєтесь?")

    elif step == "job":
        u["job"] = text
        u["step"] = "children"
        await update.message.reply_text("🧒 Чи є діти?")

    elif step == "children":
        u["children"] = text
        u["step"] = "pets"
        await update.message.reply_text("🐾 Чи є тваринки?")

    elif step == "pets":
        u["pets"] = text
        u["step"] = "parking"
        await update.message.reply_text(
            "🚗 Паркування?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Так", callback_data="park_yes")],
                [InlineKeyboardButton("Ні", callback_data="park_no")],
                [InlineKeyboardButton("Пізніше", callback_data="park_later")]
            ])
        )

    elif step == "move_in":
        u["move_in"] = text
        u["step"] = "view_time"
        await update.message.reply_text("⏰ Коли ви доступні для оглядів?")

    elif step == "view_time":
        u["view_time"] = text
        u["step"] = "wishes"
        await update.message.reply_text("✨ Напишіть особливі побажання до житла")

    elif step == "wishes":
        u["wishes"] = text
        u["step"] = "budget"
        await update.message.reply_text("💶 Який бюджет на оренду в місяць (від–до €)?")

    elif step == "budget":
        u["budget"] = text
        u["step"] = "location"
        await update.message.reply_text(
            "🌍 Де ви зараз?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc_ua")],
                [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc_sk")],
                [InlineKeyboardButton("✍️ Інша країна", callback_data="loc_other")]
            ])
        )

    elif step == "location_custom":
        u["location"] = text
        u["step"] = "view_format"
        await update.message.reply_text(
            "👀 Який формат огляду?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💻 Онлайн", callback_data="view_online")],
                [InlineKeyboardButton("🚶 Фізичний", callback_data="view_offline")],
                [InlineKeyboardButton("🔁 Обидва", callback_data="view_both")]
            ])
        )

    elif step == "name":
        u["name"] = text
        await update.message.reply_text(
            summary(u, "—"),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Так", callback_data="confirm_yes")],
                [InlineKeyboardButton("❌ Ні", callback_data="confirm_no")]
            ])
        )

# ================== CONTACT ==================
async def contact_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = users[uid]
    u["phone"] = update.message.contact.phone_number
    u["step"] = "name"
    await update.message.reply_text("👤 Як до вас можемо звертатись?")

# ================== PARKING ==================
async def parking_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["parking"] = {
        "park_yes": "Так",
        "park_no": "Ні",
        "park_later": "Пізніше"
    }[q.data]
    u["step"] = "move_in"
    await q.message.reply_text("📅 Яка найкраща дата для заїзду?")

# ================== STATS ==================
async def stats_today(update: Update, ctx):
    today = now().date()
    count = sum(1 for r in requests_log if r["date"].date() == today)
    await update.message.reply_text(f"📊 Сьогодні: {count} запитів")

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats_today", stats_today))

    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(CallbackQueryHandler(parking_handler, pattern="^park_"))

    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
