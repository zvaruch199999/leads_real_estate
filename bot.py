# bot.py
# python-telegram-bot v20+
# ENV:
#   BOT_TOKEN        = токен бота
#   ADMIN_GROUP_ID   = id вашої групи для заявок (наприклад -100xxxxxxxxxx)

import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
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

# ========= CONFIG =========
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0").strip() or "0")
GROUP_LINK = "https://t.me/+IhcJixOP1_QyNjM0"

if not BOT_TOKEN or ADMIN_GROUP_ID == 0:
    raise RuntimeError("BOT_TOKEN або ADMIN_GROUP_ID не задані")

# ========= DB =========
DB_PATH = "real_estate.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()

cur.execute(
    """
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    tg_username TEXT,
    tg_fullname TEXT,
    created_at TEXT,
    status TEXT,
    deal TEXT,
    property TEXT
)
"""
)
cur.execute(
    """
CREATE TABLE IF NOT EXISTS request_group_messages (
    req_id INTEGER,
    chat_id INTEGER,
    message_id INTEGER,
    PRIMARY KEY (req_id, chat_id)
)
"""
)
conn.commit()

# ========= STATE =========
users = {}  # uid -> dict (flow state)
REQUEST_COUNTER = 0  # in-memory, but DB also keeps autoincrement; we use DB id for req_id

PARKING_MAP = {"park_yes": "Так", "park_no": "Ні", "park_later": "Пізніше"}
VIEW_MAP = {"view_online": "Онлайн", "view_offline": "Фізичний", "view_both": "Обидва варіанти"}
LOCATION_MAP = {"loc_ua": "Україна", "loc_sk": "Словаччина"}

STATUS_MAP = {
    "search": "🟡 В пошуках",
    "reserved": "🟢 Мають резервацію",
    "self": "🔵 Самі знайшли",
    "other": "🟠 Чужий маклер",
    "stop": "⚫️ Не шукають",
    "closed": "🔴 Закрили угоду",
}

PROPERTY_BUTTONS = [
    ("🛏 Ліжко-місце", "prop_Ліжко-місце"),
    ("🏢 Студія", "prop_Студія"),
    ("1️⃣ 1-кімнатна", "prop_1-кімнатна"),
    ("2️⃣ 2-кімнатна", "prop_2-кімнатна"),
    ("3️⃣ 3-кімнатна", "prop_3-кімнатна"),
    ("4️⃣ 4-кімнатна", "prop_4-кімнатна"),
    ("5️⃣ 5-кімнатна", "prop_5-кімнатна"),
    ("🏠 Будинок", "prop_Будинок"),
    ("✍️ Свій варіант", "prop_custom"),
]


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_phone(phone: str) -> str:
    return re.sub(r"[^\d+]", "", phone or "").strip()


def build_status_keyboard(req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🟡 В пошуках", callback_data=f"status:search:{req_id}"),
                InlineKeyboardButton("🟢 Мають резервацію", callback_data=f"status:reserved:{req_id}"),
            ],
            [
                InlineKeyboardButton("🔵 Самі знайшли", callback_data=f"status:self:{req_id}"),
                InlineKeyboardButton("🟠 Чужий маклер", callback_data=f"status:other:{req_id}"),
            ],
            [
                InlineKeyboardButton("⚫️ Не шукають", callback_data=f"status:stop:{req_id}"),
                InlineKeyboardButton("🔴 Закрили угоду", callback_data=f"status:closed:{req_id}"),
            ],
        ]
    )


