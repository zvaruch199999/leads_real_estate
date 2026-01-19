import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ----------------------------
# CONFIG (env first, then optional config.py)
# ----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID")

try:
    # optional if you have config.py
    from config import BOT_TOKEN as CFG_BOT_TOKEN, ADMIN_GROUP_ID as CFG_ADMIN_GROUP_ID
    BOT_TOKEN = BOT_TOKEN or CFG_BOT_TOKEN
    ADMIN_GROUP_ID = ADMIN_GROUP_ID or CFG_ADMIN_GROUP_ID
except Exception:
    pass

if not BOT_TOKEN or not ADMIN_GROUP_ID:
    raise RuntimeError("BOT_TOKEN або ADMIN_GROUP_ID не задані")

ADMIN_GROUP_ID = int(ADMIN_GROUP_ID)

GROUP_LINK = "https://t.me/+IhcJixOP1_QyNjM0"

# ----------------------------
# DB
# ----------------------------
DB_PATH = "real_estate.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    req_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    username TEXT,
    name TEXT,
    phone TEXT,

    deal TEXT,
    property TEXT,
    city TEXT,
    district TEXT,
    for_whom TEXT,
    job TEXT,
    children TEXT,
    pets TEXT,
    parking TEXT,
    move_in TEXT,
    budget TEXT,
    view_time TEXT,
    wishes TEXT,
    location TEXT,
    view_format TEXT,

    status_key TEXT NOT NULL DEFAULT 'searching',
    created_at TEXT NOT NULL,
    group_chat_id INTEGER,
    group_message_id INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS counters (
    k TEXT PRIMARY KEY,
    v INTEGER NOT NULL
)
""")
cur.execute("INSERT OR IGNORE INTO counters (k,v) VALUES ('request_counter', 0)")
conn.commit()

# ----------------------------
# In-memory state
# ----------------------------
users = {}  # uid -> dict

# ----------------------------
# Maps / enums
# ----------------------------
STATUS = {
    "searching": "🟡 В пошуках",
    "reserved": "🟢 Мають резервацію",
    "self_found": "🔵 Самі знайшли",
    "other_realtor": "🟠 Знайшов чужий маклер",
    "not_searching": "⚫ Не шукають вже",
    "closed": "🔴 Закрили угоду",
}

STATUS_BUTTONS = [
    [InlineKeyboardButton(STATUS["searching"], callback_data="status:{lead_id}:searching"),
     InlineKeyboardButton(STATUS["reserved"], callback_data="status:{lead_id}:reserved")],
    [InlineKeyboardButton(STATUS["self_found"], callback_data="status:{lead_id}:self_found"),
     InlineKeyboardButton(STATUS["other_realtor"], callback_data="status:{lead_id}:other_realtor")],
    [InlineKeyboardButton(STATUS["not_searching"], callback_data="status:{lead_id}:not_searching"),
     InlineKeyboardButton(STATUS["closed"], callback_data="status:{lead_id}:closed")],
]

PARKING_MAP = {"yes": "Так", "no": "Ні", "later": "Пізніше"}
VIEW_MAP = {"online": "Онлайн", "offline": "Фізичний", "both": "Обидва варіанти"}
LOCATION_MAP = {"ua": "Україна", "sk": "Словаччина"}

PROPERTY_OPTIONS = [
    ("🛏 Ліжко-місце", "bed"),
    ("🚪 Кімната", "room"),
    ("🏢 Студія", "studio"),
    ("1️⃣ 1-кімнатна", "1"),
    ("2️⃣ 2-кімнатна", "2"),
    ("3️⃣ 3-кімнатна", "3"),
    ("4️⃣ 4-кімнатна", "4"),
    ("5️⃣ 5-кімнатна", "5"),
    ("🏠 Будинок", "house"),
    ("✍️ Свій варіант", "custom"),
]

PHONE_RE = re.compile(r"^\+?\d[\d\s().-]{6,}$")


# ----------------------------
# Helpers
# ----------------------------
def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def ua_username(u) -> str:
    if u.username:
        return f"@{u.username}"
    return "—"

def next_req_id() -> int:
    cur.execute("UPDATE counters SET v = v + 1 WHERE k='request_counter'")
    cur.execute("SELECT v FROM counters WHERE k='request_counter'")
    conn.commit()
    return int(cur.fetchone()[0])

def build_summary_text(data: dict, req_id: int, status_key: str = "searching") -> str:
    return (
        f"📋 <b>Запит №{req_id}</b>\n"
        f"📌 <b>Статус:</b> {STATUS.get(status_key, STATUS['searching'])}\n\n"

        f"👤 <b>Імʼя:</b> {data.get('name','—')}\n"
        f"🆔 <b>Telegram:</b> {data.get('telegram','—')}\n"
        f"📞 <b>Телефон:</b> {data.get('phone','—')}\n\n"

        f"1️⃣ 🏠 <b>Тип угоди:</b> {data.get('deal','—')}\n"
        f"2️⃣ 🏡 <b>Тип житла:</b> {data.get('property','—')}\n"
        f"3️⃣ 📍 <b>Місто:</b> {data.get('city','—')}\n"
        f"4️⃣ 🗺 <b>Район:</b> {data.get('district','—')}\n"
        f"5️⃣ 👥 <b>Для кого:</b> {data.get('for_whom','—')}\n"
        f"6️⃣ 💼 <b>Діяльність:</b> {data.get('job','—')}\n"
        f"7️⃣ 🧒 <b>Діти:</b> {data.get('children','—')}\n"
        f"8️⃣ 🐾 <b>Тваринки:</b> {data.get('pets','—')}\n"
        f"9️⃣ 🚗 <b>Паркування:</b> {data.get('parking','—')}\n"
        f"🔟 📅 <b>Дата заїзду:</b> {data.get('move_in','—')}\n"
        f"1️⃣1️⃣ 💶 <b>Бюджет оренда (в місяць):</b> {data.get('budget','—')}\n"
        f"1️⃣2️⃣ ⏰ <b>Доступність для оглядів:</b> {data.get('view_time','—')}\n"
        f"1️⃣3️⃣ ✨ <b>Побажання:</b> {data.get('wishes','—')}\n"
        f"1️⃣4️⃣ 🌍 <b>Зараз в:</b> {data.get('location','—')}\n"
        f"1️⃣5️⃣ 👀 <b>Формат огляду:</b> {data.get('view_format','—')}\n"
    )

def status_markup(lead_id: int) -> InlineKeyboardMarkup:
    kb = []
    for row in STATUS_BUTTONS:
        kb.append([InlineKeyboardButton(btn.text, callback_data=btn.callback_data.format(lead_id=lead_id)) for btn in row])
    return InlineKeyboardMarkup(kb)

async def safe_answer(q):
    try:
        await q.answer()
    except Exception:
        pass

def ensure_user(uid: int):
    if uid not in users:
        users[uid] = {"step": None}

def reset_user(uid: int):
    users.pop(uid, None)

async def ask_deal(update: Update):
    kb = [
        [InlineKeyboardButton("🏠 Оренда", callback_data="deal:rent")],
        [InlineKeyboardButton("🏡 Купівля", callback_data="deal:buy")],
    ]
    await update.message.reply_text(
        "👋 Вітаємо! Почнемо анкету.\n\n1️⃣ 🏠 Що вас цікавить?",
        reply_markup=InlineKeyboardMarkup(kb),
    )

async def ask_property(msg):
    rows = []
    for label, key in PROPERTY_OPTIONS:
        rows.append([InlineKeyboardButton(label, callback_data=f"prop:{key}")])
    await msg.reply_text(
        "2️⃣ 🏡 Який тип житла вас цікавить?",
        reply_markup=InlineKeyboardMarkup(rows),
    )

async def ask_parking(msg):
    kb = [
        [InlineKeyboardButton("Так", callback_data="park:yes")],
        [InlineKeyboardButton("Ні", callback_data="park:no")],
        [InlineKeyboardButton("Пізніше", callback_data="park:later")],
    ]
    await msg.reply_text(
        "9️⃣ 🚗 Чи потрібне паркування?",
        reply_markup=InlineKeyboardMarkup(kb),
    )

async def ask_location(msg):
    kb = [
        [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc:ua")],
        [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc:sk")],
        [InlineKeyboardButton("✍️ Інша країна", callback_data="loc:custom")],
    ]
    await msg.reply_text(
        "1️⃣4️⃣ 🌍 Де ви зараз знаходитесь?",
        reply_markup=InlineKeyboardMarkup(kb),
    )

async def ask_view_format(msg):
    kb = [
        [InlineKeyboardButton("💻 Онлайн", callback_data="view:online")],
        [InlineKeyboardButton("🚶 Фізичний", callback_data="view:offline")],
        [InlineKeyboardButton("🔁 Обидва варіанти", callback_data="view:both")],
    ]
    await msg.reply_text(
        "1️⃣5️⃣ 👀 Який формат огляду вам підходить?",
        reply_markup=InlineKeyboardMarkup(kb),
    )

async def ask_phone(msg):
    # Telegram limitation: request_contact only via reply keyboard (not inline).
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Поділитись контактом для пошуку житла", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await msg.reply_text(
        "1️⃣6️⃣ 📞 Поділіться контактом для пошуку житла\n"
        "або напишіть номер телефону вручну (наприклад: +421901234567):",
        reply_markup=kb,
    )

async def send_check_summary(update: Update, uid: int):
    u = users[uid]
    kb = [
        [InlineKeyboardButton("✅ Так, вірно", callback_data="confirm:yes")],
        [InlineKeyboardButton("❌ Ні, скасувати", callback_data="confirm:no")],
    ]
    txt = build_summary_text(u, u["req_id"], status_key="searching") + "\n<b>Все вірно?</b>"
    await update.message.reply_text(
        txt,
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )

async def send_terms(q_msg):
    kb = [
        [InlineKeyboardButton("✅ Так", callback_data="terms:yes")],
        [InlineKeyboardButton("❌ Ні", callback_data="terms:no")],
    ]
    await q_msg.reply_text(
        "ℹ️ <b>Умови співпраці:</b>\n\n"
        "• депозит може дорівнювати в розмірі орендної плати\n"
        "• оплачується повна або часткова комісія ріелтору\n"
        "• можливий подвійний депозит при дітях або тваринах\n\n"
        "<b>Чи погоджуєтесь?</b>",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.HTML,
    )

async def post_to_group(u: dict) -> tuple[int, int, int]:
    """
    returns (lead_db_id, group_chat_id, group_message_id)
    """
    # Insert into DB first to get lead_id
    cur.execute("""
    INSERT INTO leads (
        req_id, user_id, username, name, phone,
        deal, property, city, district, for_whom, job, children, pets, parking, move_in,
        budget, view_time, wishes, location, view_format,
        status_key, created_at, group_chat_id, group_message_id
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        u["req_id"], u["user_id"], u.get("telegram_raw"), u.get("name"), u.get("phone"),
        u.get("deal"), u.get("property"), u.get("city"), u.get("district"),
        u.get("for_whom"), u.get("job"), u.get("children"), u.get("pets"), u.get("parking"),
        u.get("move_in"), u.get("budget"), u.get("view_time"), u.get("wishes"),
        u.get("location"), u.get("view_format"),
        "searching", now_utc_iso(), None, None
    ))
    conn.commit()
    lead_id = cur.lastrowid

    # Build message for group
    group_text = build_summary_text(u, u["req_id"], status_key="searching")

    sent = await u["ctx"].bot.send_message(
        chat_id=ADMIN_GROUP_ID,
        text=group_text,
        parse_mode=ParseMode.HTML,
        reply_markup=status_markup(lead_id),
        disable_web_page_preview=True,
    )

    # Save message ids
    cur.execute("UPDATE leads SET group_chat_id=?, group_message_id=? WHERE id=?",
                (sent.chat_id, sent.message_id, lead_id))
    conn.commit()

    return lead_id, sent.chat_id, sent.message_id

