# bot.py  (python-telegram-bot v20+)
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
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

# =========================
# CONFIG / ENV
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID", "").strip()

if not BOT_TOKEN or not ADMIN_GROUP_ID:
    raise RuntimeError("BOT_TOKEN або ADMIN_GROUP_ID не задані")

ADMIN_GROUP_ID = int(ADMIN_GROUP_ID)

# Адмін тільки ти (Варіант A)
ADMIN_IDS = {1057216609}

# Ліміт для звичайних користувачів
COOLDOWN_HOURS = 2

GROUP_INVITE_LINK = "https://t.me/+IhcJixOP1_QyNjM0"

# =========================
# DB
# =========================
conn = sqlite3.connect("real_estate.db", check_same_thread=False)
cur = conn.cursor()

cur.execute(
    """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    req_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    username TEXT,
    tg_fullname TEXT,

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

    phone TEXT,
    name TEXT,

    status_key TEXT NOT NULL DEFAULT 'searching',
    created_at TEXT NOT NULL,

    group_message_id INTEGER
);
"""
)
cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_user_created ON leads(user_id, created_at);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status_key);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_deal_created ON leads(deal, created_at);")
conn.commit()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


def has_active_lead(uid: int) -> bool:
    cur.execute(
        """
        SELECT COUNT(*)
        FROM leads
        WHERE user_id=?
          AND status_key IN ('searching','reserved')
        """,
        (uid,),
    )
    return (cur.fetchone()[0] or 0) > 0


def has_recent_lead(uid: int, hours: int) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    cur.execute(
        """
        SELECT COUNT(*)
        FROM leads
        WHERE user_id=?
          AND created_at >= ?
        """,
        (uid, cutoff.isoformat()),
    )
    return (cur.fetchone()[0] or 0) > 0


def next_req_id() -> int:
    cur.execute("SELECT COALESCE(MAX(req_id),0) FROM leads")
    return int(cur.fetchone()[0] or 0) + 1


def normalize_phone(s: str) -> str:
    return re.sub(r"[^\d+]", "", (s or "").strip())


PHONE_RE = re.compile(r"^\+?\d[\d\s\-\(\)]{6,}$")

# =========================
# UI MAPS
# =========================
PARKING_MAP = {"park_yes": "Так", "park_no": "Ні", "park_later": "Пізніше"}

VIEW_MAP = {"view_online": "Онлайн", "view_offline": "Фізичний", "view_both": "Обидва варіанти"}

LOCATION_MAP = {"loc_ua": "Україна", "loc_sk": "Словаччина"}

PROPERTY_BUTTONS = [
    ("🛏 Ліжко-місце", "prop_bed"),
    ("🚪 Кімната", "prop_room"),
    ("🏢 Студія", "prop_studio"),
    ("1️⃣ 1-кімнатна", "prop_1"),
    ("2️⃣ 2-кімнатна", "prop_2"),
    ("3️⃣ 3-кімнатна", "prop_3"),
    ("4️⃣ 4-кімнатна", "prop_4"),
    ("5️⃣ 5-кімнатна", "prop_5"),
    ("🏠 Будинок", "prop_house"),
    ("✍️ Свій варіант", "prop_custom"),
]
PROPERTY_VALUE = {
    "prop_bed": "Ліжко-місце",
    "prop_room": "Кімната",
    "prop_studio": "Студія",
    "prop_1": "1-кімнатна",
    "prop_2": "2-кімнатна",
    "prop_3": "3-кімнатна",
    "prop_4": "4-кімнатна",
    "prop_5": "5-кімнатна",
    "prop_house": "Будинок",
}

# Купівля — тип нерухомості
BUY_PROPERTY_BUTTONS = [
    ("🏢 Квартира", "buyprop_flat"),
    ("🏠 Будинок", "buyprop_house"),
    ("🏞 Земля", "buyprop_land"),
    ("🏬 Комерційна", "buyprop_commercial"),
    ("✍️ Свій варіант", "buyprop_custom"),
]
BUY_PROPERTY_VALUE = {
    "buyprop_flat": "Квартира",
    "buyprop_house": "Будинок",
    "buyprop_land": "Земля",
    "buyprop_commercial": "Комерційна",
}

