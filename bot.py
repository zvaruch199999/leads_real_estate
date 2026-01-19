import os
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID")

if not BOT_TOKEN or not ADMIN_GROUP_ID:
    raise RuntimeError("BOT_TOKEN або ADMIN_GROUP_ID не задані")

ADMIN_GROUP_ID = int(ADMIN_GROUP_ID)

users = {}
request_counter = 0


def status_keyboard(req_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟡 В пошуках", callback_data=f"status:search:{req_id}"),
            InlineKeyboardButton("🟢 Мають резервацію", callback_data=f"status:reserve:{req_id}")
        ],
        [
            InlineKeyboardButton("🔵 Самі знайшли", callback_data=f"status:self:{req_id}"),
            InlineKeyboardButton("🟠 Чужий маклер", callback_data=f"status:other:{req_id}")
        ],
        [
            InlineKeyboardButton("⚫ Не шукають", callback_data=f"status:stop:{req_id}"),
            InlineKeyboardButton("🔴 Закрили угоду", callback_data=f"status:closed:{req_id}")
        ]
    ])


def build_summary(u, status="🟡 В пошуках"):
    return (
        f"📋 Запит №{u['req_id']}\n"
        f"📌 Статус: {status}\n\n"
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


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id] = {"step": "deal"}
    kb = [
        [InlineKeyboardButton("🏠 Оренда", callback_data="deal:rent")],
        [InlineKeyboardButton("🏡 Купівля", callback_data="deal:buy")]
    ]
    await update.message.reply_text("👋 Що вас цікавить?", reply_markup=InlineKeyboardMarkup(kb))


async def deal_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["deal"] = "Оренда" if "rent" in q.data else "Купівля"
    u["step"] = "property"

    kb = [
        [InlineKeyboardButton("🛏 Ліжко-місце", callback_data="prop:Ліжко-місце")],
        [InlineKeyboardButton("🏢 Студія", callback_data="prop:Студія")],
        [InlineKeyboardButton("1️⃣ 1-кімнатна", callback_data="prop:1-кімнатна")],
        [InlineKeyboardButton("2️⃣ 2-кімнатна", callback_data="prop:2-кімнатна")],
        [InlineKeyboardButton("3️⃣ 3-кімнатна", callback_data="prop:3-кімнатна")],
        [InlineKeyboardButton("✍️ Свій варіант", callback_data="prop:custom")]
    ]
    await q.message.reply_text("🏡 Тип житла:", reply_markup=InlineKeyboardMarkup(kb))