def stats_text(days: int) -> str:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    cur.execute("""
        SELECT property, status_key, COUNT(*)
        FROM leads
        WHERE created_at >= ?
        GROUP BY property, status_key
        ORDER BY property ASC
    """, (since.isoformat(),))
    rows = cur.fetchall()

    if not rows:
        return f"📊 <b>Статистика за {days} дн.</b>\n\nНемає запитів за цей період."

    # Aggregate
    by_property = {}
    total_by_status = {k: 0 for k in STATUS.keys()}
    total = 0

    for prop, st, cnt in rows:
        by_property.setdefault(prop or "—", {k: 0 for k in STATUS.keys()})
        if st not in by_property[prop or "—"]:
            by_property[prop or "—"][st] = 0
        by_property[prop or "—"][st] += cnt
        if st in total_by_status:
            total_by_status[st] += cnt
        total += cnt

    lines = [f"📊 <b>Статистика за {days} дн.</b>\n"]
    lines.append(f"🧾 <b>Всього запитів:</b> {total}\n")

    lines.append("📌 <b>По статусах:</b>")
    for k in ["searching", "reserved", "self_found", "other_realtor", "not_searching", "closed"]:
        lines.append(f"• {STATUS[k]}: <b>{total_by_status.get(k,0)}</b>")
    lines.append("")

    lines.append("🏡 <b>По типу житла (і статусах):</b>")
    for prop, sts in sorted(by_property.items(), key=lambda x: x[0].lower()):
        prop_total = sum(sts.values())
        if prop_total == 0:
            continue
        lines.append(f"\n<b>{prop}</b> — {prop_total}")
        for k in ["searching", "reserved", "self_found", "other_realtor", "not_searching", "closed"]:
            c = sts.get(k, 0)
            if c:
                lines.append(f"  • {STATUS[k]}: <b>{c}</b>")

    return "\n".join(lines).strip()