BUY_FINANCE_BUTTONS = [
    ("💰 Власні кошти", "buyfin_cash"),
    ("🏦 Іпотека", "buyfin_mortgage"),
    ("🔁 Комбінація", "buyfin_combo"),
    ("✍️ Свій варіант", "buyfin_custom"),
]
BUY_FINANCE_VALUE = {
    "buyfin_cash": "Власні кошти",
    "buyfin_mortgage": "Іпотека",
    "buyfin_combo": "Комбінація",
}

STATUS_LABEL = {
    "searching": "🟡 В пошуках",
    "reserved": "🟢 Мають резервацію",
    "self_found": "🔵 Самі знайшли",
    "other_agent": "🟠 Знайшов чужий рієлтор",
    "not_searching": "⚫ Не шукають вже",
    "closed": "🔴 Закрили угоду",
}


def status_keyboard(lead_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🟡 В пошуках", callback_data=f"status:{lead_id}:searching"),
                InlineKeyboardButton("🟢 Мають резервацію", callback_data=f"status:{lead_id}:reserved"),
            ],
            [
                InlineKeyboardButton("🔵 Самі знайшли", callback_data=f"status:{lead_id}:self_found"),
                InlineKeyboardButton("🟠 Чужий рієлтор", callback_data=f"status:{lead_id}:other_agent"),
            ],
            [
                InlineKeyboardButton("⚫ Не шукають", callback_data=f"status:{lead_id}:not_searching"),
                InlineKeyboardButton("🔴 Закрили угоду", callback_data=f"status:{lead_id}:closed"),
            ],
        ]
    )

# =========================
# FLOW STATE
# =========================
users = {}  # uid -> dict


def ensure_user(uid: int):
    if uid not in users:
        users[uid] = {"step": None}


def reset_user(uid: int):
    users.pop(uid, None)


def tg_display(user) -> str:
    if user.username:
        return f"@{user.username}"
    return f"tg://user?id={user.id}"


def safe_html(s: str) -> str:
    return (s or "").replace("<", "").replace(">", "")


def build_summary_html(u: dict, req_id: int, status_key: str) -> str:
    deal = u.get("deal", "—")

    if deal == "Купівля":
        return (
            f"📋 <b>Запит №{req_id}</b>\n"
            f"📌 <b>Статус:</b> {STATUS_LABEL.get(status_key, STATUS_LABEL['searching'])}\n\n"
            f"👤 <b>Як до вас звертатись:</b> {safe_html(u.get('name','—'))}\n"
            f"🆔 <b>Telegram:</b> {safe_html(u.get('tg','—'))}\n"
            f"📞 <b>Телефон:</b> {safe_html(u.get('phone','—'))}\n\n"
            f"1️⃣ 🏡 <b>Тип угоди:</b> Купівля\n"
            f"2️⃣ 🏠 <b>Яку нерухомість шукаєте:</b> {safe_html(u.get('property','—'))}\n"
            f"3️⃣ ✨ <b>Очікування/деталі:</b> {safe_html(u.get('wishes','—'))}\n"
            f"4️⃣ 📍 <b>Де хочете купити:</b> {safe_html(u.get('city','—'))}\n"
            f"5️⃣ 💶 <b>Ціна (від-до):</b> {safe_html(u.get('budget','—'))}\n"
            f"6️⃣ 💳 <b>Фінансування:</b> {safe_html(u.get('job','—'))}\n"
            f"7️⃣ 📅 <b>Коли купити:</b> {safe_html(u.get('move_in','—'))}\n"
            f"8️⃣ ⏰ <b>Доступність оглядів:</b> {safe_html(u.get('view_time','—'))}\n"
        )

    return (
        f"📋 <b>Запит №{req_id}</b>\n"
        f"📌 <b>Статус:</b> {STATUS_LABEL.get(status_key, STATUS_LABEL['searching'])}\n\n"
        f"👤 <b>Імʼя/Прізвище:</b> {safe_html(u.get('name','—'))}\n"
        f"🆔 <b>Telegram:</b> {safe_html(u.get('tg','—'))}\n"
        f"📞 <b>Телефон:</b> {safe_html(u.get('phone','—'))}\n\n"
        f"1️⃣ 🏠 <b>Тип угоди:</b> {safe_html(u.get('deal','—'))}\n"
        f"2️⃣ 🏡 <b>Тип житла:</b> {safe_html(u.get('property','—'))}\n"
        f"3️⃣ 📍 <b>Місто:</b> {safe_html(u.get('city','—'))}\n"
        f"4️⃣ 🗺 <b>Район:</b> {safe_html(u.get('district','—'))}\n"
        f"5️⃣ 👥 <b>Для кого:</b> {safe_html(u.get('for_whom','—'))}\n"
        f"6️⃣ 💼 <b>Діяльність:</b> {safe_html(u.get('job','—'))}\n"
        f"👥 <b>Кількість осіб:</b> {safe_html(u.get('people_count','—'))}\n"
f"📄 <b>Документи:</b> {safe_html(u.get('slovakia_docs','—'))}\n"
f"🇸🇰 <b>В Словаччині:</b> {safe_html(u.get('slovakia_time','—'))}\n"
f"🗣 <b>Мова:</b> {safe_html(u.get('language_owner','—'))}\n"
f"📝 <b>Прописка:</b> {safe_html(u.get('registration','—'))}\n"
f"📧 <b>Email:</b> {safe_html(u.get('email','—'))}\n"
        f"7️⃣ 🧒 <b>Діти:</b> {safe_html(u.get('children','—'))}\n"
        f"8️⃣ 🐾 <b>Тваринки:</b> {safe_html(u.get('pets','—'))}\n"
        f"9️⃣ 🚗 <b>Паркування:</b> {safe_html(u.get('parking','—'))}\n"
        f"🔟 📅 <b>Заїзд:</b> {safe_html(u.get('move_in','—'))}\n"
        f"1️⃣1️⃣ 💶 <b>Бюджет оренда (€/міс):</b> {safe_html(u.get('budget','—'))}\n"
        f"1️⃣2️⃣ ⏰ <b>Огляди (дні/час):</b> {safe_html(u.get('view_time','—'))}\n"
        f"1️⃣3️⃣ ✨ <b>Побажання:</b> {safe_html(u.get('wishes','—'))}\n"
        f"1️⃣4️⃣ 🌍 <b>Зараз в:</b> {safe_html(u.get('location','—'))}\n"
        f"1️⃣5️⃣ 👀 <b>Формат огляду:</b> {safe_html(u.get('view_format','—'))}\n"
    )


