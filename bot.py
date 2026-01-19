import os
import sqlite3
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== CONFIG (ENV) ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID_RAW = os.getenv("ADMIN_GROUP_ID")
if not BOT_TOKEN or not ADMIN_GROUP_ID_RAW:
    raise RuntimeError("BOT_TOKEN або ADMIN_GROUP_ID не задані")
ADMIN_GROUP_ID = int(ADMIN_GROUP_ID_RAW)

# ================== DB ==================
conn = sqlite3.connect("requests.db", check_same_thread=False)
cur = conn.cursor()

# Таблиця заявок (для статистики та статусів)
cur.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    date TEXT NOT NULL,
    housing_type TEXT NOT NULL,
    status TEXT NOT NULL
)
""")

# Мапа message_id (в групі) -> request_id (щоб апдейтити статус по кнопках)
cur.execute("""
CREATE TABLE IF NOT EXISTS message_map (
    group_chat_id INTEGER NOT NULL,
    group_message_id INTEGER NOT NULL,
    request_id INTEGER NOT NULL,
    PRIMARY KEY (group_chat_id, group_message_id)
)
""")

conn.commit()

# ================== STATE ==================
users = {}

# ================== TEXT MAPS ==================
PARKING_MAP = {"park_yes": "Так", "park_no": "Ні", "park_later": "Пізніше"}
VIEW_MAP = {"view_online": "Онлайн", "view_offline": "Фізичний", "view_both": "Обидва варіанти"}
LOCATION_MAP = {"loc_ua": "Україна", "loc_sk": "Словаччина"}

# Статуси (з кнопок)
STATUS_KEY_TO_LABEL = {
    "search": "🟡 В пошуках",
    "reserve": "🟢 Мають резервацію",
    "self": "🔵 Самі знайшли",
    "other": "🟠 Знайшов чужий маклер",
    "stop": "⚫ Не шукають вже",
    "closed": "🔴 Закрили угоду",
}

# Для БД зберігаємо саме текст (людський), щоб статистика була читабельна
DEFAULT_STATUS = STATUS_KEY_TO_LABEL["search"]


def build_group_text(u: dict, req_id: int, status_label: str) -> str:
    tg = f"@{u.get('username')}" if u.get("username") else "—"
    return (
        f"📋 Запит №{req_id}\n"
        f"📌 Статус: {status_label}\n\n"
        f"👤 Імʼя: {u.get('name','—')}\n"
        f"🆔 Telegram: {tg}\n"
        f"📞 Телефон: {u.get('phone','—')}\n\n"
        f"🏠 Тип угоди: {u.get('deal','—')}\n"
        f"🏡 Житло: {u.get('property','—')}\n"
        f"📍 Місто: {u.get('city','—')} / {u.get('district','—')}\n"
        f"👥 Для кого: {u.get('for_whom','—')}\n"
        f"💼 Діяльність: {u.get('job','—')}\n"
        f"🧒 Діти: {u.get('children','—')}\n"
        f"🐾 Тваринки: {u.get('pets','—')}\n"
        f"🚗 Паркування: {u.get('parking','—')}\n"
        f"📅 Заїзд: {u.get('move_in','—')}\n"
        f"💶 Бюджет оренда: {u.get('budget','—')}\n"
        f"⏰ Огляди: {u.get('view_time','—')}\n"
        f"✨ Побажання: {u.get('wishes','—')}\n"
        f"🌍 Зараз в: {u.get('location','—')}\n"
        f"👀 Формат огляду: {u.get('view_format','—')}"
    )


def build_user_summary(u: dict, req_id: int) -> str:
    return (
        f"📋 **Перевірте дані (Запит №{req_id})**\n\n"
        f"🏠 Тип угоди: {u.get('deal','—')}\n"
        f"🏡 Житло: {u.get('property','—')}\n"
        f"📍 Місто: {u.get('city','—')} / {u.get('district','—')}\n"
        f"👥 Для кого: {u.get('for_whom','—')}\n"
        f"💼 Діяльність: {u.get('job','—')}\n"
        f"🧒 Діти: {u.get('children','—')}\n"
        f"🐾 Тваринки: {u.get('pets','—')}\n"
        f"🚗 Паркування: {u.get('parking','—')}\n"
        f"📅 Заїзд: {u.get('move_in','—')}\n"
        f"💶 Бюджет оренда: {u.get('budget','—')}\n"
        f"⏰ Огляди: {u.get('view_time','—')}\n"
        f"✨ Побажання: {u.get('wishes','—')}\n"
        f"🌍 Зараз в: {u.get('location','—')}\n"
        f"👀 Формат огляду: {u.get('view_format','—')}\n"
        f"📞 Телефон: {u.get('phone','—')}\n"
        f"👤 Імʼя: {u.get('name','—')}"
    )


def status_keyboard(req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟡 В пошуках", callback_data=f"status:search:{req_id}"),
            InlineKeyboardButton("🟢 Резервація", callback_data=f"status:reserve:{req_id}"),
        ],
        [
            InlineKeyboardButton("🔵 Самі знайшли", callback_data=f"status:self:{req_id}"),
            InlineKeyboardButton("🟠 Чужий маклер", callback_data=f"status:other:{req_id}"),
        ],
        [
            InlineKeyboardButton("⚫ Не шукають", callback_data=f"status:stop:{req_id}"),
            InlineKeyboardButton("🔴 Закрили угоду", callback_data=f"status:closed:{req_id}"),
        ],
    ])


# ================== START/RESET ==================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id] = {"step": "deal", "username": update.effective_user.username or ""}
    kb = [
        [InlineKeyboardButton("🏠 Оренда", callback_data="deal_rent")],
        [InlineKeyboardButton("🏡 Купівля", callback_data="deal_buy")],
    ]
    await update.message.reply_text("👋 Вітаємо! Що вас цікавить?", reply_markup=InlineKeyboardMarkup(kb))


async def reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users.pop(update.effective_user.id, None)
    await update.message.reply_text("🔄 Анкету скинуто. Натисніть /start щоб почати знову.")


# ================== FLOW: CALLBACKS ==================
async def deal_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = users.setdefault(q.from_user.id, {"username": q.from_user.username or ""})
    u["deal"] = "Оренда" if q.data == "deal_rent" else "Купівля"
    u["step"] = "property"

    kb = [
        [InlineKeyboardButton("🛏 Ліжко-місце", callback_data="prop_Ліжко-місце")],
        [InlineKeyboardButton("🛋 Кімната", callback_data="prop_Кімната")],
        [InlineKeyboardButton("🏢 Студія", callback_data="prop_Студія")],
        [InlineKeyboardButton("1️⃣ 1-кімнатна", callback_data="prop_1-кімнатна")],
        [InlineKeyboardButton("2️⃣ 2-кімнатна", callback_data="prop_2-кімнатна")],
        [InlineKeyboardButton("3️⃣ 3-кімнатна", callback_data="prop_3-кімнатна")],
        [InlineKeyboardButton("4️⃣ 4-кімнатна", callback_data="prop_4-кімнатна")],
        [InlineKeyboardButton("5️⃣ 5-кімнатна", callback_data="prop_5-кімнатна")],
        [InlineKeyboardButton("🏠 Будинок", callback_data="prop_Будинок")],
        [InlineKeyboardButton("✍️ Свій варіант", callback_data="prop_custom")],
    ]
    await q.message.reply_text("🏡 Оберіть тип житла:", reply_markup=InlineKeyboardMarkup(kb))


async def property_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]

    if q.data == "prop_custom":
        u["step"] = "property_text"
        await q.message.reply_text("✍️ Напишіть тип житла вручну:")
    else:
        u["property"] = q.data.replace("prop_", "")
        u["step"] = "city"
        await q.message.reply_text("🏙️ В якому місті шукаєте житло?")


async def parking_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["parking"] = PARKING_MAP[q.data]
    u["step"] = "move_in"
    await q.message.reply_text("📅 Яка найкраща дата для заїзду?")


async def location_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
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
        [InlineKeyboardButton("🔁 Обидва", callback_data="view_both")],
    ]
    await msg.reply_text("👀 Який формат огляду вам підходить?", reply_markup=InlineKeyboardMarkup(kb))


async def view_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = users[q.from_user.id]
    u["view_format"] = VIEW_MAP[q.data]
    u["step"] = "contact"

    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Поділитись контактом для пошуку житла", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await q.message.reply_text("📞 Поділіться контактом для звʼязку:", reply_markup=kb)


async def confirm_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
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
        await q.message.reply_text("❌ Запит скасовано. Натисніть /start щоб почати заново.")


async def terms_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = users.get(uid)

    if not u:
        return

    if q.data == "terms_no":
        users.pop(uid, None)
        await ctx.bot.send_message(chat_id=uid, text="❌ Добре. Якщо передумаєте — натисніть /start.")
        return

    # terms_yes: створюємо запис у БД
    created_at = datetime.now().isoformat(timespec="seconds")
    date_str = datetime.now().strftime("%Y-%m-%d")
    housing_type = u.get("property", "—")
    status_label = DEFAULT_STATUS

    cur.execute(
        "INSERT INTO requests (created_at, date, housing_type, status) VALUES (?, ?, ?, ?)",
        (created_at, date_str, housing_type, status_label),
    )
    conn.commit()
    req_id = cur.lastrowid

    # надсилаємо в групу
    group_text = build_group_text(u, req_id, status_label)
    sent = await ctx.bot.send_message(
        chat_id=ADMIN_GROUP_ID,
        text=group_text,
        reply_markup=status_keyboard(req_id),
    )

    # прив'язка повідомлення до req_id (для надійності)
    cur.execute(
        "INSERT OR REPLACE INTO message_map (group_chat_id, group_message_id, request_id) VALUES (?, ?, ?)",
        (sent.chat_id, sent.message_id, req_id),
    )
    conn.commit()

    # фінал клієнту (завжди через send_message, щоб не губилось)
    await ctx.bot.send_message(
        chat_id=uid,
        text=(
            "✅ **Запит успішно відправлено маклеру!**\n\n"
            "📞 Маклер звʼяжеться з вами протягом **24–48 годин**.\n\n"
            "🏘 Долучайтесь до нашої групи з актуальними пропозиціями житла в Братиславі:\n"
            "👉 https://t.me/+IhcJixOP1_QyNjM0"
        ),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )

    users.pop(uid, None)


# ================== STATUS UPDATE (GROUP BUTTONS) ==================
async def status_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    # callback_data: status:<key>:<req_id>
    try:
        _, key, req_id_str = q.data.split(":")
        req_id = int(req_id_str)
    except Exception:
        return

    new_status = STATUS_KEY_TO_LABEL.get(key)
    if not new_status:
        return

    # Оновлюємо БД
    cur.execute("UPDATE requests SET status=? WHERE id=?", (new_status, req_id))
    conn.commit()

    # Оновлюємо текст повідомлення в групі
    lines = (q.message.text or "").split("\n")
    for i, line in enumerate(lines):
        if line.startswith("📌 Статус:"):
            lines[i] = f"📌 Статус: {new_status}"
            break

    await q.message.edit_text("\n".join(lines), reply_markup=status_keyboard(req_id))


# ================== FLOW: TEXT INPUTS ==================
async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in users:
        return
    u = users[uid]
    t = update.message.text.strip()

    step = u.get("step")

    if step == "property_text":
        u["property"] = t
        u["step"] = "city"
        await update.message.reply_text("🏙️ В якому місті шукаєте житло?")

    elif step == "city":
        u["city"] = t
        u["step"] = "district"
        await update.message.reply_text("🗺️ Який район вас цікавить?")

    elif step == "district":
        u["district"] = t
        u["step"] = "for_whom"
        await update.message.reply_text("👥 Для кого шукаєте житло? (розпишіть детальніше)")

    elif step == "for_whom":
        u["for_whom"] = t
        u["step"] = "job"
        await update.message.reply_text("💼 Чим ви займаєтесь? (діяльність)")

    elif step == "job":
        u["job"] = t
        u["step"] = "children"
        await update.message.reply_text("🧒 Чи маєте дітей? Якщо так — вік та хлопчик/дівчинка. Якщо ні — «Ні».")

    elif step == "children":
        u["children"] = t
        u["step"] = "pets"
        await update.message.reply_text("🐾 Чи маєте тваринок? Якщо так — яка і коротко про неї. Якщо ні — «Ні».")

    elif step == "pets":
        u["pets"] = t
        u["step"] = "parking"
        kb = [
            [InlineKeyboardButton("✅ Так", callback_data="park_yes")],
            [InlineKeyboardButton("❌ Ні", callback_data="park_no")],
            [InlineKeyboardButton("⏳ Пізніше", callback_data="park_later")],
        ]
        await update.message.reply_text("🚗 Чи потрібне паркування?", reply_markup=InlineKeyboardMarkup(kb))

    elif step == "move_in":
        u["move_in"] = t
        u["step"] = "budget"
        await update.message.reply_text("💶 Який бюджет на оренду в місяць (від–до €)?")

    elif step == "budget":
        u["budget"] = t
        u["step"] = "view_time"
        await update.message.reply_text("⏰ Як зазвичай ви доступні для оглядів? (дні/час)")

    elif step == "view_time":
        u["view_time"] = t
        u["step"] = "wishes"
        await update.message.reply_text("✨ Напишіть особливі побажання на житло:")

    elif step == "wishes":
        u["wishes"] = t
        u["step"] = "location"
        kb = [
            [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc_ua")],
            [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc_sk")],
            [InlineKeyboardButton("🏳️ Інша країна", callback_data="loc_custom")],
        ]
        await update.message.reply_text("🌍 Де ви зараз знаходитесь?", reply_markup=InlineKeyboardMarkup(kb))

    elif step == "custom_location":
        u["location"] = t
        u["step"] = "view_format"
        await ask_view_format(update.message)

    elif step == "name":
        u["name"] = t
        # показуємо підсумок і підтвердження
        kb = [
            [InlineKeyboardButton("✅ Так, вірно", callback_data="confirm_yes")],
            [InlineKeyboardButton("❌ Ні, скасувати", callback_data="confirm_no")],
        ]
        # тимчасово req_id = 0 (для показу)
        await update.message.reply_text(
            build_user_summary(u, 0),
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )

    else:
        await update.message.reply_text("⚠️ Натисніть /start щоб почати анкету.")


# ================== CONTACT ==================
async def contact_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in users:
        return
    u = users[uid]
    u["phone"] = update.message.contact.phone_number
    u["step"] = "name"
    await update.message.reply_text("👤 Напишіть, будь ласка, як до вас можемо звертатись (імʼя/прізвище):")


# ================== STATS ==================
def format_stats(rows):
    """
    rows: [(status, housing_type, count)]
    """
    if not rows:
        return "Немає даних за цей період"

    grouped = {}
    for status, housing_type, count in rows:
        grouped.setdefault(status, {})
        grouped[status][housing_type] = count

    text = ""
    for status, housing_map in grouped.items():
        text += f"\n{status}:\n"
        for housing_type, count in housing_map.items():
            text += f" • {housing_type}: {count}\n"
    return text


async def stats_period(update: Update, days: int, title: str):
    if days == 1:
        date_from = datetime.now().strftime("%Y-%m-%d")
        cur.execute("""
            SELECT status, housing_type, COUNT(*)
            FROM requests
            WHERE date = ?
            GROUP BY status, housing_type
        """, (date_from,))
    else:
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        cur.execute("""
            SELECT status, housing_type, COUNT(*)
            FROM requests
            WHERE date >= ?
            GROUP BY status, housing_type
        """, (date_from,))

    rows = cur.fetchall()
    await update.message.reply_text(f"{title}\n{format_stats(rows)}")


async def stats_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await stats_period(update, 1, "📊 Статистика за сьогодні:")


async def stats_week(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await stats_period(update, 7, "📊 Статистика за 7 днів:")


async def stats_month(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await stats_period(update, 30, "📊 Статистика за 30 днів:")


# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("stats_today", stats_today))
    app.add_handler(CommandHandler("stats_week", stats_week))
    app.add_handler(CommandHandler("stats_month", stats_month))

    # callbacks
    app.add_handler(CallbackQueryHandler(status_handler, pattern="^status:"))
    app.add_handler(CallbackQueryHandler(deal_handler, pattern="^deal_"))
    app.add_handler(CallbackQueryHandler(property_handler, pattern="^prop_"))
    app.add_handler(CallbackQueryHandler(parking_handler, pattern="^park_"))
    app.add_handler(CallbackQueryHandler(location_handler, pattern="^loc_"))
    app.add_handler(CallbackQueryHandler(view_handler, pattern="^view_"))
    app.add_handler(CallbackQueryHandler(confirm_handler, pattern="^confirm_"))
    app.add_handler(CallbackQueryHandler(terms_handler, pattern="^terms_"))

    # messages
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