# ----------------------------
# Handlers
# ----------------------------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    reset_user(update.effective_user.id)
    ensure_user(update.effective_user.id)
    await ask_deal(update)

async def reset_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    reset_user(update.effective_user.id)
    await update.message.reply_text("🔄 Анкету скинуто. Натисніть /start щоб почати заново.")

async def deal_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await safe_answer(q)
    uid = q.from_user.id
    ensure_user(uid)

    users[uid].update({
        "user_id": uid,
        "telegram": ua_username(q.from_user),
        "telegram_raw": q.from_user.username or None,
        "ctx": ctx,
        "deal": "Оренда" if q.data == "deal:rent" else "Купівля",
        "step": "property",
    })
    await ask_property(q.message)

async def prop_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await safe_answer(q)
    uid = q.from_user.id
    u = users.get(uid)
    if not u:
        return

    key = q.data.split(":", 1)[1]
    if key == "custom":
        u["step"] = "property_text"
        await q.message.reply_text("✍️ Напишіть свій варіант типу житла:")
        return

    # map keys to readable labels
    key_to_label = {
        "bed": "Ліжко-місце",
        "room": "Кімната",
        "studio": "Студія",
        "1": "1-кімнатна",
        "2": "2-кімнатна",
        "3": "3-кімнатна",
        "4": "4-кімнатна",
        "5": "5-кімнатна",
        "house": "Будинок",
    }
    u["property"] = key_to_label.get(key, key)
    u["step"] = "city"
    await q.message.reply_text("3️⃣ 📍 В якому місті шукаєте житло?")