async def ask_contact(message, u: dict):
    u["step"] = "phone"
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Поділитись контактом для пошуку житла", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.reply_text(
        "📞 Поділіться контактом (кнопкою нижче)\n"
        "або напишіть номер телефону вручну (наприклад: +421901234567):",
        reply_markup=kb,
    )


async def finalize_lead_and_notify(ctx: ContextTypes.DEFAULT_TYPE, user_message, u: dict):
    req_id = next_req_id()
    u["req_id"] = req_id
    status_key = "searching"
    created_at = now_iso()

    cur.execute(
        """
        INSERT INTO leads (
            req_id, user_id, username, tg_fullname,
            deal, property, city, district, for_whom, job, children, pets, parking,
            move_in, budget, view_time, wishes, location, view_format,
            phone, name, status_key, created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            req_id,
            u.get("user_id"),
            u.get("tg"),
            u.get("tg_fullname", ""),
            u.get("deal", ""),
            u.get("property", ""),
            u.get("city", ""),
            u.get("district", ""),
            u.get("for_whom", ""),
            u.get("job", ""),
            u.get("children", ""),
            u.get("pets", ""),
            u.get("parking", ""),
            u.get("move_in", ""),
            u.get("budget", ""),
            u.get("view_time", ""),
            u.get("wishes", ""),
            u.get("location", ""),
            u.get("view_format", ""),
            u.get("phone", ""),
            u.get("name", ""),
            status_key,
            created_at,
        ),
    )
    conn.commit()
    lead_id = cur.lastrowid

    msg_text = build_summary_html(u, req_id=req_id, status_key=status_key)
    sent = await ctx.bot.send_message(
        chat_id=ADMIN_GROUP_ID,
        text=msg_text,
        parse_mode=ParseMode.HTML,
        reply_markup=status_keyboard(lead_id),
        disable_web_page_preview=True,
    )
    cur.execute("UPDATE leads SET group_message_id=? WHERE id=?", (sent.message_id, lead_id))
    conn.commit()

    await user_message.reply_text(
        "✅ <b>Запит успішно відправлено рієлтору!</b>\n\n"
        "📞 Рієлтор звʼяжеться з вами протягом <b>24–48 годин</b>.\n\n"
        "🏡 Долучайтесь до нашої групи з актуальними пропозиціями житла в Братиславі:\n"
        f"{GROUP_INVITE_LINK}",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=False,
        reply_markup=ReplyKeyboardRemove(),
    )

    reset_user(u["user_id"])


# =========================
# STATS (розділення Оренда/Купівля)
# =========================
def render_stats(days: int, deal_filter: str) -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cur.execute(
        """
        SELECT property, status_key, COUNT(*)
        FROM leads
        WHERE created_at >= ?
          AND deal = ?
        GROUP BY property, status_key
        """,
        (cutoff.isoformat(), deal_filter),
    )
    rows = cur.fetchall()

    title = f"📊 <b>Статистика ({deal_filter}) за {days} дн.</b>"

    if not rows:
        return f"{title}\n\nНемає заявок."

    prop_tot = {}
    status_tot = {k: 0 for k in STATUS_LABEL.keys()}
    prop_status = {}

    for prop, st, cnt in rows:
        prop = prop or "(невідомо)"
        st = st or "searching"
        cnt = int(cnt)

        prop_tot[prop] = prop_tot.get(prop, 0) + cnt
        status_tot[st] = status_tot.get(st, 0) + cnt

        prop_status.setdefault(prop, {})
        prop_status[prop][st] = prop_status[prop].get(st, 0) + cnt

    total = sum(prop_tot.values())
    active = status_tot.get("searching", 0) + status_tot.get("reserved", 0)

    lines = [
        title,
        "",
        f"🧾 <b>Всього:</b> {total}",
        f"🟡🟢 <b>Активних:</b> {active}",
        "",
        "🏡 <b>По категоріях (тип житла):</b>",
    ]

    for p, c in sorted(prop_tot.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"• {p}: <b>{c}</b>")

    lines.append("")
    lines.append("📌 <b>По статусах:</b>")
    for st in ["searching", "reserved", "self_found", "other_agent", "not_searching", "closed"]:
        lines.append(f"• {STATUS_LABEL[st]}: <b>{status_tot.get(st, 0)}</b>")

    lines.append("")
    lines.append("🧩 <b>Детально (категорія → статус):</b>")
    for p, _ in sorted(prop_tot.items(), key=lambda x: (-x[1], x[0])):
        parts = []
        st_map = prop_status.get(p, {})
        for st in ["searching", "reserved", "self_found", "other_agent", "not_searching", "closed"]:
            if st_map.get(st, 0):
                parts.append(f"{STATUS_LABEL[st]} {st_map[st]}")
        lines.append(f"• <b>{p}</b>: " + (", ".join(parts) if parts else "—"))

    return "\n".join(lines)


async def stats_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🏠 Оренда", callback_data="statsdeal:Оренда")],
            [InlineKeyboardButton("🏡 Купівля", callback_data="statsdeal:Купівля")],
        ]
    )
    await update.message.reply_text("📊 Оберіть тип статистики:", reply_markup=kb)


async def stats_deal_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id not in ADMIN_IDS:
        return

    try:
        deal = q.data.split(":", 1)[1]
    except Exception:
        return

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📊 Сьогодні", callback_data=f"stats:{deal}:1")],
            [InlineKeyboardButton("📊 Тиждень", callback_data=f"stats:{deal}:7")],
            [InlineKeyboardButton("📊 Місяць", callback_data=f"stats:{deal}:30")],
        ]
    )
    await q.message.reply_text(f"📊 Оберіть період статистики ({deal}):", reply_markup=kb)


async def stats_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id not in ADMIN_IDS:
        return

    # stats:<deal>:<days>
    try:
        _, deal, days_s = q.data.split(":")
        days = int(days_s)
    except Exception:
        return

    await q.message.reply_text(render_stats(days, deal), parse_mode=ParseMode.HTML)


# =========================
# COMMANDS
# =========================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = ctx.args or []
    admin_test = is_admin(uid) and len(args) > 0 and args[0].lower() == "test"

    if not admin_test and has_active_lead(uid):
        await update.message.reply_text(
            "⚠️ У вас вже є активна заявка і вона опрацьовується.\n"
            "Будь ласка, дочекайтесь її вирішення."
        )
        return

    if (not admin_test) and (not is_admin(uid)) and has_recent_lead(uid, hours=COOLDOWN_HOURS):
        await update.message.reply_text(
            f"⏳ Ви вже подавали заявку протягом останніх {COOLDOWN_HOURS} годин.\n"
            "Спробуйте пізніше."
        )
        return

    reset_user(uid)
    ensure_user(uid)

    users[uid]["tg"] = tg_display(update.effective_user)
    users[uid]["tg_fullname"] = update.effective_user.full_name or ""
    users[uid]["user_id"] = uid

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🏠 Оренда", callback_data="deal_rent")],
            [InlineKeyboardButton("🏡 Купівля", callback_data="deal_buy")],
        ]
    )
    await update.message.reply_text("👋 Вітаємо!\nЩо вас цікавить?", reply_markup=kb)


async def reset_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    reset_user(update.effective_user.id)
    await update.message.reply_text("🔄 Анкету скинуто. Натисніть /start щоб почати заново.")


async def admin_reset_me(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("⛔ Доступ тільки для адміна.")
        return
    old = "1970-01-01T00:00:00+00:00"
    cur.execute("UPDATE leads SET status_key='closed', created_at=? WHERE user_id=?", (old, uid))
    conn.commit()
    await update.message.reply_text("✅ Скинуто. Можеш тестити /start або /start test.")


# =========================
# CALLBACKS (FLOW)
# =========================
async def deal_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    ensure_user(uid)
    u = users[uid]

    if q.data == "deal_rent":
        u["deal"] = "Оренда"
        u["step"] = "property"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=cb)] for (t, cb) in PROPERTY_BUTTONS])
        await q.message.reply_text("1️⃣ 🏡 Який тип житла вас цікавить?", reply_markup=kb)
        return

    u["deal"] = "Купівля"
    u["step"] = "buy_property"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=cb)] for (t, cb) in BUY_PROPERTY_BUTTONS])
    await q.message.reply_text("1️⃣ 🏠 Яку нерухомість шукаєте для купівлі?", reply_markup=kb)


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

    u["property"] = PROPERTY_VALUE.get(q.data, q.data)
    u["step"] = "city"
    await q.message.reply_text("2️⃣ 📍 В якому місті шукаєте житло?")


async def buy_property_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = users.get(uid)
    if not u:
        return

    if q.data == "buyprop_custom":
        u["step"] = "buy_property_text"
        await q.message.reply_text("✍️ Напишіть, яку нерухомість шукаєте для купівлі:")
        return

    u["property"] = BUY_PROPERTY_VALUE.get(q.data, q.data)
    u["step"] = "buy_details"
    await q.message.reply_text("2️⃣ ✨ Напишіть ваші очікування/уявлення та деталі нерухомості:")


async def buy_finance_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = users.get(uid)
    if not u:
        return

    if q.data == "buyfin_custom":
        u["step"] = "buy_finance_text"
        await q.message.reply_text("✍️ Напишіть, як плануєте вирішувати фінансування:")
        return

    u["job"] = BUY_FINANCE_VALUE.get(q.data, q.data)
    u["step"] = "buy_when"
    await q.message.reply_text("6️⃣ 📅 Коли орієнтовно хотіли б купити цю нерухомість?")


async def parking_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = users.get(uid)
    if not u:
        return

    u["parking"] = PARKING_MAP.get(q.data, "Пізніше")
    u["step"] = "move_in"
    await q.message.reply_text("🔟 📅 Яка найкраща дата для вашого заїзду?")


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

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💻 Онлайн", callback_data="view_online")],
            [InlineKeyboardButton("🚶 Фізичний", callback_data="view_offline")],
            [InlineKeyboardButton("🔁 Обидва варіанти", callback_data="view_both")],
        ]
    )
    await q.message.reply_text("1️⃣5️⃣ 👀 Який формат огляду вам підходить?", reply_markup=kb)


async def view_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = users.get(uid)
    if not u:
        return

    u["view_format"] = VIEW_MAP.get(q.data, "—")
    await ask_contact(q.message, u)


async def confirm_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = users.get(uid)
    if not u:
        return

    if q.data == "confirm_no":
        reset_user(uid)
        await q.message.reply_text("❌ Запит скасовано. Натисніть /start щоб почати знову.")
        return

    # confirm_yes
    if u.get("deal") == "Оренда":
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("✅ Так", callback_data="terms_yes")],
                [InlineKeyboardButton("❌ Ні", callback_data="terms_no")],
            ]
        )
        await q.message.reply_text(
            "ℹ️ <b>Умови співпраці:</b>\n\n"
            "• депозит може дорівнювати в розмірі орендної плати\n"
            "• оплачується повна або часткова комісія рієлтору\n"
            "• можливий подвійний депозит при дітях або тваринах\n\n"
            "<b>Чи погоджуєтесь?</b>",
            reply_markup=kb,
            parse_mode=ParseMode.HTML,
        )
        return

    await finalize_lead_and_notify(ctx, q.message, u)


async def terms_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = users.get(uid)
    if not u:
        return

    if q.data == "terms_no":
        reset_user(uid)
        await q.message.reply_text("❌ Добре, ми не будемо продовжувати роботу.")
        return

    await finalize_lead_and_notify(ctx, q.message, u)


# =========================
# TEXT + CONTACT HANDLERS
# =========================
async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in users:
        return
    u = users[uid]
    step = u.get("step")
    t = (update.message.text or "").strip()

    # Купівля
    if step == "buy_property_text":
        u["property"] = t
        u["step"] = "buy_details"
        await update.message.reply_text("2️⃣ ✨ Напишіть ваші очікування/уявлення та деталі нерухомості:")
        return

    if step == "buy_details":
        u["wishes"] = t
        u["step"] = "buy_where"
        await update.message.reply_text("3️⃣ 📍 Де орієнтовно хочете купити? (місто/район/локація)")
        return

    if step == "buy_where":
        u["city"] = t
        u["step"] = "buy_price"
        await update.message.reply_text("4️⃣ 💶 На яку ціну нерухомості орієнтуєтесь? (може бути від–до)")
        return

    if step == "buy_price":
        u["budget"] = t
        u["step"] = "buy_finance"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(x, callback_data=cb)] for (x, cb) in BUY_FINANCE_BUTTONS])
        await update.message.reply_text(
            "5️⃣ 💳 Як хочете вирішувати фінансування?\n(Маємо фахівців у фінансовому секторі)",
            reply_markup=kb,
        )
        return

    if step == "buy_finance_text":
        u["job"] = t
        u["step"] = "buy_when"
        await update.message.reply_text("6️⃣ 📅 Коли орієнтовно хотіли б купити цю нерухомість?")
        return

    if step == "buy_when":
        u["move_in"] = t
        u["step"] = "buy_viewings"
        await update.message.reply_text("7️⃣ ⏰ Як ви доступні для оглядів? (дні/час)")
        return

    if step == "buy_viewings":
        u["view_time"] = t
        u.setdefault("district", "—")
        u.setdefault("for_whom", "—")
        u.setdefault("children", "—")
        u.setdefault("pets", "—")
        u.setdefault("parking", "—")
        u.setdefault("location", "—")
        u.setdefault("view_format", "—")
        await ask_contact(update.message, u)
        return

    # Оренда
    if step == "property_text":
        u["property"] = t
        u["step"] = "city"
        await update.message.reply_text("2️⃣ 📍 В якому місті шукаєте житло?")
        return

    if step == "city":
        u["city"] = t
        u["step"] = "district"
        await update.message.reply_text("3️⃣ 🗺 Який район?")
        return

    if step == "district":
        u["district"] = t
        u["step"] = "for_whom"
        await update.message.reply_text("4️⃣ 👥 Розпишіть, для кого шукаєте житло:")
        return

    if step == "for_whom":
        u["for_whom"] = t
        u["step"] = "job"
        await update.message.reply_text("5️⃣ 💼 Чим ви займаєтесь? (діяльність):")
        return

   if step == "job":
    u["job"] = t
    u["step"] = "people_count"

    await update.message.reply_text(
        "👥 Скільки осіб буде проживати в житлі?"
    )
    return
        await update.message.reply_text("6️⃣ 🧒 Чи маєте дітей? Якщо так — вік та стать. Якщо ні — «Ні».")
        return
if step == "people_count":
    u["people_count"] = t
    u["step"] = "slovakia_docs"

    await update.message.reply_text(
        "📄 Які документи маєте в Словаччині?"
    )
    return

if step == "slovakia_docs":
    u["slovakia_docs"] = t
    u["step"] = "slovakia_time"

    await update.message.reply_text(
        "🇸🇰 Як довго проживаєте в Словаччині?"
    )
    return

if step == "slovakia_time":
    u["slovakia_time"] = t
    u["step"] = "language_owner"

    await update.message.reply_text(
        "🗣 Якою мовою можете спілкуватися з власником після підписання договору?"
    )
    return

if step == "language_owner":
    u["language_owner"] = t
    u["step"] = "children"

    await update.message.reply_text(
        "🧒 Чи маєте дітей? Якщо так — вік та стать. Якщо ні — Ні."
    )
    return
    
    if step == "children":
        u["children"] = t
        u["step"] = "pets"
        await update.message.reply_text("7️⃣ 🐾 Чи маєте тваринок? Якщо так — які. Якщо ні — «Ні».")
        return

    if step == "pets":
    u["pets"] = t
    u["step"] = "registration"

    await update.message.reply_text(
        "📝 Чи потрібна прописка?"
    )
    return
       if step == "registration":
    u["registration"] = t
    u["step"] = "parking"

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Так", callback_data="park_yes")],
            [InlineKeyboardButton("Ні", callback_data="park_no")],
            [InlineKeyboardButton("Пізніше", callback_data="park_later")],
        ]
    )

    await update.message.reply_text(
        "🚗 Чи потрібне паркування?",
        reply_markup=kb
    )
    return

    if step == "move_in":
        u["move_in"] = t
        u["step"] = "budget"
        await update.message.reply_text("1️⃣1️⃣ 💶 Який бюджет на оренду в місяць (від–до €)?")
        return

    if step == "budget":
        u["budget"] = t
        u["step"] = "view_time"
        await update.message.reply_text("1️⃣2️⃣ ⏰ Як зазвичай ви доступні для оглядів? (дні/час)")
        return

    if step == "view_time":
        u["view_time"] = t
        u["step"] = "wishes"
        await update.message.reply_text("1️⃣3️⃣ ✨ Напишіть особливі побажання на житло:")
        return

    if step == "wishes":
        u["wishes"] = t
        u["step"] = "location"
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🇺🇦 В Україні", callback_data="loc_ua")],
                [InlineKeyboardButton("🇸🇰 В Словаччині", callback_data="loc_sk")],
                [InlineKeyboardButton("✍️ Інша країна", callback_data="loc_custom")],
            ]
        )
        await update.message.reply_text("1️⃣4️⃣ 🌍 Де ви зараз знаходитесь?", reply_markup=kb)
        return

    if step == "custom_location":
        u["location"] = t
        u["step"] = "view_format"
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("💻 Онлайн", callback_data="view_online")],
                [InlineKeyboardButton("🚶 Фізичний", callback_data="view_offline")],
                [InlineKeyboardButton("🔁 Обидва варіанти", callback_data="view_both")],
            ]
        )
        await update.message.reply_text("1️⃣5️⃣ 👀 Який формат огляду вам підходить?", reply_markup=kb)
        return

    # спільне: телефон/ім'я/підтвердження
    if step == "phone":
        if not PHONE_RE.match(t):
            await update.message.reply_text(
                "⚠️ Не схоже на номер.\nВведіть у форматі +421901234567 або натисніть кнопку «Поділитись контактом»."
            )
            return
u["phone"] = normalize_phone(t)
u["step"] = "email"

await update.message.reply_text(
    "📧 Вкажіть email або напишіть Ні"
)
return

if step == "email":
    u["email"] = t
    u["step"] = "name"

    await update.message.reply_text(
        "👤 Як до вас можемо звертатись? (Імʼя та прізвище)"
    )
    return

u["step"] = "name"
        await update.message.reply_text("👤 Як до вас можемо звертатись? (Імʼя/Прізвище)", reply_markup=ReplyKeyboardRemove())
        return

    if step == "name":
        u["name"] = t
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("✅ Так, вірно", callback_data="confirm_yes")],
                [InlineKeyboardButton("❌ Ні, скасувати", callback_data="confirm_no")],
            ]
        )
        preview = build_summary_html(u, req_id=0, status_key="searching").replace("Запит №0", "Перевірте дані")
        await update.message.reply_text(preview + "\n<b>Все вірно?</b>", parse_mode=ParseMode.HTML, reply_markup=kb)
        return


async def contact_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = users.get(uid)
    if not u or u.get("step") != "phone":
        return
    if update.message.contact and update.message.contact.phone_number:
        u["phone"] = normalize_phone(update.message.contact.phone_number)
        u["step"] = "name"
        await update.message.reply_text("👤 Як до вас можемо звертатись? (Імʼя/Прізвище)", reply_markup=ReplyKeyboardRemove())


# =========================
# STATUS CALLBACK (GROUP)
# =========================
async def status_change_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.message.chat_id != ADMIN_GROUP_ID:
        return

    try:
        _, lead_id_s, new_key = q.data.split(":")
        lead_id = int(lead_id_s)
    except Exception:
        return

    if new_key not in STATUS_LABEL:
        return

    cur.execute("UPDATE leads SET status_key=? WHERE id=?", (new_key, lead_id))
    conn.commit()

    cur.execute(
        """
        SELECT req_id, username, tg_fullname, deal, property, city, district, for_whom, job,
               children, pets, parking, move_in, budget, view_time, wishes, location, view_format,
               phone, name, group_message_id
        FROM leads
        WHERE id=?
        """,
        (lead_id,),
    )
    row = cur.fetchone()
    if not row:
        return

    (
        req_id, username, tg_fullname, deal, prop, city, district, for_whom, job,
        children, pets, parking, move_in, budget, view_time, wishes, location, view_format,
        phone, name, group_message_id
    ) = row

    temp_u = {
        "tg": username or "—",
        "tg_fullname": tg_fullname or "",
        "deal": deal or "",
        "property": prop or "",
        "city": city or "",
        "district": district or "",
        "for_whom": for_whom or "",
        "job": job or "",
        "children": children or "",
        "pets": pets or "",
        "parking": parking or "",
        "move_in": move_in or "",
        "budget": budget or "",
        "view_time": view_time or "",
        "wishes": wishes or "",
        "location": location or "",
        "view_format": view_format or "",
        "phone": phone or "",
        "name": name or "",
    }

    new_text = build_summary_html(temp_u, req_id=req_id, status_key=new_key)

    try:
        await ctx.bot.edit_message_text(
            chat_id=ADMIN_GROUP_ID,
            message_id=group_message_id or q.message.message_id,
            text=new_text,
            parse_mode=ParseMode.HTML,
            reply_markup=status_keyboard(lead_id),
            disable_web_page_preview=True,
        )
    except Exception:
        try:
            await ctx.bot.edit_message_reply_markup(
                chat_id=ADMIN_GROUP_ID,
                message_id=group_message_id or q.message.message_id,
                reply_markup=status_keyboard(lead_id),
            )
        except Exception:
            pass


# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(CommandHandler("admin_reset_me", admin_reset_me))
    app.add_handler(CommandHandler("stats", stats_menu))

    # stats callbacks
    app.add_handler(CallbackQueryHandler(stats_deal_callback, pattern=r"^statsdeal:"))
    app.add_handler(CallbackQueryHandler(stats_callback, pattern=r"^stats:"))

    # flow callbacks
    app.add_handler(CallbackQueryHandler(deal_handler, pattern=r"^deal_"))
    app.add_handler(CallbackQueryHandler(property_handler, pattern=r"^prop_"))
    app.add_handler(CallbackQueryHandler(buy_property_handler, pattern=r"^buyprop_"))
    app.add_handler(CallbackQueryHandler(buy_finance_handler, pattern=r"^buyfin_"))
    app.add_handler(CallbackQueryHandler(parking_handler, pattern=r"^park_"))
    app.add_handler(CallbackQueryHandler(location_handler, pattern=r"^loc_"))
    app.add_handler(CallbackQueryHandler(view_handler, pattern=r"^view_"))
    app.add_handler(CallbackQueryHandler(confirm_handler, pattern=r"^confirm_"))
    app.add_handler(CallbackQueryHandler(terms_handler, pattern=r"^terms_"))

    # group status buttons
    app.add_handler(CallbackQueryHandler(status_change_handler, pattern=r"^status:"))

    # messages
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