async def property_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if "custom" in q.data:
        u["step"] = "property_custom"
        await q.message.reply_text("✍️ Напишіть тип житла:")
    else:
        u["property"] = q.data.split(":")[1]
        u["step"] = "city"
        await q.message.reply_text("📍 В якому місті шукаєте житло?")


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
        await update.message.reply_text("👥 Для кого житло?")

    elif step == "for_whom":
        u["for_whom"] = t
        u["step"] = "job"
        await update.message.reply_text("💼 Чим займаєтесь?")

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
            [InlineKeyboardButton("Так", callback_data="park:yes")],
            [InlineKeyboardButton("Ні", callback_data="park:no")],
            [InlineKeyboardButton("Пізніше", callback_data="park:later")]
        ]
        await update.message.reply_text("🚗 Паркування?", reply_markup=InlineKeyboardMarkup(kb))

    elif step == "move_in":
        u["move_in"] = t
        u["step"] = "view_time"
        await update.message.reply_text("⏰ Коли доступні для оглядів?")

    elif step == "view_time":
        u["view_time"] = t
        u["step"] = "wishes"
        await update.message.reply_text("✨ Напишіть особливі побажання:")

    elif step == "wishes":
        u["wishes"] = t
        u["step"] = "budget"
        await update.message.reply_text("💶 Який бюджет на оренду в місяць (від–до €)?")

    elif step == "budget":
        u["budget"] = t
        u["step"] = "location"
        kb = [
            [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc:ua")],
            [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc:sk")],
            [InlineKeyboardButton("✍️ Інша країна", callback_data="loc:custom")]
        ]
        await update.message.reply_text("🌍 Де ви зараз?", reply_markup=InlineKeyboardMarkup(kb))

    elif step == "custom_location":
        u["location"] = t
        await ask_view_format(update.message, u)

    elif step == "name":
        global request_counter
        request_counter += 1
        u["name"] = t
        u["req_id"] = request_counter
        u["username"] = update.effective_user.username or "немає"
        await show_terms(update.message, u)


async def park_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["parking"] = q.data.split(":")[1]
    u["step"] = "move_in"
    await q.message.reply_text("📅 Коли плануєте заїзд?")


async def location_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if "custom" in q.data:
        u["step"] = "custom_location"
        await q.message.reply_text("✍️ Напишіть країну:")
    else:
        u["location"] = "Україна" if "ua" in q.data else "Словаччина"
        await ask_view_format(q.message, u)


async def ask_view_format(msg, u):
    u["step"] = "view_format"
    kb = [
        [InlineKeyboardButton("💻 Онлайн", callback_data="view:online")],
        [InlineKeyboardButton("🚶 Фізичний", callback_data="view:offline")],
        [InlineKeyboardButton("🔁 Обидва варіанти", callback_data="view:both")]
    ]
    await msg.reply_text("👀 Який формат огляду?", reply_markup=InlineKeyboardMarkup(kb))


async def view_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["view_format"] = q.data.split(":")[1]
    u["step"] = "contact"

    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Поділитись контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await q.message.reply_text("📞 Поділіться контактом для пошуку житла:", reply_markup=kb)


async def contact_handler(update: Update, ctx):
    u = users[update.effective_user.id]
    u["phone"] = update.message.contact.phone_number
    u["step"] = "name"
    await update.message.reply_text("👤 Як до вас можемо звертатись?")


async def show_terms(msg, u):
    kb = [
        [InlineKeyboardButton("✅ Так", callback_data="terms:yes")],
        [InlineKeyboardButton("❌ Ні", callback_data="terms:no")]
    ]
    await msg.reply_text(
        "ℹ️ Умови співпраці:\n"
        "• депозит може дорівнювати орендній платі\n"
        "• оплачується повна або часткова комісія ріелтору\n"
        "• можливий подвійний депозит при дітях або тваринах\n\n"
        "Чи погоджуєтесь?",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def terms_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if "yes" in q.data:
        msg = await ctx.bot.send_message(
            ADMIN_GROUP_ID,
            build_summary(u),
            reply_markup=status_keyboard(u["req_id"])
        )

        u["group_message_id"] = msg.message_id

        await q.message.reply_text(
            "✅ Запит відправлено маклеру.\n"
            "Маклер звʼяжеться з вами протягом 24–48 годин.\n\n"
            "🔗 Долучайтесь до нашої групи з пропозиціями:\n"
            "https://t.me/+IhcJixOP1_QyNjM0"
        )

    users.pop(q.from_user.id, None)


async def status_handler(update: Update, ctx):
    q = update.callback_query
    await q.answer()

    _, status, req_id = q.data.split(":")
    status_map = {
        "search": "🟡 В пошуках",
        "reserve": "🟢 Мають резервацію",
        "self": "🔵 Самі знайшли",
        "other": "🟠 Чужий маклер",
        "stop": "⚫ Не шукають",
        "closed": "🔴 Закрили угоду"
    }

    text = q.message.text.split("\n")
    text[1] = f"📌 Статус: {status_map[status]}"
    await q.message.edit_text("\n".join(text), reply_markup=status_keyboard(req_id))


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(deal_handler, pattern="^deal"))
    app.add_handler(CallbackQueryHandler(property_handler, pattern="^prop"))
    app.add_handler(CallbackQueryHandler(park_handler, pattern="^park"))
    app.add_handler(CallbackQueryHandler(location_handler, pattern="^loc"))
    app.add_handler(CallbackQueryHandler(view_handler, pattern="^view"))
    app.add_handler(CallbackQueryHandler(terms_handler, pattern="^terms"))
    app.add_handler(CallbackQueryHandler(status_handler, pattern="^status"))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