async def parking_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await safe_answer(q)
    uid = q.from_user.id
    u = users.get(uid)
    if not u:
        return

    key = q.data.split(":", 1)[1]
    u["parking"] = PARKING_MAP.get(key, "—")
    u["step"] = "move_in"
    await q.message.reply_text("🔟 📅 Яка найкраща дата для вашого заїзду?")

async def location_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await safe_answer(q)
    uid = q.from_user.id
    u = users.get(uid)
    if not u:
        return

    key = q.data.split(":", 1)[1]
    if key == "custom":
        u["step"] = "location_text"
        await q.message.reply_text("✍️ Напишіть країну:")
        return

    u["location"] = LOCATION_MAP.get(key, "—")
    u["step"] = "view_format"
    await ask_view_format(q.message)

async def view_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await safe_answer(q)
    uid = q.from_user.id
    u = users.get(uid)
    if not u:
        return

    key = q.data.split(":", 1)[1]
    u["view_format"] = VIEW_MAP.get(key, "—")
    u["step"] = "phone"
    await ask_phone(q.message)

async def confirm_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await safe_answer(q)
    uid = q.from_user.id
    u = users.get(uid)
    if not u:
        return

    key = q.data.split(":", 1)[1]
    if key == "no":
        reset_user(uid)
        await q.message.reply_text("❌ Запит скасовано. Натисніть /start щоб почати заново.")
        return

    # yes -> show terms
    await send_terms(q.message)