def build_summary(u: dict, req_id: int, status: str) -> str:
    tg_line = u.get("tg_username") or "—"
    if tg_line and not tg_line.startswith("@") and tg_line != "—":
        tg_line = "@" + tg_line

    return (
        f"📋 **Запит №{req_id}**\n"
        f"📌 Статус: {STATUS_MAP.get(status, STATUS_MAP['search'])}\n\n"
        f"👤 Імʼя: {u.get('name','—')}\n"
        f"🆔 Telegram: {tg_line}\n"
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


async def reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users.pop(uid, None)
    await update.message.reply_text("🔄 Скинуто. Натисніть /start щоб почати заново.")


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users[uid] = {
        "step": "deal",
        "tg_username": (update.effective_user.username or ""),
        "tg_fullname": (update.effective_user.full_name or ""),
    }

    kb = [
        [InlineKeyboardButton("🏠 Оренда", callback_data="deal_rent")],
        [InlineKeyboardButton("🏡 Купівля", callback_data="deal_buy")],
    ]
    await update.message.reply_text(
        "👋 Вітаємо!\n\n1️⃣ Що вас цікавить?",
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def deal_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    users[uid] = users.get(uid, {})
    users[uid].update(
        {
            "deal": "Оренда" if q.data == "deal_rent" else "Купівля",
            "step": "property",
            "tg_username": (q.from_user.username or ""),
            "tg_fullname": (q.from_user.full_name or ""),
        }
    )

    kb = [[InlineKeyboardButton(t, callback_data=cb)] for (t, cb) in PROPERTY_BUTTONS]
    await q.message.reply_text("2️⃣ 🏡 Тип житла:", reply_markup=InlineKeyboardMarkup(kb))


async def property_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = users.get(uid)
    if not u:
        return

    if q.data == "prop_custom":
        u["step"] = "property_text"
        await q.message.reply_text("✍️ Напишіть тип житла вручну:")
        return

    u["property"] = q.data.replace("prop_", "")
    u["step"] = "city"
    await q.message.reply_text("3️⃣ 📍 В якому місті шукаєте житло?")


async def parking_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = users.get(uid)
    if not u:
        return

    u["parking"] = PARKING_MAP.get(q.data, "—")
    u["step"] = "move_in"
    await q.message.reply_text("9️⃣ 📅 Яка найкраща дата для вашого заїзду?")


async def location_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = users.get(uid)
    if not u:
        return

    if q.data == "loc_custom":
        u["step"] = "custom_location"
        await q.message.reply_text("✍️ Напишіть країну:")
        return

    u["location"] = LOCATION_MAP.get(q.data, "—")
    u["step"] = "view_format"
    await ask_view_format(q.message)


async def ask_view_format(msg):
    kb = [
        [InlineKeyboardButton("💻 Онлайн", callback_data="view_online")],
        [InlineKeyboardButton("🚶 Фізичний", callback_data="view_offline")],
        [InlineKeyboardButton("🔁 Обидва варіанти", callback_data="view_both")],
    ]
    await msg.reply_text("1️⃣3️⃣ 👀 Який формат огляду вам підходить?", reply_markup=InlineKeyboardMarkup(kb))


async def view_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = users.get(uid)
    if not u:
        return

    u["view_format"] = VIEW_MAP.get(q.data, "—")
    u["step"] = "contact"
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Поділитись контактом для пошуку житла", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await q.message.reply_text("📞 Поділіться контактом для пошуку житла:", reply_markup=kb)


async def contact_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = users.get(uid)
    if not u:
        return

    u["phone"] = normalize_phone(update.message.contact.phone_number)
    u["step"] = "name"
    await update.message.reply_text("1️⃣4️⃣ 👤 Як до вас можемо звертатись? (Імʼя/Прізвище)", reply_markup=ReplyKeyboardRemove())


async def confirm_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = users.get(uid)
    if not u:
        return

    if q.data == "confirm_yes":
        kb = [
            [InlineKeyboardButton("✅ Так", callback_data="terms_yes")],
            [InlineKeyboardButton("❌ Ні", callback_data="terms_no")],
        ]
        await q.message.reply_text(
            "ℹ️ **Умови співпраці:**\n\n"
            "• депозит може дорівнювати в розмірі орендної плати\n"
            "• оплачується повна або часткова комісія ріелтору\n"
            "• можливий подвійний депозит при дітях або тваринах\n\n"
            "Чи погоджуєтесь? Натисніть кнопку Так/Ні",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )
    else:
        users.pop(uid, None)
        await q.message.reply_text("❌ Запит скасовано. Натисніть /start щоб почати знову.")


async def terms_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = users.get(uid)
    if not u:
        return

    if q.data == "terms_no":
        users.pop(uid, None)
        await q.message.reply_text("❌ Добре, ми не будемо продовжувати роботу. Натисніть /start якщо передумаєте.")
        return

    # terms_yes:
    # 1) створюємо запис в БД
    cur.execute(
        """
        INSERT INTO requests (user_id, tg_username, tg_fullname, created_at, status, deal, property)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            uid,
            u.get("tg_username", ""),
            u.get("tg_fullname", ""),
            now_utc_iso(),
            "search",
            u.get("deal", ""),
            u.get("property", ""),
        ),
    )
    conn.commit()
    req_id = cur.lastrowid
    u["req_id"] = req_id

    # 2) відправляємо в групу + кнопки статусу (і зберігаємо message_id)
    summary = build_summary(u, req_id=req_id, status="search")
    msg = await ctx.bot.send_message(
        chat_id=ADMIN_GROUP_ID,
        text=summary,
        parse_mode="Markdown",
        reply_markup=build_status_keyboard(req_id),
        disable_web_page_preview=True,
    )

    cur.execute(
        "INSERT OR REPLACE INTO request_group_messages (req_id, chat_id, message_id) VALUES (?, ?, ?)",
        (req_id, ADMIN_GROUP_ID, msg.message_id),
    )
    conn.commit()

    # 3) фінальне повідомлення клієнту + preview лінку
    final_text = (
        "✅ Запит успішно відправлено маклеру!\n\n"
        "☎️ Маклер звʼяжеться з вами протягом 24–48 годин.\n\n"
        "🏡 Долучайтесь до нашої групи з актуальними пропозиціями житла в Братиславі:\n"
        f"{GROUP_LINK}"
    )
    await q.message.reply_text(
        final_text,
        reply_markup=ReplyKeyboardRemove(),
        disable_web_page_preview=False,  # <-- щоб був preview
    )

    users.pop(uid, None)


async def status_change_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data  # status:<key>:<req_id>

    try:
        _, key, req_id_s = data.split(":")
        req_id = int(req_id_s)
    except Exception:
        return

    if key not in STATUS_MAP:
        return

    # оновлюємо статус в БД
    cur.execute("UPDATE requests SET status=? WHERE id=?", (key, req_id))
    conn.commit()

    # беремо дані запиту, щоб перебудувати текст (мінімум: deal/property)
    cur.execute("SELECT user_id, tg_username, tg_fullname, status, deal, property FROM requests WHERE id=?", (req_id,))
    row = cur.fetchone()
    if not row:
        return

    # Відновлюємо частину u для правильного summary, але основний текст ми не маємо з БД.
    # Тому редагуємо лише "Статус" рядок у повідомленні групи (через replace),
    # щоб не ламати решту.
    # Надійніше: просто edit_text залишаючи той самий текст і міняючи статус у верхньому рядку.
    old_text = q.message.text_markdown or q.message.text or ""
    # Пробуємо замінити рядок зі статусом
    new_status_line = f"📌 Статус: {STATUS_MAP[key]}"
    new_text = re.sub(r"^📌 Статус:.*$", new_status_line, old_text, flags=re.MULTILINE)
    if new_text == old_text:
        # якщо не знайшли — додамо на початок
        new_text = f"{new_status_line}\n\n{old_text}"

    try:
        await q.message.edit_text(
            new_text,
            parse_mode="Markdown",
            reply_markup=build_status_keyboard(req_id),
            disable_web_page_preview=True,
        )
    except Exception:
        # якщо Telegram не дає редагувати через markdown/довжину — просто оновимо клавіатуру
        try:
            await q.message.edit_reply_markup(reply_markup=build_status_keyboard(req_id))
        except Exception:
            pass


def stats_text(days: int) -> str:
    # UTC
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    cur.execute(
        """
        SELECT status, property, COUNT(*)
        FROM requests
        WHERE created_at >= ?
        GROUP BY status, property
        ORDER BY status, property
        """,
        (since,),
    )
    rows = cur.fetchall()

    if not rows:
        return f"📊 Статистика за {days} днів:\n\nНемає запитів."

    # групуємо по статусу
    by_status = {}
    for st, prop, cnt in rows:
        by_status.setdefault(st, {})
        by_status[st][prop] = cnt

    lines = [f"📊 **Статистика за {days} днів:**\n"]
    for st_key, props in by_status.items():
        lines.append(f"{STATUS_MAP.get(st_key, st_key)}")
        total = sum(props.values())
        lines.append(f"  • Всього: {total}")
        for prop, cnt in sorted(props.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"  • 🏡 {prop}: {cnt}")
        lines.append("")  # blank line

    return "\n".join(lines).strip()


async def stats_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(stats_text(1), parse_mode="Markdown")


async def stats_week(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(stats_text(7), parse_mode="Markdown")


async def stats_month(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(stats_text(30), parse_mode="Markdown")


async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = users.get(uid)
    if not u:
        return

    t = (update.message.text or "").strip()
    step = u.get("step")

    if step == "property_text":
        u["property"] = t
        u["step"] = "city"
        await update.message.reply_text("3️⃣ 📍 В якому місті шукаєте житло?")

    elif step == "city":
        u["city"] = t
        u["step"] = "district"
        await update.message.reply_text("4️⃣ 🗺 Який район?")

    elif step == "district":
        u["district"] = t
        u["step"] = "for_whom"
        await update.message.reply_text("5️⃣ 👥 Розпишіть, для кого шукаєте житло:")

    elif step == "for_whom":
        u["for_whom"] = t
        u["step"] = "job"
        await update.message.reply_text("6️⃣ 💼 Чим ви займаєтесь? Діяльність:")

    elif step == "job":
        u["job"] = t
        u["step"] = "children"
        await update.message.reply_text("7️⃣ 🧒 Чи маєте дітей? Якщо так — напишіть вік та стать. Якщо ні — «Ні».")

    elif step == "children":
        u["children"] = t
        u["step"] = "pets"
        await update.message.reply_text(
            "8️⃣ 🐾 Чи маєте тваринок?\n"
            "Якщо так — напишіть яку і коротко про неї.\n"
            "Якщо ні — напишіть «Ні»."
        )

    elif step == "pets":
        u["pets"] = t
        u["step"] = "parking"
        kb = [
            [InlineKeyboardButton("✅ Так", callback_data="park_yes")],
            [InlineKeyboardButton("❌ Ні", callback_data="park_no")],
            [InlineKeyboardButton("⏳ Пізніше", callback_data="park_later")],
        ]
        await update.message.reply_text("9️⃣ 🚗 Паркування?", reply_markup=InlineKeyboardMarkup(kb))

    elif step == "move_in":
        u["move_in"] = t
        u["step"] = "view_time"
        await update.message.reply_text("1️⃣0️⃣ ⏰ Коли ви доступні для оглядів? (дні/час)")

    elif step == "view_time":
        u["view_time"] = t
        u["step"] = "wishes"
        await update.message.reply_text("1️⃣1️⃣ ✨ Напишіть особливі побажання до житла:")

    elif step == "wishes":
        u["wishes"] = t
        u["step"] = "budget"
        await update.message.reply_text("1️⃣2️⃣ 💶 Який бюджет на оренду в місяць (від–до €)?")

    elif step == "budget":
        u["budget"] = t
        u["step"] = "location"
        kb = [
            [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc_ua")],
            [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc_sk")],
            [InlineKeyboardButton("✍️ Інша країна", callback_data="loc_custom")],
        ]
        await update.message.reply_text("1️⃣3️⃣ 🌍 Де ви зараз?", reply_markup=InlineKeyboardMarkup(kb))

    elif step == "custom_location":
        u["location"] = t
        u["step"] = "view_format"
        await ask_view_format(update.message)

    elif step == "name":
        u["name"] = t

        kb = [
            [InlineKeyboardButton("✅ Так, вірно", callback_data="confirm_yes")],
            [InlineKeyboardButton("❌ Ні, скасувати", callback_data="confirm_no")],
        ]
        preview = build_summary(u, req_id=0, status="search").replace("Запит №0", "Перевірте дані")
        await update.message.reply_text(
            preview + "\n\nВсе вірно?",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # user flow
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))

    app.add_handler(CallbackQueryHandler(deal_handler, pattern=r"^deal_"))
    app.add_handler(CallbackQueryHandler(property_handler, pattern=r"^prop_"))
    app.add_handler(CallbackQueryHandler(parking_handler, pattern=r"^park_"))
    app.add_handler(CallbackQueryHandler(location_handler, pattern=r"^loc_"))
    app.add_handler(CallbackQueryHandler(view_handler, pattern=r"^view_"))
    app.add_handler(CallbackQueryHandler(confirm_handler, pattern=r"^confirm_"))
    app.add_handler(CallbackQueryHandler(terms_handler, pattern=r"^terms_"))

    # group status buttons
    app.add_handler(CallbackQueryHandler(status_change_handler, pattern=r"^status:"))

    # contact
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))

    # text steps
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # stats commands (for group)
    app.add_handler(CommandHandler("stats_today", stats_today))
    app.add_handler(CommandHandler("stats_week", stats_week))
    app.add_handler(CommandHandler("stats_month", stats_month))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