async def terms_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await safe_answer(q)
    uid = q.from_user.id
    u = users.get(uid)
    if not u:
        return

    key = q.data.split(":", 1)[1]
    if key == "no":
        reset_user(uid)
        await q.message.reply_text("❌ Добре, ми не будемо продовжувати роботу. /start — щоб почати заново.")
        return

    # YES -> send to group + final message to user
    try:
        u["ctx"] = ctx  # ensure
        lead_id, _, _ = await post_to_group(u)
        u["lead_id"] = lead_id
    except Exception as e:
        # still inform user
        await q.message.reply_text(
            "⚠️ Сталась помилка при відправленні запиту в групу.\n"
            "Спробуйте ще раз /start або напишіть адміну.",
        )
        reset_user(uid)
        return

    # Final message (with preview)
    await q.message.reply_text(
        "✅ <b>Запит успішно відправлено маклеру!</b>\n\n"
        "📞 Маклер звʼяжеться з вами протягом <b>24–48 годин</b>.\n\n"
        "🏠 Долучайтесь до нашої групи з актуальними пропозиціями житла в Братиславі:\n"
        f"👉 {GROUP_LINK}",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=False,  # allow preview
        reply_markup=ReplyKeyboardRemove(),
    )

    reset_user(uid)

async def status_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await safe_answer(q)

    # callback: status:<lead_id>:<status_key>
    try:
        _, lead_id_s, new_key = q.data.split(":", 2)
        lead_id = int(lead_id_s)
    except Exception:
        return

    if new_key not in STATUS:
        return

    # Load current lead
    cur.execute("""
        SELECT req_id, user_id, username, name, phone, deal, property, city, district,
               for_whom, job, children, pets, parking, move_in, budget, view_time, wishes,
               location, view_format, status_key, group_chat_id, group_message_id
        FROM leads WHERE id=?
    """, (lead_id,))
    row = cur.fetchone()
    if not row:
        return

    (
        req_id, user_id, username, name, phone, deal, prop, city, district,
        for_whom, job, children, pets, parking, move_in, budget, view_time, wishes,
        location, view_format, old_status, gchat, gmsg
    ) = row

    # Update DB
    cur.execute("UPDATE leads SET status_key=? WHERE id=?", (new_key, lead_id))
    conn.commit()

    # Edit same message in group
    data = {
        "name": name or "—",
        "telegram": f"@{username}" if username else "—",
        "telegram_raw": username,
        "phone": phone or "—",
        "deal": deal or "—",
        "property": prop or "—",
        "city": city or "—",
        "district": district or "—",
        "for_whom": for_whom or "—",
        "job": job or "—",
        "children": children or "—",
        "pets": pets or "—",
        "parking": parking or "—",
        "move_in": move_in or "—",
        "budget": budget or "—",
        "view_time": view_time or "—",
        "wishes": wishes or "—",
        "location": location or "—",
        "view_format": view_format or "—",
    }
    new_text = build_summary_text(data, req_id, status_key=new_key)

    try:
        await ctx.bot.edit_message_text(
            chat_id=gchat,
            message_id=gmsg,
            text=new_text,
            parse_mode=ParseMode.HTML,
            reply_markup=status_markup(lead_id),
            disable_web_page_preview=True,
        )
    except Exception:
        # if can't edit (too old), at least keep buttons working
        pass

async def stats_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(stats_text(1), parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def stats_week(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(stats_text(7), parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def stats_month(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(stats_text(30), parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def contact_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = users.get(uid)
    if not u:
        return
    # Accept contact only when step expects phone
    if u.get("step") != "phone":
        return

    u["phone"] = update.message.contact.phone_number
    u["step"] = "name"
    await update.message.reply_text(
        "1️⃣7️⃣ 👤 Як до вас можемо звертатись? (Імʼя/Прізвище)",
        reply_markup=ReplyKeyboardRemove(),
    )

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in users:
        return
    u = users[uid]
    step = u.get("step")
    text = (update.message.text or "").strip()

    if not step:
        return

    if step == "property_text":
        u["property"] = text
        u["step"] = "city"
        await update.message.reply_text("3️⃣ 📍 В якому місті шукаєте житло?")
        return

    if step == "city":
        u["city"] = text
        u["step"] = "district"
        await update.message.reply_text("4️⃣ 🗺 Який район?")
        return

    if step == "district":
        u["district"] = text
        u["step"] = "for_whom"
        await update.message.reply_text("5️⃣ 👥 Розпишіть, для кого шукаєте житло:")
        return

    if step == "for_whom":
        u["for_whom"] = text
        u["step"] = "job"
        await update.message.reply_text("6️⃣ 💼 Чим ви займаєтесь? (Діяльність)")
        return

    if step == "job":
        u["job"] = text
        u["step"] = "children"
        await update.message.reply_text(
            "7️⃣ 🧒 Чи маєте дітей?\nЯкщо так — напишіть вік та стать.\nЯкщо ні — напишіть «Ні»."
        )
        return

    if step == "children":
        u["children"] = text
        u["step"] = "pets"
        await update.message.reply_text(
            "8️⃣ 🐾 Чи маєте тваринок?\n"
            "Якщо так — напишіть яку і трошки про неї.\n"
            "Якщо ні — напишіть «Ні»."
        )
        return

    if step == "pets":
        u["pets"] = text
        u["step"] = "parking"
        await ask_parking(update.message)
        return

    if step == "move_in":
        u["move_in"] = text
        u["step"] = "budget"
        await update.message.reply_text("1️⃣1️⃣ 💶 Який бюджет на оренду в місяць (від–до€)?")
        return

    if step == "budget":
        u["budget"] = text
        u["step"] = "view_time"
        await update.message.reply_text("1️⃣2️⃣ ⏰ Як зазвичай ви доступні для оглядів? (дні/час)")
        return

    if step == "view_time":
        u["view_time"] = text
        u["step"] = "wishes"
        await update.message.reply_text("1️⃣3️⃣ ✨ Напишіть особливі побажання на житло:")
        return

    if step == "wishes":
        u["wishes"] = text
        u["step"] = "location"
        await ask_location(update.message)
        return

    if step == "location_text":
        u["location"] = text
        u["step"] = "view_format"
        await ask_view_format(update.message)
        return

    if step == "phone":
        # allow manual phone input
        if not PHONE_RE.match(text):
            await update.message.reply_text(
                "⚠️ Не схоже на номер телефону.\n"
                "Напишіть номер у форматі +421901234567 або натисніть кнопку «Поділитись контактом»."
            )
            return
        u["phone"] = text
        u["step"] = "name"
        await update.message.reply_text(
            "1️⃣7️⃣ 👤 Як до вас можемо звертатись? (Імʼя/Прізвище)",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if step == "name":
        u["name"] = text
        # assign req_id once at end
        u["req_id"] = next_req_id()
        u["step"] = "confirm"
        await send_check_summary(update, uid)
        return

async def park_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # when parking chosen -> move_in next
    await parking_handler(update, ctx)

async def deal_to_property_flow_guard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # (not used) kept for clarity
    pass

# ----------------------------
# main
# ----------------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset_cmd))

    # stats in group
    app.add_handler(CommandHandler("stats_today", stats_today))
    app.add_handler(CommandHandler("stats_week", stats_week))
    app.add_handler(CommandHandler("stats_month", stats_month))

    # callbacks
    app.add_handler(CallbackQueryHandler(deal_handler, pattern=r"^deal:"))
    app.add_handler(CallbackQueryHandler(prop_handler, pattern=r"^prop:"))
    app.add_handler(CallbackQueryHandler(park_cb, pattern=r"^park:"))
    app.add_handler(CallbackQueryHandler(location_handler, pattern=r"^loc:"))
    app.add_handler(CallbackQueryHandler(view_handler, pattern=r"^view:"))
    app.add_handler(CallbackQueryHandler(confirm_handler, pattern=r"^confirm:"))
    app.add_handler(CallbackQueryHandler(terms_handler, pattern=r"^terms:"))
    app.add_handler(CallbackQueryHandler(status_handler, pattern=r"^status:"))

    # messages
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
