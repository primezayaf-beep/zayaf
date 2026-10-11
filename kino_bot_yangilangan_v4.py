
import os
import asyncio
import logging
import re
import json
import base64
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from html import escape, unescape

import aiosqlite
from dotenv import load_dotenv
from aiogram import BaseMiddleware, Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    BotCommand, BotCommandScopeAllPrivateChats, InputFile, FSInputFile, ChatJoinRequest
)
from aiogram.types import InlineKeyboardButton as TelegramInlineKeyboardButton
from aiogram.client.default import Default
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
import secrets
import urllib.request
import urllib.error

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "@Avex_films_bot")
OWNER_ID = int(os.getenv("OWNER_ID", os.getenv("ADMIN_ID", "0")))
ADMIN_ID = OWNER_ID

def parse_admin_ids(raw_value):
    ids = set()
    if not raw_value:
        return ids
    for part in str(raw_value).replace(" ", "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            continue
    return ids

ADMIN_IDS = parse_admin_ids(os.getenv("ADMIN_IDS", ""))
ADMIN_IDS.add(OWNER_ID)
AI_HASH = os.getenv("AI_HASH", "")
DB = os.getenv("DB_PATH", "kino_bot.db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-5.6-luna")
AI_STICKER_FILE_ID = os.getenv("AI_STICKER_FILE_ID", "")
PREVIEW_SECONDS = int(os.getenv("PREVIEW_SECONDS", "5"))
AI_FRAME_COUNT = int(os.getenv("AI_FRAME_COUNT", "24"))
WEB_HOST=os.getenv("WEB_HOST","0.0.0.0")
WEB_PORT=int(os.getenv("WEB_PORT","8080"))
WEB_OWNER_KEY=os.getenv("WEB_OWNER_KEY","")
WEB_ADMIN_KEY=os.getenv("WEB_ADMIN_KEY","")
MAX_UPLOAD_BYTES=int(os.getenv("MAX_UPLOAD_BYTES",str(500*1024**3)))
MAX_REQUIRED_CHANNELS = 10

if not BOT_TOKEN or not OWNER_ID:
    raise RuntimeError("BOT_TOKEN va OWNER_ID .env faylida bo'lishi kerak.")

logging.basicConfig(level=logging.INFO)
CUSTOM_EMOJI_IDS = {}
TELEGRAM_HTML_TAG = re.compile(
    r"</?(?:b|strong|i|em|u|ins|s|strike|del|a|code|pre|tg-spoiler|span|blockquote|tg-emoji)"
    r"(?:\s+[^<>]*)?\s*/?>",
    re.IGNORECASE,
)


def InlineKeyboardButton(*, text, **kwargs):
    kwargs.setdefault("style", "success")
    return TelegramInlineKeyboardButton(text=text, **kwargs)


def custom_emoji_text(text):
    if not CUSTOM_EMOJI_IDS:
        return text
    emoji_pattern = re.compile(
        "|".join(re.escape(emoji) for emoji in sorted(CUSTOM_EMOJI_IDS, key=len, reverse=True))
    )
    parts = re.split(r"(<[^>]*>)", text)
    for index, part in enumerate(parts):
        if index % 2 and TELEGRAM_HTML_TAG.fullmatch(part):
            continue
        safe_text = escape(unescape(part), quote=False)
        parts[index] = emoji_pattern.sub(
            lambda match: (
                f'<tg-emoji emoji-id="{CUSTOM_EMOJI_IDS[match.group(0)]}">'
                f'{match.group(0)}</tg-emoji>'
            ),
            safe_text,
        )
    return "".join(parts)


def custom_emoji_method(method):
    for text_field, entities_field in (("text", "entities"), ("caption", "caption_entities")):
        text = getattr(method, text_field, None)
        if not isinstance(text, str) or getattr(method, entities_field, None):
            continue
        parse_mode = getattr(method, "parse_mode", None)
        if parse_mode not in (None, "HTML") and not isinstance(parse_mode, Default):
            continue
        transformed = custom_emoji_text(text)
        if transformed != text:
            return method.model_copy(update={text_field: transformed, "parse_mode": "HTML"})
    return method


class CustomEmojiSession(AiohttpSession):
    async def make_request(self, bot, method, timeout=None):
        return await super().make_request(bot, custom_emoji_method(method), timeout)


bot = Bot(BOT_TOKEN, session=CustomEmojiSession())
dp = Dispatcher(storage=MemoryStorage())


class PrivateChatOnlyMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message) and event.chat.type != "private":
            return None
        if (
            isinstance(event, CallbackQuery)
            and event.message is not None
            and event.message.chat.type != "private"
        ):
            await event.answer()
            return None
        return await handler(event, data)


dp.message.outer_middleware(PrivateChatOnlyMiddleware())
dp.callback_query.outer_middleware(PrivateChatOnlyMiddleware())

# ============================================================
# TRANSLATIONS
# ============================================================
T = {
"uz": {
"welcome":"🎬 <b>Kino botga xush kelibsiz!</b>\n\n🔢 Kino kodini yuboring.",
"choose_lang":"🌐 <b>Tilni tanlang:</b>",
"lang_saved":"✅ Til saqlandi.",
"settings":"⚙️ <b>Sozlamalar</b>",
"lang":"🌐 Tilni o'zgartirish",
"help":"🆘 Yordam",
"support_sent":"✅ Murojaatingiz adminga yuborildi.",
"no_access":"⛔ Sizda bu bo'lim uchun ruxsat yo'q.",
"not_admin":"⛔ Siz admin emassiz.",
"banned":"🚫 Siz botdan bloklangansiz.",
"need_sub":"🔐 <b>Botdan foydalanish uchun quyidagi kanallar/guruhlarga a'zo bo'ling.</b>",
"check":"✅ Obunani tekshirish",
"sub_ok":"✅ Obuna tasdiqlandi!",
"sub_no":"❌ Hali barcha kanallarga a'zo emassiz.",
"movie_code":"🔢 Kino kodini yuboring.",
"not_found":"❌ Bu kod bo'yicha kino topilmadi.",
"vip":"💎 VIP Tarif",
"vip_active":"💎 VIP faol",
"vip_off":"💎 VIP faol emas",
"vip_required":"🔒 Bu kino faqat VIP a’zolar uchun. Siz VIP tarifga a’zo bo‘lmagansiz.",
},
"ru": {
"welcome":"🎬 <b>Добро пожаловать в кино-бот!</b>\n\n🔢 Отправьте код фильма.",
"choose_lang":"🌐 <b>Выберите язык:</b>",
"lang_saved":"✅ Язык сохранён.",
"settings":"⚙️ <b>Настройки</b>",
"lang":"🌐 Изменить язык",
"help":"🆘 Помощь",
"support_sent":"✅ Ваше обращение отправлено администратору.",
"no_access":"⛔ У вас нет доступа к этому разделу.",
"not_admin":"⛔ Вы не администратор.",
"banned":"🚫 Вы заблокированы в боте.",
"need_sub":"🔐 <b>Для использования бота подпишитесь на следующие каналы/группы.</b>",
"check":"✅ Проверить подписку",
"sub_ok":"✅ Подписка подтверждена!",
"sub_no":"❌ Вы ещё не подписались на все каналы.",
"movie_code":"🔢 Отправьте код фильма.",
"not_found":"❌ Фильм с таким кодом не найден.",
"vip":"💎 VIP Тариф",
"vip_active":"💎 VIP активен",
"vip_off":"💎 VIP не активен",
"vip_required":"🔒 Этот фильм доступен только VIP-пользователям. У вас нет активного VIP-тарифа.",
},
"en": {
"welcome":"🎬 <b>Welcome to the movie bot!</b>\n\n🔢 Send the movie code.",
"choose_lang":"🌐 <b>Choose a language:</b>",
"lang_saved":"✅ Language saved.",
"settings":"⚙️ <b>Settings</b>",
"lang":"🌐 Change language",
"help":"🆘 Help",
"support_sent":"✅ Your support request was sent to the administrator.",
"no_access":"⛔ You don't have permission for this section.",
"not_admin":"⛔ You are not an administrator.",
"banned":"🚫 You are blocked from this bot.",
"need_sub":"🔐 <b>Subscribe to the following channels/groups to use the bot.</b>",
"check":"✅ Check subscription",
"sub_ok":"✅ Subscription confirmed!",
"sub_no":"❌ You haven't joined all required channels yet.",
"movie_code":"🔢 Send the movie code.",
"not_found":"❌ No movie was found for this code.",
"vip":"💎 VIP Plan",
"vip_active":"💎 VIP active",
"vip_off":"💎 VIP inactive",
"vip_required":"🔒 This movie is available to VIP members only. You do not have an active VIP plan.",
}}

def tr(lang, key):
    return T.get(lang, T["uz"]).get(key, T["uz"].get(key, key))


def success_text(text):
    return f"✅ <b>{text}</b>"


async def get_lang(uid):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT language FROM users WHERE id=?", (uid,))
        row = await cur.fetchone()
    return row[0] if row and row[0] in T else "uz"

# ============================================================
# DATABASE
# ============================================================
async def db_init():
    async with aiosqlite.connect(DB) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY, username TEXT DEFAULT '', full_name TEXT DEFAULT '',
            joined_at TEXT, last_active TEXT, banned INTEGER DEFAULT 0,
            ban_reason TEXT DEFAULT '', language TEXT DEFAULT 'uz',
            vip_until TEXT DEFAULT NULL, notify_movies INTEGER DEFAULT 1,
            notify_episodes INTEGER DEFAULT 1, notify_favorites INTEGER DEFAULT 1,
            notify_vip INTEGER DEFAULT 1, notify_announcements INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS admins(
            user_id INTEGER PRIMARY KEY,
            can_movies INTEGER DEFAULT 0, can_users INTEGER DEFAULT 0,
            can_broadcast INTEGER DEFAULT 0, can_channels INTEGER DEFAULT 0,
            can_stats INTEGER DEFAULT 0, can_admins INTEGER DEFAULT 0,
            can_vip INTEGER DEFAULT 0, can_support INTEGER DEFAULT 0,
            can_logs INTEGER DEFAULT 0, added_at TEXT
        );
        CREATE TABLE IF NOT EXISTS channels(
            id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT UNIQUE NOT NULL,
            title TEXT DEFAULT '', username TEXT DEFAULT '', invite_link TEXT DEFAULT '',
            kind TEXT DEFAULT 'public', required INTEGER DEFAULT 1, added_at TEXT
        );
        CREATE TABLE IF NOT EXISTS movies(
            id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL, description TEXT DEFAULT '', genre TEXT DEFAULT '',
            year TEXT DEFAULT '', media_type TEXT NOT NULL, file_id TEXT NOT NULL,
            views INTEGER DEFAULT 0, vip_only INTEGER DEFAULT 0, access_mode TEXT DEFAULT 'all', created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS episodes(
            id INTEGER PRIMARY KEY AUTOINCREMENT, movie_id INTEGER NOT NULL,
            episode_no INTEGER NOT NULL, title TEXT DEFAULT '', media_type TEXT NOT NULL,
            file_id TEXT NOT NULL, views INTEGER DEFAULT 0, created_at TEXT,
            UNIQUE(movie_id,episode_no)
        );
        CREATE TABLE IF NOT EXISTS ratings(
            user_id INTEGER NOT NULL, movie_id INTEGER NOT NULL, rating INTEGER NOT NULL,
            UNIQUE(user_id,movie_id)
        );
        CREATE TABLE IF NOT EXISTS favorites(
            user_id INTEGER NOT NULL, movie_id INTEGER NOT NULL,
            UNIQUE(user_id,movie_id)
        );
        CREATE TABLE IF NOT EXISTS support_tickets(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT,
            status TEXT DEFAULT 'open', created_at TEXT, answered_at TEXT
        );
        CREATE TABLE IF NOT EXISTS admin_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER, action TEXT,
            details TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY, value TEXT
        );
        CREATE TABLE IF NOT EXISTS vip_plans(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, days INTEGER,
            price INTEGER, active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS payment_methods(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, details TEXT,
            active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS payments(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            plan_id INTEGER, amount INTEGER, method_id INTEGER,
            receipt_file_id TEXT, receipt_type TEXT, status TEXT DEFAULT 'pending',
            reason TEXT DEFAULT '', created_at TEXT, reviewed_at TEXT,
            reviewed_by INTEGER
        );
        CREATE TABLE IF NOT EXISTS join_requests(
            user_id INTEGER NOT NULL, chat_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending', created_at TEXT,
            PRIMARY KEY(user_id,chat_id)
        );
        CREATE TABLE IF NOT EXISTS movie_access(
            movie_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
            UNIQUE(movie_id,user_id)
        );
        CREATE TABLE IF NOT EXISTS movie_watch_history(
            user_id INTEGER NOT NULL, movie_id INTEGER NOT NULL,
            watched_at TEXT, UNIQUE(user_id,movie_id)
        );
        """)
        # Existing databases uchun xavfsiz migratsiyalar.
        cur = await db.execute("PRAGMA table_info(movies)")
        movie_cols = {row[1] for row in await cur.fetchall()}
        if "vip_only" not in movie_cols:
            await db.execute("ALTER TABLE movies ADD COLUMN vip_only INTEGER DEFAULT 0")
        if "access_mode" not in movie_cols:
            await db.execute("ALTER TABLE movies ADD COLUMN access_mode TEXT DEFAULT 'all'")

        cur = await db.execute("PRAGMA table_info(channels)")
        channel_cols = {row[1] for row in await cur.fetchall()}
        if "required" not in channel_cols:
            await db.execute("ALTER TABLE channels ADD COLUMN required INTEGER DEFAULT 1")
        # Referral tizimi butunlay olib tashlandi.
        await db.execute("DROP TABLE IF EXISTS referrals")
        await db.execute("DELETE FROM settings WHERE key IN ('referral_enabled','referral_bonus_days')")

        defaults = {
            "auto_receipt":"off",
            "admin_receipt":"on",
            "maintenance":"off",
            "movie_channel_id":"",
            "movie_channel_username":"",
            "news_channel_id":"",
            "news_channel_link":"",
            "news_channel_title":""
        }
        for k,v in defaults.items():
            await db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",(k,v))

        cur = await db.execute("SELECT value FROM settings WHERE key='donetv_seeded'")
        if await cur.fetchone():
            old_seed = os.getenv("DONETV_CHANNEL", "").strip()
            match = re.search(r"(?:https?://)?t\.me/([A-Za-z0-9_]{5,})/?$", old_seed)
            old_username = match.group(1) if match else old_seed.lstrip("@").strip()
            if re.fullmatch(r"[A-Za-z0-9_]{5,}", old_username):
                await db.execute(
                    "DELETE FROM channels WHERE lower(trim(username, '@'))=?",
                    (old_username.lower(),),
                )
            await db.execute("DELETE FROM settings WHERE key='donetv_seeded'")
        cur = await db.execute("SELECT value FROM settings WHERE key='legacy_channels_cleaned'")
        if not await cur.fetchone():
            await db.execute("""
                DELETE FROM channels
                WHERE lower(trim(username, '@')) IN ('tucosprofit', 'a_toolsx2')
                   OR lower(trim(chat_id, '@')) IN ('tucosprofit', 'a_toolsx2')
                   OR lower(rtrim(trim(invite_link), '/')) IN (
                        'https://t.me/tucosprofit', 'https://t.me/a_toolsx2'
                   )
            """)
            await db.execute(
                "INSERT INTO settings(key,value) VALUES('legacy_channels_cleaned','1')"
            )
        for admin_uid in sorted(ADMIN_IDS):
            await db.execute("""
                INSERT INTO admins(user_id,can_movies,can_users,can_broadcast,can_channels,
                can_stats,can_admins,can_vip,can_support,can_logs,added_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(user_id) DO UPDATE SET can_movies=excluded.can_movies,
                can_users=excluded.can_users,can_broadcast=excluded.can_broadcast,
                can_channels=excluded.can_channels,can_stats=excluded.can_stats,
                can_admins=excluded.can_admins,can_vip=excluded.can_vip,
                can_support=excluded.can_support,can_logs=excluded.can_logs
            """,(admin_uid,1,1,1,1,1,1,1,1,1,datetime.now().isoformat()))
        # Example plans only if database is empty.
        cur = await db.execute("SELECT COUNT(*) FROM vip_plans")
        if (await cur.fetchone())[0] == 0:
            await db.executemany(
                "INSERT INTO vip_plans(name,days,price) VALUES(?,?,?)",
                [("1 kun",1,5000),("7 kun",7,15000),("30 kun",30,30000)]
            )
        await db.commit()

async def save_user(message: Message):
    u=message.from_user; now=datetime.now().isoformat()
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        INSERT INTO users(id,username,full_name,joined_at,last_active)
        VALUES(?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET username=excluded.username,
        full_name=excluded.full_name,last_active=excluded.last_active
        """,(u.id,u.username or "",u.full_name or "",now,now))
        await db.commit()

async def is_banned(uid):
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT banned,ban_reason FROM users WHERE id=?",(uid,))
        r=await cur.fetchone()
    return bool(r and r[0]), (r[1] if r else "")

async def is_vip(uid):
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT vip_until FROM users WHERE id=?",(uid,))
        r=await cur.fetchone()
    if not r or not r[0]: return False
    try: return datetime.fromisoformat(r[0]) > datetime.now()
    except: return False

async def get_setting(k, default=""):
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT value FROM settings WHERE key=?",(k,))
        r=await cur.fetchone()
    return r[0] if r else default

async def set_setting(k,v):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(k,v))
        await db.commit()


def emoji_pack_name(value):
    value = value.strip()
    match = re.fullmatch(r"(?:https?://)?t\.me/addemoji/([A-Za-z0-9_]{1,64})/?", value)
    if match:
        return match.group(1)
    if re.fullmatch(r"[A-Za-z0-9_]{1,64}", value):
        return value
    raise ValueError("Telegram custom emoji to'plami havolasi noto'g'ri.")


async def fetch_custom_emoji_mapping(pack_name):
    sticker_set = await bot.get_sticker_set(pack_name)
    mapping = {}
    for sticker in sticker_set.stickers:
        if sticker.emoji and sticker.custom_emoji_id:
            mapping.setdefault(sticker.emoji, sticker.custom_emoji_id)
    if not mapping:
        raise ValueError("To'plamda ishlatish mumkin bo'lgan custom emoji topilmadi.")
    return mapping


async def log_action(admin_id, action, details=""):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO admin_logs(admin_id,action,details,created_at) VALUES(?,?,?,?)",
                         (admin_id,action,details,datetime.now().isoformat()))
        await db.commit()

PERMS={"movies":"can_movies","users":"can_users","broadcast":"can_broadcast",
       "channels":"can_channels","stats":"can_stats","admins":"can_admins",
       "vip":"can_vip","support":"can_support","logs":"can_logs"}

async def admin_right(uid, perm):
    if uid in ADMIN_IDS:
        return True
    col=PERMS.get(perm)
    if not col: return False
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute(f"SELECT {col} FROM admins WHERE user_id=?",(uid,))
        r=await cur.fetchone()
    return bool(r and r[0])

async def admin_exists(uid):
    if uid in ADMIN_IDS:
        return True
    return await admin_right(uid,"movies") or any(
        [await admin_right(uid,p) for p in PERMS]
    )

# ============================================================
# FSM
# ============================================================
class AddMovie(StatesGroup):
    code=State(); title=State(); description=State(); genre=State(); year=State(); access=State(); preview=State(); selected_users=State(); media=State(); scene=State()
class MovieChannel(StatesGroup):
    chat_id=State(); username=State()
class AddEpisode(StatesGroup):
    code=State(); episode=State(); title=State(); media=State()
class AddChannel(StatesGroup):
    title=State(); link=State()

class BanUser(StatesGroup):
    user_id=State(); reason=State()
class UnbanUser(StatesGroup): user_id=State()
class AddAdmin(StatesGroup): user_id=State(); permissions=State()
class RemoveAdmin(StatesGroup): user_id=State()
class Broadcast(StatesGroup): source=State(); button=State(); confirm=State()
class ForwardBroadcast(StatesGroup): source=State(); confirm=State()
class NewsChannel(StatesGroup): chat_id=State()
class NewsPost(StatesGroup): source=State(); confirm=State()
class Support(StatesGroup): message=State()
class AddPlan(StatesGroup): name=State(); days=State(); price=State()
class AddPaymentMethod(StatesGroup): name=State(); details=State()
class ReceiptReview(StatesGroup): reason=State()

# ============================================================
# KEYBOARDS
# ============================================================
def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha",callback_data="lang:uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский",callback_data="lang:ru")],
        [InlineKeyboardButton(text="🇬🇧 English",callback_data="lang:en")],
    ])

def user_kb(lang="uz"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Profil",callback_data="profile"),
         InlineKeyboardButton(text="⭐ Reyting",callback_data="ranking"),
         InlineKeyboardButton(text="💚 Sevimlilar",callback_data="favorites")],
        [InlineKeyboardButton(text="🔔 Xabarnomalar",callback_data="notifications"),
         InlineKeyboardButton(text="🤖 AI qidiruv",callback_data="ai_web_start"),
         InlineKeyboardButton(text="⚙️ Sozlamalar",callback_data="settings")],
        [InlineKeyboardButton(text="🆘 Support",callback_data="support_start")],
    ])

def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Kino",callback_data="manage_movies"),
         InlineKeyboardButton(text="📺 Serial",callback_data="add_episode"),
         InlineKeyboardButton(text="📢 Obuna",callback_data="channels_menu")],
        [InlineKeyboardButton(text="👑 Adminlar",callback_data="admins_menu"),
         InlineKeyboardButton(text="👥 Userlar",callback_data="users_menu"),
         InlineKeyboardButton(text="📨 Xabar",callback_data="broadcast_start")],
        [InlineKeyboardButton(text="📰 Yangiliklar",callback_data="news_menu")],
        [InlineKeyboardButton(text="↪️ Forward",callback_data="forward_broadcast_start"),
         InlineKeyboardButton(text="🤖 AI / Web",callback_data="ai_web_admin"),
         InlineKeyboardButton(text="📝 Log",callback_data="admin_logs")],
        [InlineKeyboardButton(text="📊 Statistika",callback_data="advanced_stats"),
         InlineKeyboardButton(text="🆘 Support",callback_data="support_admin")],
    ])

def movie_kb(mid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ 1",callback_data=f"rate:{mid}:1"),
         InlineKeyboardButton(text="⭐ 2",callback_data=f"rate:{mid}:2"),
         InlineKeyboardButton(text="⭐ 3",callback_data=f"rate:{mid}:3"),
         InlineKeyboardButton(text="⭐ 4",callback_data=f"rate:{mid}:4"),
         InlineKeyboardButton(text="⭐ 5",callback_data=f"rate:{mid}:5")],
        [InlineKeyboardButton(text="❤️ Sevimliga",callback_data=f"fav:{mid}")],
        [InlineKeyboardButton(text="📺 Qismlar",callback_data=f"eps:{mid}")]
    ])

# ============================================================
# SUBSCRIPTION
# ============================================================
async def required_channel_count():
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT COUNT(*) FROM channels WHERE COALESCE(required,1)=1")
        return (await cur.fetchone())[0]


async def save_required_channel(chat_id,title,username,invite_link,kind):
    async with aiosqlite.connect(DB) as db:
        await db.execute("BEGIN IMMEDIATE")
        cur=await db.execute("SELECT COUNT(*) FROM channels WHERE COALESCE(required,1)=1")
        if (await cur.fetchone())[0] >= MAX_REQUIRED_CHANNELS:
            await db.rollback()
            return False
        await db.execute(
            "INSERT INTO channels(chat_id,title,username,invite_link,kind,required,added_at) VALUES(?,?,?,?,?,1,?)",
            (chat_id,title,username,invite_link,kind,datetime.now().isoformat()),
        )
        await db.commit()
    return True


async def subscription_kb():
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT id,chat_id,title,username,invite_link,kind FROM channels WHERE COALESCE(required,1)=1 ORDER BY id")
        rows=await cur.fetchall()
    buttons=[]
    for cid,chat_id,title,username,invite,kind in rows:
        url=invite or (f"https://t.me/{username.lstrip('@')}" if username else None)
        if not url:
            try:
                chat=await bot.get_chat(chat_id)
                username=chat.username or username
                kind="public" if username else "private"
                if username:
                    url=f"https://t.me/{username}"
                else:
                    url=(await bot.create_chat_invite_link(chat_id=chat.id)).invite_link
                async with aiosqlite.connect(DB) as db:
                    await db.execute(
                        "UPDATE channels SET title=?,username=?,invite_link=?,kind=? WHERE id=?",
                        (chat.title or title,username or "",url,kind,cid),
                    )
                    await db.commit()
            except TelegramAPIError as e:
                logging.warning("Required chat invite link unavailable for %s: %s",chat_id,e)
            except Exception:
                logging.exception("Could not prepare required chat button for %s",chat_id)
        if url:
            buttons.append([InlineKeyboardButton(text=f"📢 {title or username or cid}",url=url)])
    buttons.append([InlineKeyboardButton(text="✅ Obunani tekshirish",callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def check_subscription(uid):
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT chat_id,title,username,kind FROM channels WHERE COALESCE(required,1)=1")
        channels=await cur.fetchall()
        cur=await db.execute("SELECT chat_id,status FROM join_requests WHERE user_id=?",(uid,))
        reqs={str(r[0]):r[1] for r in await cur.fetchall()}
    missing=[]
    for chat_id,title,username,kind in channels:
        if not str(chat_id or "").strip():
            continue
        try:
            m=await bot.get_chat_member(chat_id=chat_id,user_id=uid)
            if m.status in ("member","administrator","creator"):
                continue
            if kind == "private_request" and reqs.get(str(chat_id)) in ("pending","approved"):
                continue
            if kind == "private" and reqs.get(str(chat_id)) in ("pending","approved"):
                continue
            if m.status in ("left","kicked"):
                missing.append((chat_id,title,username,kind))
        except Exception as e:
            err=str(e).lower()
            if kind in ("private_request","private") and reqs.get(str(chat_id)) in ("pending","approved"):
                continue
            logging.warning("Required chat membership check failed for %s: %s",chat_id,e)
            missing.append((chat_id,title,username,kind))
    return missing

@dp.chat_join_request()
async def handle_join_request(request: ChatJoinRequest):
    try:
        async with aiosqlite.connect(DB) as db:
            await db.execute("INSERT INTO users(id,username,full_name,joined_at,last_active) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET username=excluded.username,full_name=excluded.full_name,last_active=excluded.last_active",
                             (request.from_user.id, request.from_user.username or "", request.from_user.full_name or "", datetime.now().isoformat(), datetime.now().isoformat()))
            await db.execute("INSERT INTO join_requests(user_id,chat_id,status,created_at) VALUES(?,?,?,?) ON CONFLICT(user_id,chat_id) DO UPDATE SET status=excluded.status,created_at=excluded.created_at",
                             (request.from_user.id,str(request.chat.id),"pending",datetime.now().isoformat()))
            await db.commit()
    except Exception as e:
        logging.warning("Join request save failed: %s",e)


async def require_subscription(message):
    if await is_vip(message.from_user.id): return True
    missing=await check_subscription(message.from_user.id)
    if not missing:
        return True
    lang=await get_lang(message.from_user.id)
    await message.answer(tr(lang,"need_sub"),reply_markup=await subscription_kb())
    return False

@dp.callback_query(F.data=="check_sub")
async def check_sub(call):
    missing=await check_subscription(call.from_user.id)
    lang=await get_lang(call.from_user.id)
    if missing: await call.answer(tr(lang,"sub_no"),show_alert=True)
    else:
        await call.answer(success_text(tr(lang,"sub_ok")),show_alert=True)
        await call.message.answer(tr(lang,"movie_code"))

# ============================================================
# LANGUAGE / SETTINGS / NOTIFICATIONS / SUPPORT
# ============================================================
@dp.callback_query(F.data.startswith("lang:"))
async def set_lang(call):
    lang=call.data.split(":")[1]
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET language=? WHERE id=?",(lang,call.from_user.id))
        await db.commit()
    await call.answer(success_text(tr(lang,"lang_saved")))
    await call.message.edit_text(tr(lang,"welcome"),reply_markup=user_kb(lang))

@dp.callback_query(F.data=="settings")
async def settings(call):
    lang=await get_lang(call.from_user.id)
    await call.message.answer(tr(lang,"settings"),reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=tr(lang,"lang"),callback_data="change_lang")],
        [InlineKeyboardButton(text="🔔 Xabarnomalar",callback_data="notifications")],
        [InlineKeyboardButton(text=tr(lang,"help"),callback_data="help")]
    ]))
    await call.answer()

@dp.callback_query(F.data=="change_lang")
async def change_lang(call):
    await call.message.answer("🌐 Tilni tanlang:",reply_markup=lang_kb()); await call.answer()

@dp.callback_query(F.data=="notifications")
async def notifications(call):
    uid=call.from_user.id
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("""SELECT notify_movies,notify_episodes,notify_favorites,
        notify_vip,notify_announcements FROM users WHERE id=?""",(uid,))
        r=await cur.fetchone()
    labels=["🆕 Yangi kino","📺 Yangi qism","❤️ Sevimli serial","💎 VIP muddati","📢 Muhim e'lon"]
    cols=["notify_movies","notify_episodes","notify_favorites","notify_vip","notify_announcements"]
    kb=[]
    for label,col,val in zip(labels,cols,r or [1]*5):
        kb.append([InlineKeyboardButton(text=f"{label}: {'ON 🟢' if val else 'OFF 🔴'}",callback_data=f"toggle_notify:{col}")])
    await call.message.answer("🔔 <b>Xabarnomalar</b>",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await call.answer()

@dp.callback_query(F.data.startswith("toggle_notify:"))
async def toggle_notify(call):
    col=call.data.split(":",1)[1]
    if col not in {"notify_movies","notify_episodes","notify_favorites","notify_vip","notify_announcements"}:
        return await call.answer("❌",show_alert=True)
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute(f"SELECT {col} FROM users WHERE id=?",(call.from_user.id,))
        r=await cur.fetchone(); new=0 if r and r[0] else 1
        await db.execute(f"UPDATE users SET {col}=? WHERE id=?",(new,call.from_user.id)); await db.commit()
    await call.answer("✅ O'zgartirildi"); await notifications(call)

@dp.callback_query(F.data=="help")
async def help_user(call):
    lang=await get_lang(call.from_user.id)
    await call.message.answer(f"{tr(lang,'help')}\n\n📌 Kino kodini yuboring.\n🆘 Muammo bo'lsa Support orqali yozing.")
    await call.answer()

@dp.callback_query(F.data=="support_start")
async def support_start(call,state):
    await state.set_state(Support.message)
    await call.message.answer("🆘 Muammoingizni yozing yoki screenshot yuboring.")
    await call.answer()

@dp.message(Support.message)
async def support_receive(message,state):
    await save_user(message)
    uid=message.from_user.id
    text=message.text or message.caption or "[media]"
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("INSERT INTO support_tickets(user_id,message,created_at) VALUES(?,?,?)",
                             (uid,text,datetime.now().isoformat()))
        tid=cur.lastrowid; await db.commit()
    await bot.send_message(OWNER_ID,f"🆘 <b>Yangi Support #{tid}</b>\n👤 <code>{uid}</code>\n\n{escape(text)}",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                               [InlineKeyboardButton(text="↩️ Javob berish",callback_data=f"support_reply:{uid}:{tid}")],
                               [InlineKeyboardButton(text="✅ Yopish",callback_data=f"support_close:{tid}")]
                           ]))
    lang=await get_lang(uid); await message.answer(tr(lang,"support_sent")); await state.clear()

# ============================================================
# VIP USER + RECEIPTS
# ============================================================
async def vip_plans_kb():
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT id,name,days,price FROM vip_plans WHERE active=1 ORDER BY days")
        rows=await cur.fetchall()
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💎 {n} — {p:,} so'm",callback_data=f"buyvip:{i}")]
        for i,n,d,p in rows
    ])

@dp.callback_query(F.data=="vip_menu")
async def vip_menu(call):
    uid=call.from_user.id
    active=await is_vip(uid)
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT vip_until FROM users WHERE id=?",(uid,)); r=await cur.fetchone()
    status="💎 VIP faol" if active else "💎 VIP faol emas"
    if active: status += f"\n📅 {r[0]}"
    await call.message.answer(f"<b>💎 VIP Tarif</b>\n\n{status}\n\nMuddatni tanlang:",
                              reply_markup=await vip_plans_kb())
    await call.answer()

@dp.callback_query(F.data.startswith("buyvip:"))
async def buy_vip(call):
    pid=int(call.data.split(":")[1])
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT name,days,price FROM vip_plans WHERE id=? AND active=1",(pid,))
        plan=await cur.fetchone()
        cur=await db.execute("SELECT id,name,details FROM payment_methods WHERE active=1 ORDER BY id")
        methods=await cur.fetchall()
    if not plan: return await call.answer("❌ Tarif topilmadi.",show_alert=True)
    name,days,price=plan
    if not methods: return await call.message.answer("💳 Hozircha to'lov usuli sozlanmagan.")
    kb=[[InlineKeyboardButton(text=f"💳 {m[1]}",callback_data=f"paymethod:{pid}:{m[0]}")] for m in methods]
    await call.message.answer(f"💎 <b>{escape(name)}</b>\n📅 {days} kun\n💰 {price:,} so'm\n\nTo'lov usulini tanlang:",
                              reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await call.answer()

@dp.callback_query(F.data.startswith("paymethod:"))
async def paymethod(call):
    _,pid,mid=call.data.split(":"); pid=int(pid); mid=int(mid)
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT name,days,price FROM vip_plans WHERE id=?",(pid,)); p=await cur.fetchone()
        cur=await db.execute("SELECT name,details FROM payment_methods WHERE id=?",(mid,)); m=await cur.fetchone()
    if not p or not m: return await call.answer("❌ Topilmadi.",show_alert=True)
    name,days,price=p; mn,details=m
    await call.message.answer(
        f"💎 <b>{escape(name)}</b>\n📅 {days} kun\n💰 <b>{price:,} so'm</b>\n\n"
        f"💳 <b>{escape(mn)}</b>\n{escape(details)}\n\n"
        "🧾 To'lovni amalga oshirgach, chekni <b>rasm yoki PDF</b> qilib shu botga yuboring.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧾 Chek yuborish",callback_data=f"sendreceipt:{pid}:{mid}")]
        ]))
    await call.answer()

class Receipt(StatesGroup): plan=State(); method=State()

@dp.callback_query(F.data.startswith("sendreceipt:"))
async def receipt_start(call,state):
    _,pid,mid=call.data.split(":")
    await state.update_data(plan_id=int(pid),method_id=int(mid))
    await state.set_state(Receipt.plan)
    await call.message.answer("🧾 Chekni endi rasm yoki PDF qilib yuboring.")
    await call.answer()

@dp.message(Receipt.plan, F.photo)
async def receipt_photo(message,state):
    data=await state.get_data()
    await create_payment(message,data["plan_id"],data["method_id"],message.photo[-1].file_id,"photo")
    await state.clear()

@dp.message(Receipt.plan, F.document)
async def receipt_doc(message,state):
    data=await state.get_data()
    await create_payment(message,data["plan_id"],data["method_id"],message.document.file_id,"document")
    await state.clear()

async def create_payment(message,pid,mid,file_id,file_type):
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT name,days,price FROM vip_plans WHERE id=?",(pid,)); p=await cur.fetchone()
        cur=await db.execute("SELECT name FROM payment_methods WHERE id=? AND active=1",(mid,)); m=await cur.fetchone()
        if not p or not m:
            return await message.answer("❌ Tarif yoki to‘lov usuli topilmadi.")
        cur=await db.execute("""INSERT INTO payments(user_id,plan_id,amount,method_id,receipt_file_id,
        receipt_type,status,created_at) VALUES(?,?,?,?,?,?,?,?)""",
                             (message.from_user.id,pid,p[2],mid,file_id,file_type,"pending",datetime.now().isoformat()))
        payid=cur.lastrowid; await db.commit()
    auto=await get_setting("auto_receipt","off")
    admin_mode=await get_setting("admin_receipt","on")
    # Safe automatic mode: OCR is only a confidence filter; uncertain cases go to admin.
    if auto=="on":
        ok=await receipt_confidence_check(message,p[2])
        if ok:
            await approve_payment(payid,OWNER_ID,auto=True)
            return await message.answer("✅ Chek avtomatik tekshirildi va to'lov tasdiqlandi.\n💎 VIP faollashtirildi.")
    if admin_mode=="on" or auto=="off":
        await send_payment_to_admin(payid,message.from_user.id,p,mid,file_id,file_type)
        return await message.answer("🧾 Chekingiz qabul qilindi. Admin tekshiruviga yuborildi.")
    await message.answer("⚠️ Chekni tekshirishning faol rejimi yo'q. Admin bilan bog'laning.")

async def receipt_confidence_check(message,expected_amount):
    # No bank access: this intentionally does NOT claim that money reached a card.
    # If OCR is installed, it can detect the expected amount from a receipt image.
    # Otherwise it returns False so every uncertain receipt goes to an admin.
    try:
        import pytesseract
        from PIL import Image
        import io
        if not message.photo: return False
        bio=io.BytesIO()
        await bot.download(message.photo[-1],destination=bio)
        bio.seek(0)
        text=pytesseract.image_to_string(Image.open(bio),lang="eng")
        nums=re.findall(r"\d[\d\s,\.]*",text)
        normalized={int(re.sub(r"\D","",x)) for x in nums if re.sub(r"\D","",x)}
        return expected_amount in normalized
    except Exception:
        return False

async def send_payment_to_admin(payid,uid,plan,mid,file_id,file_type):
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT name,details FROM payment_methods WHERE id=?",(mid,)); m=await cur.fetchone()
    caption=f"🧾 <b>VIP to'lov #{payid}</b>\n👤 User: <code>{uid}</code>\n💎 Tarif: {escape(plan[0])}\n📅 {plan[1]} kun\n💰 {plan[2]:,} so'm\n💳 {escape(m[0] if m else '-')}"
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash",callback_data=f"payapprove:{payid}")],
        [InlineKeyboardButton(text="❌ Rad etish",callback_data=f"payreject:{payid}")]
    ])
    if file_type=="photo": await bot.send_photo(OWNER_ID,file_id,caption=caption,reply_markup=kb)
    else: await bot.send_document(OWNER_ID,file_id,caption=caption,reply_markup=kb)

async def approve_payment(payid,admin_id,auto=False):
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("""SELECT user_id,plan_id,status FROM payments WHERE id=?""",(payid,))
        p=await cur.fetchone()
        if not p or p[2]!="pending": return False
        cur=await db.execute("SELECT days FROM vip_plans WHERE id=?",(p[1],)); plan=await cur.fetchone()
        if not plan: return False
        cur=await db.execute("SELECT vip_until FROM users WHERE id=?",(p[0],)); r=await cur.fetchone()
        now=datetime.now()
        try: base=datetime.fromisoformat(r[0]) if r and r[0] else now
        except: base=now
        if base<now: base=now
        until=base+timedelta(days=plan[0])
        await db.execute("UPDATE users SET vip_until=? WHERE id=?",(until.isoformat(),p[0]))
        await db.execute("UPDATE payments SET status='approved',reviewed_at=?,reviewed_by=? WHERE id=?",
                         (now.isoformat(),admin_id,payid))
        await db.commit()
    await log_action(admin_id,"VIP to'lov tasdiqlandi",f"payment={payid}, user={p[0]}, days={plan[0]}")
    await bot.send_message(p[0],f"✅ To'lovingiz tasdiqlandi!\n💎 VIP faollashtirildi.\n📅 {until.strftime('%d.%m.%Y %H:%M')}")
    return True

@dp.callback_query(F.data.startswith("payapprove:"))
async def pay_approve(call):
    if not await admin_right(call.from_user.id,"vip"): return await call.answer("⛔ Ruxsat yo'q",show_alert=True)
    ok=await approve_payment(int(call.data.split(":")[1]),call.from_user.id)
    await call.answer("✅ Tasdiqlandi." if ok else "❌ So'rov topilmadi yoki allaqachon ko'rilgan.",show_alert=True)

@dp.callback_query(F.data.startswith("payreject:"))
async def pay_reject(call):
    if not await admin_right(call.from_user.id,"vip"): return await call.answer("⛔ Ruxsat yo'q",show_alert=True)
    payid=int(call.data.split(":")[1])
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT user_id,status FROM payments WHERE id=?",(payid,)); p=await cur.fetchone()
        if not p or p[1]!="pending": return await call.answer("❌ So'rov topilmadi.",show_alert=True)
        await db.execute("UPDATE payments SET status='rejected',reviewed_at=?,reviewed_by=? WHERE id=?",
                         (datetime.now().isoformat(),call.from_user.id,payid)); await db.commit()
    await log_action(call.from_user.id,"VIP to'lovi rad etildi",f"payment={payid}")
    await bot.send_message(p[0],"❌ To'lov so'rovingiz admin tomonidan rad etildi.")
    await call.answer("❌ Rad etildi.",show_alert=True)

# ============================================================
# VIP ADMIN
# ============================================================
@dp.callback_query(F.data=="vip_admin")
async def vip_admin(call):
    if not await admin_right(call.from_user.id,"vip"): return await call.answer("⛔ Ruxsat yo'q",show_alert=True)
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 VIP narxlari",callback_data="vip_plans")],
        [InlineKeyboardButton(text="💳 To'lov usullari",callback_data="pay_methods")],
        [InlineKeyboardButton(text="🤖 Chek avto tasdiqlash",callback_data="toggle_setting:auto_receipt")],
        [InlineKeyboardButton(text="👨‍💼 Admin tasdiqlashi",callback_data="toggle_setting:admin_receipt")],
        [InlineKeyboardButton(text="🧾 Kutilayotgan to'lovlar",callback_data="pending_payments")],
    ])
    await call.message.answer("💎 <b>VIP boshqaruvi</b>",reply_markup=kb); await call.answer()

@dp.callback_query(F.data.startswith("toggle_setting:"))
async def toggle_setting(call):
    if not await admin_right(call.from_user.id,"vip"): return await call.answer("⛔ Ruxsat yo'q",show_alert=True)
    k=call.data.split(":")[1]; old=await get_setting(k,"off"); new="off" if old=="on" else "on"
    await set_setting(k,new); await log_action(call.from_user.id,"Sozlama o'zgardi",f"{k}={new}")
    await call.answer(f"{k}: {new.upper()}"); await vip_admin(call)

@dp.callback_query(F.data=="vip_plans")
async def vip_plans_admin(call):
    if not await admin_right(call.from_user.id,"vip"): return await call.answer("⛔",show_alert=True)
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT id,name,days,price,active FROM vip_plans ORDER BY days"); rows=await cur.fetchall()
    text="💰 <b>VIP tariflar</b>\n\n"
    for i,n,d,p,a in rows: text+=f"#{i} {escape(n)} — {d} kun — {p:,} so'm — {'ON' if a else 'OFF'}\n"
    buttons=[[InlineKeyboardButton(text="➕ Tarif qo'shish",callback_data="add_vip_plan")]]
    for i,n,d,p,a in rows:
        buttons.append([
            InlineKeyboardButton(text=(f"🔴 O‘chirish #{i}" if a else f"🟢 Yoqish #{i}"),callback_data=f"toggle_vip_plan:{i}"),
            InlineKeyboardButton(text=f"🗑 Tarif #{i}",callback_data=f"delete_vip_plan:{i}")
        ])
    await call.message.answer(text,reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)); await call.answer()

@dp.callback_query(F.data.startswith("toggle_vip_plan:"))
async def toggle_vip_plan(call):
    if not await admin_right(call.from_user.id,"vip"): return await call.answer("⛔",show_alert=True)
    pid=int(call.data.split(":")[1])
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT active FROM vip_plans WHERE id=?",(pid,)); row=await cur.fetchone()
        if not row: return await call.answer("❌ Tarif topilmadi.",show_alert=True)
        new=0 if row[0] else 1
        await db.execute("UPDATE vip_plans SET active=? WHERE id=?",(new,pid)); await db.commit()
    await log_action(call.from_user.id,"VIP tarif holati o‘zgardi",f"plan={pid}, active={new}")
    await call.answer("✅ Tarif yoqildi." if new else "🔴 Tarif o‘chirildi.",show_alert=True)

@dp.callback_query(F.data.startswith("delete_vip_plan:"))
async def delete_vip_plan(call):
    if not await admin_right(call.from_user.id,"vip"): return await call.answer("⛔",show_alert=True)
    pid=int(call.data.split(":")[1])
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT COUNT(*) FROM payments WHERE plan_id=?",(pid,)); used=(await cur.fetchone())[0]
        if used:
            await db.execute("UPDATE vip_plans SET active=0 WHERE id=?",(pid,))
            msg="Tarifda to‘lov tarixi borligi uchun butunlay o‘chirilmadi, OFF qilindi."
        else:
            cur=await db.execute("DELETE FROM vip_plans WHERE id=?",(pid,))
            msg="Tarif o‘chirildi." if cur.rowcount else "Tarif topilmadi."
        await db.commit()
    await log_action(call.from_user.id,"VIP tarif o‘chirildi",f"plan={pid}")
    await call.answer(f"✅ {msg}",show_alert=True)

@dp.callback_query(F.data=="add_vip_plan")
async def add_plan(call,state):
    if not await admin_right(call.from_user.id,"vip"): return await call.answer("⛔",show_alert=True)
    await state.set_state(AddPlan.name); await call.message.answer("💎 Tarif nomi:"); await call.answer()

@dp.message(AddPlan.name)
async def plan_name(message,state):
    await state.update_data(name=message.text.strip()); await state.set_state(AddPlan.days); await message.answer("📅 Necha kun?")

@dp.message(AddPlan.days)
async def plan_days(message,state):
    try: d=int(message.text.strip()); assert d>0
    except: return await message.answer("❌ Musbat son yuboring.")
    await state.update_data(days=d); await state.set_state(AddPlan.price); await message.answer("💰 Narxi (so'm):")

@dp.message(AddPlan.price)
async def plan_price(message,state):
    try: p=int(message.text.strip()); assert p>=0
    except: return await message.answer("❌ Raqam yuboring.")
    data=await state.get_data()
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO vip_plans(name,days,price) VALUES(?,?,?)",(data["name"],data["days"],p)); await db.commit()
    await log_action(message.from_user.id,"VIP tarif qo'shildi",data["name"]); await state.clear(); await message.answer("✅ VIP tarif qo'shildi.")

@dp.callback_query(F.data=="pay_methods")
async def pay_methods(call):
    if not await admin_right(call.from_user.id,"vip"): return await call.answer("⛔",show_alert=True)
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT id,name,details,active FROM payment_methods ORDER BY id"); rows=await cur.fetchall()
    text="💳 <b>To'lov usullari</b>\n\n"
    for i,n,d,a in rows: text+=f"#{i} {escape(n)} — {'ON' if a else 'OFF'}\n{escape(d)}\n\n"
    await call.message.answer(text,reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ To'lov turi qo'shish",callback_data="add_pay_method")]
    ])); await call.answer()

@dp.callback_query(F.data=="add_pay_method")
async def add_pay_method(call,state):
    if not await admin_right(call.from_user.id,"vip"): return await call.answer("⛔",show_alert=True)
    await state.set_state(AddPaymentMethod.name); await call.message.answer("💳 To'lov turi nomi (masalan Click yoki karta):"); await call.answer()

@dp.message(AddPaymentMethod.name)
async def pm_name(message,state):
    await state.update_data(name=message.text.strip()); await state.set_state(AddPaymentMethod.details)
    await message.answer("💳 Karta raqami yoki to'lov tafsilotlarini yuboring:")

@dp.message(AddPaymentMethod.details)
async def pm_details(message,state):
    data=await state.get_data()
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO payment_methods(name,details) VALUES(?,?)",(data["name"],message.text.strip())); await db.commit()
    await log_action(message.from_user.id,"To'lov usuli qo'shildi",data["name"]); await state.clear()
    await message.answer("✅ To'lov usuli qo'shildi.")

@dp.callback_query(F.data=="pending_payments")
async def pending_payments(call):
    if not await admin_right(call.from_user.id,"vip"): return await call.answer("⛔",show_alert=True)
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("""SELECT id,user_id,amount,status,created_at FROM payments
        WHERE status='pending' ORDER BY id DESC LIMIT 50"""); rows=await cur.fetchall()
    text="🧾 <b>Kutilayotgan to'lovlar</b>\n\n"
    for i,u,a,s,c in rows: text+=f"#{i} 👤 <code>{u}</code> 💰 {a:,} so'm\n"
    await call.message.answer(text or "📭 Kutilayotgan to'lov yo'q."); await call.answer()

# ============================================================
# CHANNELS
# ============================================================
@dp.callback_query(F.data=="channels_menu")
async def channels_menu(call):
    if not await admin_right(call.from_user.id,"channels"): return await call.answer("⛔",show_alert=True)
    count=await required_channel_count()
    await call.message.answer(f"📢 <b>Majburiy obuna</b>\n\nMajburiy kanal/guruhlar: {count}/{MAX_REQUIRED_CHANNELS}",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kanal/guruh qo'shish",callback_data="add_channel")],
        [InlineKeyboardButton(text="📋 Barcha kanallar",callback_data="channel_list")],
        [InlineKeyboardButton(text="✅ Majburiy tanlash",callback_data="select_required_channels")],
        [InlineKeyboardButton(text="🗑 O'chirish",callback_data="remove_channel")]
    ])); await call.answer()

@dp.callback_query(F.data=="add_channel")
async def add_channel_start(call,state):
    if not await admin_right(call.from_user.id,"channels"): return await call.answer("⛔",show_alert=True)
    if await required_channel_count() >= MAX_REQUIRED_CHANNELS:
        return await call.answer(f"❌ Eng ko'pi bilan {MAX_REQUIRED_CHANNELS} ta majburiy kanal/guruh qo'shish mumkin.",show_alert=True)
    await state.set_state(AddChannel.title)
    await call.message.answer("📢 Kanal nomini yuboring.\nMasalan: <code>UNIVERS FILIMS</code>")
    await call.answer()

@dp.message(AddChannel.title)
async def add_channel_title(message,state):
    title=message.text.strip()
    if not title: return await message.answer("❌ Kanal nomi bo‘sh bo‘lmasin.")
    await state.update_data(title=title)
    await state.set_state(AddChannel.link)
    await message.answer("🔗 Kanal ID yoki linkini yuboring.\nMasalan: <code>@Univers_Filims</code>, <code>https://t.me/Univers_Filims</code> yoki <code>-1001234567890</code>")

@dp.message(AddChannel.link)
async def add_channel_link(message,state):
    link=message.text.strip()
    d=await state.get_data()
    if await required_channel_count() >= MAX_REQUIRED_CHANNELS:
        await state.clear()
        return await message.answer(f"❌ Eng ko'pi bilan {MAX_REQUIRED_CHANNELS} ta majburiy kanal/guruh qo'shish mumkin.")
    raw_value = link.strip()
    if raw_value.startswith("@"):
        username=raw_value[1:]
        if not re.fullmatch(r"[A-Za-z0-9_]{5,}",username):
            return await message.answer("❌ Username noto'g'ri. @username yoki -100... chat ID yuboring.")
        chat_id="@"+username
        public_username=username
        invite_link=f"https://t.me/{username}"
        kind="public"
    elif raw_value.startswith("https://") or raw_value.startswith("http://"):
        m=re.fullmatch(r"https?://t\.me/([A-Za-z0-9_]{5,})/?",raw_value)
        if not m:
            return await message.answer("❌ Invite-linkning o'zi bilan a'zolikni tekshirib bo'lmaydi. Public t.me/username yoki -100... chat ID yuboring.")
        username=m.group(1)
        chat_id="@"+username
        public_username=username
        invite_link=f"https://t.me/{username}"
        kind="public"
    elif re.fullmatch(r"-?\d{5,}", raw_value):
        chat_id=raw_value
        public_username=""
        invite_link=""
        kind="private"
    else:
        username=raw_value.lstrip("@").strip()
        if not re.fullmatch(r"[A-Za-z0-9_]{5,}",username):
            return await message.answer("❌ Kanal manzili noto'g'ri. @username, t.me/username yoki -100... ID kiriting.")
        chat_id="@"+username
        public_username=username
        invite_link=f"https://t.me/{username}"
        kind="public"
    try:
        chat=await bot.get_chat(chat_id)
        if chat.type not in ("channel","group","supergroup"):
            return await message.answer("❌ Bu Telegram chat kanal yoki guruh emas.")
        bot_member=await bot.get_chat_member(chat_id=chat.id,user_id=bot.id)
        if bot_member.status not in ("administrator","creator"):
            return await message.answer("❌ Bot guruh/kanalda admin emas. Telegram'da botni admin qilib, shu ID/linkni qayta yuboring.")
        title=chat.title or d["title"]
        chat_id=str(chat.id)
        public_username=chat.username or public_username
        if public_username:
            invite_link=f"https://t.me/{public_username}"
        else:
            try:
                invite_link=(await bot.create_chat_invite_link(chat_id=chat.id)).invite_link
            except TelegramAPIError as e:
                return await message.answer(
                    "❌ Yopiq kanal/guruh uchun taklif havolasi yaratilmadi. "
                    "Botga a'zo taklif qilish huquqini bering va qayta urinib ko'ring.\n"
                    f"<code>{escape(str(e)[:250])}</code>"
                )
    except Exception as e:
        return await message.answer(f"❌ Chatni tekshirib bo'lmadi. Botni guruhga qo'shing va admin qiling, keyin qayta urinib ko'ring.\n<code>{escape(str(e)[:250])}</code>")
    try:
        saved=await save_required_channel(chat_id,title,public_username,invite_link,kind)
    except aiosqlite.IntegrityError:
        await state.clear(); return await message.answer("❌ Bu kanal/guruh allaqachon ulangan.")
    if not saved:
        await state.clear()
        return await message.answer(f"❌ Eng ko'pi bilan {MAX_REQUIRED_CHANNELS} ta majburiy kanal/guruh qo'shish mumkin.")
    await log_action(message.from_user.id,"Majburiy obuna qo‘shildi",f"{title} {chat_id}")
    await state.clear()
    await message.answer(f"✅ <b>{escape(title)}</b> majburiy obunaga qo‘shildi.\n📢 {escape(chat_id)}")

@dp.callback_query(F.data=="channel_list")
async def channel_list(call):
    if not await admin_right(call.from_user.id,"channels"): return await call.answer("⛔",show_alert=True)
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT id,chat_id,title,username,kind,required FROM channels ORDER BY id"); rows=await cur.fetchall()
    text="📋 <b>Barcha kanallar/guruhlar</b>\n\n"
    for i,c,t,u,k,r in rows:
        status="✅ majburiy" if r else "❌ majburiy emas"
        text+=f"#{i} {escape(t)} | {status} | {k} | <code>{c}</code> | @{escape(u or '-')}\n"
    await call.message.answer(text or "📭 Yo'q."); await call.answer()

@dp.callback_query(F.data=="select_required_channels")
async def select_required_channels(call):
    if not await admin_right(call.from_user.id,"channels"): return await call.answer("⛔",show_alert=True)
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT id,title,username,chat_id,required FROM channels ORDER BY id")
        rows=await cur.fetchall()
    if not rows:
        await call.message.answer("📭 Hozircha kanal/guruh yo'q. Avval qo'shing.")
        return await call.answer()
    kb=[]
    for cid,title,username,chat_id,required in rows:
        label = title or (f"@{username}" if username else str(chat_id))
        status = "✅" if required else "❌"
        kb.append([InlineKeyboardButton(text=f"{status} {label}", callback_data=f"toggle_required_channel:{cid}")])
    kb.append([InlineKeyboardButton(text="↩️ Orqaga", callback_data="channels_menu")])
    await call.message.answer("📌 <b>Majburiy bo'ladigan kanallarni tanlang</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await call.answer()

@dp.callback_query(F.data.startswith("toggle_required_channel:"))
async def toggle_required_channel(call):
    if not await admin_right(call.from_user.id,"channels"): return await call.answer("⛔",show_alert=True)
    try:
        cid=int(call.data.split(":",1)[1])
    except ValueError:
        return await call.answer("❌ Noto'g'ri kanal",show_alert=True)
    async with aiosqlite.connect(DB) as db:
        await db.execute("BEGIN IMMEDIATE")
        cur=await db.execute("SELECT required,title FROM channels WHERE id=?",(cid,))
        row=await cur.fetchone()
        if not row:
            await db.rollback()
            return await call.answer("❌ Kanal topilmadi",show_alert=True)
        required = 0 if row[0] else 1
        if required:
            cur=await db.execute("SELECT COUNT(*) FROM channels WHERE COALESCE(required,1)=1")
            if (await cur.fetchone())[0] >= MAX_REQUIRED_CHANNELS:
                await db.rollback()
                return await call.answer(
                    f"❌ Eng ko'pi bilan {MAX_REQUIRED_CHANNELS} ta majburiy kanal/guruh bo'lishi mumkin.",
                    show_alert=True,
                )
        await db.execute("UPDATE channels SET required=? WHERE id=?",(required,cid))
        await db.commit()
    await call.answer(f"{'✅ Majburiy qilindi' if required else '❌ Majburiy emas qilindi'}", show_alert=True)
    await select_required_channels(call)

class RemoveChannel(StatesGroup): value=State()

@dp.callback_query(F.data=="remove_channel")
async def remove_channel(call,state):
    if not await admin_right(call.from_user.id,"channels"): return await call.answer("⛔",show_alert=True)
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT id,title,username,chat_id FROM channels ORDER BY id")
        rows=await cur.fetchall()
    if not rows:
        await call.message.answer("🗑 <b>Kanal o'chirish</b>\n\n📭 Hozircha majburiy kanal ulanmagan.")
        return await call.answer()
    kb=[]
    for cid,title,username,chat_id in rows:
        label=title or (f"@{username}" if username else str(chat_id))
        kb.append([InlineKeyboardButton(text=f"🗑 {label}",callback_data=f"remove_channel:{cid}")])
    kb.append([InlineKeyboardButton(text="↩️ Orqaga",callback_data="channels_menu")])
    await call.message.answer("🗑 <b>Qaysi kanalni o'chirasiz?</b>\n\nKerakli kanalni tugmadan tanlang:",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await call.answer()

@dp.callback_query(F.data.startswith("remove_channel:"))
async def remove_channel_do(call,state):
    if not await admin_right(call.from_user.id,"channels"): return await call.answer("⛔",show_alert=True)
    try: cid=int(call.data.split(":",1)[1])
    except: return await call.answer("❌ Kanal topilmadi.",show_alert=True)
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT title,username,chat_id FROM channels WHERE id=?",(cid,))
        row=await cur.fetchone()
        if not row:
            await state.clear()
            return await call.answer("❌ Kanal allaqachon o'chirilgan.",show_alert=True)
        title,username,chat_id=row
        await db.execute("DELETE FROM channels WHERE id=?",(cid,))
        await db.commit()
    name=title or (f"@{username}" if username else str(chat_id))
    await log_action(call.from_user.id,"Majburiy obuna o'chirildi",f"{cid}: {name}")
    await state.clear()
    await call.message.edit_text(f"✅ <b>{escape(name)}</b> majburiy obuna kanallaridan o'chirildi.",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanal boshqaruvi",callback_data="channels_menu")]
    ]))
    await call.answer("✅ O'chirildi")

# ============================================================
# NEWS CHANNEL
# ============================================================
@dp.callback_query(F.data=="news_menu")
async def news_menu(call):
    if not await admin_right(call.from_user.id,"channels"):
        return await call.answer("⛔ Ruxsat yo'q",show_alert=True)
    channel_id=await get_setting("news_channel_id")
    channel_title=await get_setting("news_channel_title")
    status=f"✅ {escape(channel_title or channel_id)}" if channel_id else "❌ Hali kanal ulanmagan"
    await call.message.answer(f"📰 <b>Yangiliklar bo'limi</b>\n\nKanal: {status}",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Yangiliklar kanalini ulash",callback_data="news_channel_setup")],
        [InlineKeyboardButton(text="✍️ Yangilik yuborish",callback_data="news_post_start")],
        [InlineKeyboardButton(text="↩️ Admin panel",callback_data="back_admin")]
    ]))
    await call.answer()

@dp.callback_query(F.data=="news_channel_setup")
async def news_channel_setup(call,state):
    if not await admin_right(call.from_user.id,"channels"):
        return await call.answer("⛔ Ruxsat yo'q",show_alert=True)
    await state.set_state(NewsChannel.chat_id)
    await call.message.answer("📢 Yangiliklar kanalining @username, t.me/username linki yoki -100... chat ID sini yuboring. Private kanal uchun chat ID kerak; bot kanalda post yozish huquqiga ega admin bo'lishi shart.")
    await call.answer()

@dp.message(NewsChannel.chat_id)
async def news_channel_save(message,state):
    raw=(message.text or "").strip()
    if raw.startswith("https://") or raw.startswith("http://"):
        match=re.fullmatch(r"https?://t\.me/([A-Za-z0-9_]{5,})/?",raw)
        raw="@"+match.group(1) if match else raw
    if raw.startswith("@") and re.fullmatch(r"@[A-Za-z0-9_]{5,}",raw):
        target=raw
    elif re.fullmatch(r"-?\d{5,}",raw):
        target=raw
    else:
        return await message.answer("❌ Manzil tushunarsiz. @username, t.me/username yoki -100... ID yuboring. Private kanal uchun ID ishlating.")
    try:
        chat=await bot.get_chat(target)
        member=await bot.get_chat_member(chat.id,bot.id)
        if member.status not in ("administrator","creator"):
            return await message.answer("❌ Bot bu kanalda admin emas. Botni kanalga admin qilib, qayta urinib ko'ring.")
        if getattr(member,"can_post_messages",True) is False:
            return await message.answer("❌ Botga kanalda post yozish huquqini bering.")
    except Exception as e:
        return await message.answer(f"❌ Kanalni tekshirib bo'lmadi. ID/linkni va bot huquqlarini tekshiring.\n<code>{escape(str(e)[:250])}</code>")
    public_link=f"https://t.me/{chat.username}" if chat.username else ""
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO settings(key,value) VALUES('news_channel_id',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(str(chat.id),))
        await db.execute("INSERT INTO settings(key,value) VALUES('news_channel_link',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(public_link,))
        await db.execute("INSERT INTO settings(key,value) VALUES('news_channel_title',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(chat.title or str(chat.id),))
        await db.commit()
    await state.clear()
    await message.answer(f"✅ Yangiliklar kanali ulandi: <b>{escape(chat.title or str(chat.id))}</b>")

@dp.callback_query(F.data=="news_post_start")
async def news_post_start(call,state):
    if not await admin_right(call.from_user.id,"channels"):
        return await call.answer("⛔ Ruxsat yo'q",show_alert=True)
    channel_id=await get_setting("news_channel_id")
    if not channel_id:
        return await call.answer("Avval yangiliklar kanalini ulang",show_alert=True)
    await state.set_state(NewsPost.source)
    await call.message.answer("✍️ Kanalga yuboriladigan yangilik matni yoki media-xabarni shu yerga yuboring. Keyingi bosqichda yuborishni tasdiqlaysiz.")
    await call.answer()

@dp.message(NewsPost.source)
async def news_post_prepare(message,state):
    await state.update_data(chat_id=message.chat.id,message_id=message.message_id)
    await state.set_state(NewsPost.confirm)
    await message.answer("📰 Yangilik kanalga chiqarilsinmi?",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Kanalga yuborish",callback_data="news_post_confirm"),
         InlineKeyboardButton(text="❌ Bekor qilish",callback_data="news_post_cancel")]
    ]))

@dp.callback_query(F.data=="news_post_confirm",NewsPost.confirm)
async def news_post_confirm(call,state):
    if not await admin_right(call.from_user.id,"channels"):
        await state.clear()
        return await call.answer("⛔ Ruxsat yo'q",show_alert=True)
    data=await state.get_data()
    channel_id=await get_setting("news_channel_id")
    await state.clear()
    try:
        await bot.copy_message(channel_id,data["chat_id"],data["message_id"])
        await call.message.answer("✅ Yangilik kanalga yuborildi.")
        await call.answer("Yuborildi")
        await log_action(call.from_user.id,"Yangilik kanalga post yuborildi",channel_id)
    except Exception as e:
        await call.answer("Kanalga yuborilmadi",show_alert=True)
        await call.message.answer(f"❌ Post yuborilmadi: <code>{escape(str(e)[:250])}</code>")

@dp.callback_query(F.data=="news_post_cancel",NewsPost.confirm)
async def news_post_cancel(call,state):
    await state.clear()
    await call.answer("Bekor qilindi")
    await call.message.answer("🛑 Yangilik yuborish bekor qilindi.")

# ============================================================
# ADMINS / USER BAN
# ============================================================
@dp.callback_query(F.data=="admins_menu")
async def admins_menu(call):
    if not await admin_right(call.from_user.id,"admins"): return await call.answer("⛔ Faqat bosh admin.",show_alert=True)
    await call.message.answer("👑 <b>Adminlar</b>",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Admin qo'shish",callback_data="add_admin")],
        [InlineKeyboardButton(text="📋 Adminlar",callback_data="admin_list")],
        [InlineKeyboardButton(text="❌ Adminlikdan olish",callback_data="remove_admin")]
    ])); await call.answer()

@dp.callback_query(F.data=="add_admin")
async def add_admin(call,state):
    if call.from_user.id!=OWNER_ID: return await call.answer("⛔ Faqat bosh admin.",show_alert=True)
    await state.set_state(AddAdmin.user_id); await call.message.answer("👤 Telegram ID:"); await call.answer()

@dp.message(AddAdmin.user_id)
async def add_admin_id(message,state):
    try: uid=int(message.text.strip())
    except: return await message.answer("❌ ID raqam bo'lishi kerak.")
    await state.update_data(user_id=uid); await state.set_state(AddAdmin.permissions)
    await message.answer("🔑 Huquqlar: movies,users,broadcast,channels,stats,admins,vip,support,logs\nMasalan: <code>movies,vip,stats</code>")

@dp.message(AddAdmin.permissions)
async def add_admin_permissions(message,state):
    d=await state.get_data(); perms={x.strip() for x in message.text.lower().split(",") if x.strip()}
    if not perms.issubset(PERMS): return await message.answer("❌ Huquq nomi noto'g'ri.")
    cols={p:int(p in perms) for p in PERMS}
    async with aiosqlite.connect(DB) as db:
        await db.execute("""INSERT INTO admins(user_id,can_movies,can_users,can_broadcast,can_channels,
        can_stats,can_admins,can_vip,can_support,can_logs,added_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET can_movies=excluded.can_movies,can_users=excluded.can_users,
        can_broadcast=excluded.can_broadcast,can_channels=excluded.can_channels,can_stats=excluded.can_stats,
        can_admins=excluded.can_admins,can_vip=excluded.can_vip,can_support=excluded.can_support,can_logs=excluded.can_logs""",
        (d["user_id"],cols["movies"],cols["users"],cols["broadcast"],cols["channels"],cols["stats"],cols["admins"],cols["vip"],cols["support"],cols["logs"],datetime.now().isoformat()))
        await db.commit()
    await log_action(message.from_user.id,"Admin qo'shildi",str(d["user_id"])); await state.clear(); await message.answer(success_text("Admin qo'shildi."))

@dp.callback_query(F.data=="admin_list")
async def admin_list(call):
    if call.from_user.id!=OWNER_ID: return await call.answer("⛔",show_alert=True)
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT user_id,can_movies,can_users,can_broadcast,can_channels,can_stats,can_admins,can_vip,can_support,can_logs FROM admins")
        rows=await cur.fetchall()
    names=list(PERMS)
    text="👑 <b>Adminlar</b>\n\n"
    for r in rows:
        uid=r[0]
        if uid==OWNER_ID: text+=f"⭐ <code>{uid}</code> — Bosh admin\n"; continue
        p=[names[i] for i,v in enumerate(r[1:]) if v]
        text+=f"👤 <code>{uid}</code> — {', '.join(p) or 'huquq yo‘q'}\n"
    await call.message.answer(text); await call.answer()

@dp.callback_query(F.data=="remove_admin")
async def remove_admin(call,state):
    if call.from_user.id!=OWNER_ID: return await call.answer("⛔",show_alert=True)
    await state.set_state(RemoveAdmin.user_id); await call.message.answer("❌ Admin ID:"); await call.answer()
@dp.message(RemoveAdmin.user_id)
async def remove_admin_do(message,state):
    try: uid=int(message.text.strip())
    except: return await message.answer("❌ ID raqam bo'lishi kerak.")
    if uid==OWNER_ID: return await message.answer("❌ Bosh adminni olib bo'lmaydi.")
    async with aiosqlite.connect(DB) as db: await db.execute("DELETE FROM admins WHERE user_id=?",(uid,)); await db.commit()
    await log_action(message.from_user.id,"Adminlik olindi",str(uid)); await state.clear(); await message.answer("✅ Adminlik olindi.")

@dp.callback_query(F.data=="users_menu")
async def users_menu(call):
    if not await admin_right(call.from_user.id,"users"): return await call.answer("⛔",show_alert=True)
    await call.message.answer("👥 <b>Userlar</b>",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Ban",callback_data="ban_user"),InlineKeyboardButton(text="✅ Unban",callback_data="unban_user")],
        [InlineKeyboardButton(text="📋 Banlanganlar",callback_data="banned_list")]
    ])); await call.answer()

@dp.callback_query(F.data=="ban_user")
async def ban_start(call,state):
    if not await admin_right(call.from_user.id,"users"): return await call.answer("⛔",show_alert=True)
    await state.set_state(BanUser.user_id); await call.message.answer("🚫 User Telegram ID:"); await call.answer()
@dp.message(BanUser.user_id)
async def ban_id(message,state):
    try: uid=int(message.text.strip())
    except: return await message.answer("❌ ID raqam bo'lishi kerak.")
    if uid==OWNER_ID: return await message.answer("❌ Bosh adminni ban qilib bo'lmaydi.")
    await state.update_data(user_id=uid); await state.set_state(BanUser.reason); await message.answer("📝 Sabab yoki - :")
@dp.message(BanUser.reason)
async def ban_reason(message,state):
    d=await state.get_data(); reason="" if message.text.strip()=="-" else message.text.strip()
    async with aiosqlite.connect(DB) as db:
        await db.execute("""INSERT INTO users(id,joined_at,last_active,banned,ban_reason) VALUES(?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET banned=1,ban_reason=excluded.ban_reason""",
        (d["user_id"],datetime.now().isoformat(),datetime.now().isoformat(),1,reason)); await db.commit()
    await log_action(message.from_user.id,"User ban qilindi",f"{d['user_id']} {reason}"); await state.clear()
    await message.answer("🚫 User ban qilindi.")

@dp.callback_query(F.data=="unban_user")
async def unban_start(call,state):
    if not await admin_right(call.from_user.id,"users"): return await call.answer("⛔",show_alert=True)
    await state.set_state(UnbanUser.user_id); await call.message.answer("✅ User ID:"); await call.answer()
@dp.message(UnbanUser.user_id)
async def unban_do(message,state):
    try: uid=int(message.text.strip())
    except: return await message.answer("❌ ID raqam bo'lishi kerak.")
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET banned=0,ban_reason='' WHERE id=?",(uid,)); await db.commit()
    await log_action(message.from_user.id,"User unban qilindi",str(uid)); await state.clear(); await message.answer("✅ Ban olib tashlandi.")

@dp.callback_query(F.data=="banned_list")
async def banned_list(call):
    if not await admin_right(call.from_user.id,"users"): return await call.answer("⛔",show_alert=True)
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT id,username,ban_reason FROM users WHERE banned=1 ORDER BY id DESC LIMIT 100"); rows=await cur.fetchall()
    text="🚫 <b>Banlanganlar</b>\n\n"
    for u,n,r in rows: text+=f"<code>{u}</code> @{escape(n or '-')} — {escape(r or '-')}\n"
    await call.message.answer(text or "✅ Yo'q."); await call.answer()

# ============================================================
# MOVIES / EPISODES / FAVORITES
# ============================================================
@dp.callback_query(F.data=="manage_movies")
async def manage_movies(call):
    if not await admin_right(call.from_user.id,"movies"): return await call.answer("⛔",show_alert=True)
    await call.message.answer("🎬 <b>Kino boshqaruvi</b>",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kino qo'shish",callback_data="add_movie")],
        [InlineKeyboardButton(text="📋 Kino ro'yxati",callback_data="movie_list")]
    ])); await call.answer()

@dp.callback_query(F.data=="add_movie")
async def add_movie(call,state):
    if not await admin_right(call.from_user.id,"movies"): return await call.answer("⛔",show_alert=True)
    await state.set_state(AddMovie.code); await call.message.answer("🔢 Kino kodi:"); await call.answer()
@dp.message(AddMovie.code)
async def movie_code(message,state):
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT id FROM movies WHERE code=?",(message.text.strip(),)); r=await cur.fetchone()
    if r: return await message.answer("❌ Bu kod mavjud.")
    await state.update_data(code=message.text.strip()); await state.set_state(AddMovie.title); await message.answer("🎬 Kino nomi:")
@dp.message(AddMovie.title)
async def movie_title(message,state):
    await state.update_data(title=message.text.strip()); await state.set_state(AddMovie.description); await message.answer("📝 Tavsif yoki - :")
@dp.message(AddMovie.description)
async def movie_desc(message,state):
    await state.update_data(description="" if message.text.strip()=="-" else message.text.strip()); await state.set_state(AddMovie.genre); await message.answer("🎭 Janr yoki - :")
@dp.message(AddMovie.genre)
async def movie_genre(message,state):
    await state.update_data(genre="" if message.text.strip()=="-" else message.text.strip()); await state.set_state(AddMovie.year); await message.answer("📅 Yil yoki - :")
@dp.message(AddMovie.year)
async def movie_year(message,state):
    await state.update_data(year="" if message.text.strip()=="-" else message.text.strip())
    await state.set_state(AddMovie.access)
    await message.answer("👥 Kimlar ko‘ra oladi?",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Hamma uchun",callback_data="movieaccess:all")],
        [InlineKeyboardButton(text="👤 Tanlanganlar",callback_data="movieaccess:selected")]
    ]))
@dp.callback_query(F.data.startswith("movieaccess:"), AddMovie.access)
async def movie_access(call,state):
    mode=call.data.split(":",1)[1]
    if mode not in {"all","selected"}: return await call.answer("❌",show_alert=True)
    await state.update_data(access_mode=mode)
    if mode=="selected":
        await state.set_state(AddMovie.selected_users)
        await call.message.answer("👤 Tanlangan user ID larini vergul bilan yuboring. Masalan: <code>123456789,987654321</code>")
    else:
        await state.set_state(AddMovie.preview)
        await call.message.answer("⏱ AI preview uzunligini tanlang:",reply_markup=preview_kb())
    await call.answer()
@dp.message(AddMovie.selected_users)
async def movie_selected_users(message,state):
    raw=[x.strip() for x in message.text.split(",") if x.strip()]
    try: users=sorted(set(int(x) for x in raw))
    except: return await message.answer("❌ User ID larni faqat raqam bilan, vergul orqali yuboring.")
    if not users: return await message.answer("❌ Kamida bitta user ID kerak.")
    await state.update_data(selected_users=users); await state.set_state(AddMovie.preview)
    await message.answer("⏱ AI preview uzunligini tanlang:",reply_markup=preview_kb())
def preview_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="4 soniya",callback_data="preview:4"),
         InlineKeyboardButton(text="5 soniya",callback_data="preview:5"),
         InlineKeyboardButton(text="10 soniya",callback_data="preview:10")],
        [InlineKeyboardButton(text="↩️ Orqaga",callback_data="add_movie_back")],
    ])

@dp.callback_query(F.data=="add_movie_back")
async def add_movie_back(call,state):
    await state.set_state(AddMovie.access)
    await call.message.answer("👥 Kimlar ko‘ra oladi?",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Hamma uchun",callback_data="movieaccess:all")],
        [InlineKeyboardButton(text="👤 Tanlanganlar",callback_data="movieaccess:selected")]
    ]))
    await call.answer()

@dp.callback_query(F.data.startswith("preview:"), AddMovie.preview)
async def movie_preview_choice(call,state):
    seconds=int(call.data.split(":")[1])
    if seconds not in {4,5,10}: return await call.answer("❌",show_alert=True)
    await state.update_data(preview_seconds=seconds)
    await state.set_state(AddMovie.media)
    await call.message.answer(f"🎥 To‘liq kinoni yuboring.\n\n🤖 AI qiziq joyini topadi va {seconds} soniyalik previewni kino kanaliga avtomatik joylaydi.")
    await call.answer("✅ Tanlandi")

def scene_choice_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 AI o‘zi tanlasin",callback_data="scene:auto")],
        [InlineKeyboardButton(text="❤️ Romantik / Ishqiy",callback_data="scene:romantic")],
        [InlineKeyboardButton(text="⚔️ Jang / Action",callback_data="scene:action")],
        [InlineKeyboardButton(text="😂 Kulgi / Komediya",callback_data="scene:comedy")],
        [InlineKeyboardButton(text="😱 Qo‘rqinchli",callback_data="scene:horror")],
        [InlineKeyboardButton(text="🎭 Drama",callback_data="scene:drama")],
        [InlineKeyboardButton(text="🔪 Triller / Sirli",callback_data="scene:thriller")],
    ])

@dp.message(AddMovie.media,F.video)
async def movie_media(message,state):
    await state.update_data(file_id=message.video.file_id)
    await state.set_state(AddMovie.scene)
    await message.answer("🎬 Video qabul qilindi.\n\nQaysi turdagi qiziq joydan preview tayyorlaymiz?",reply_markup=scene_choice_kb())

@dp.callback_query(F.data.startswith("scene:"), AddMovie.scene)
async def movie_scene_choice(call,state):
    focus=call.data.split(":",1)[1]
    if focus not in {"auto","romantic","action","comedy","horror","drama","thriller"}: return await call.answer("❌",show_alert=True)
    d=await state.get_data(); await state.update_data(scene_focus=focus)
    status=await call.message.answer("🤖 AI video tahlili boshlandi...")
    tmp_dir=tempfile.mkdtemp(prefix="kino_ai_"); src=str(Path(tmp_dir)/"movie.mp4")
    try:
        tg_file=await bot.get_file(d["file_id"]); await bot.download_file(tg_file.file_path,src)
        try: analysis=await ai_analyze_movie(src,focus)
        except Exception:
            logging.exception("AI tahlil muvaffaqiyatsiz; fallback")
            dur=await video_duration(src); analysis={"genre":d.get("genre","") or "-","description":d.get("description","") or "Kino previewi.","rating":0,"hook":"🔥 Bu kinoning qiziq sahnalaridan biri...","highlight_start":max(0,dur/2-PREVIEW_SECONDS/2)}
        genre=analysis.get("genre") or d.get("genre",""); description=analysis.get("description") or d.get("description",""); rating=analysis.get("rating",0)
        highlight=int(max(0,float(analysis.get("highlight_start",0)))); duration=await video_duration(src); highlight=min(highlight,max(0,duration-1))
        preview_seconds=int(d.get("preview_seconds") or PREVIEW_SECONDS); preview=str(Path(tmp_dir)/"preview.mp4")
        await make_preview(src,preview,highlight,preview_seconds)
        async with aiosqlite.connect(DB) as db:
            cur=await db.execute("""INSERT INTO movies(code,title,description,genre,year,media_type,file_id,vip_only,access_mode,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",(d["code"],d["title"],description,genre,d["year"],"video",d["file_id"],1 if d.get("access_mode")=="vip" else 0,d.get("access_mode","all"),datetime.now().isoformat()))
            mid=cur.lastrowid
            for uid in d.get("selected_users",[]): await db.execute("INSERT OR IGNORE INTO movie_access(movie_id,user_id) VALUES(?,?)",(mid,uid))
            await db.commit()
        await publish_movie_preview(mid,d,analysis,preview)
        await log_action(call.from_user.id,"Kino qo‘shildi",f"{d['code']} {d['title']} scene={focus}")
        await notify_all("notify_movies",f"🆕 <b>Yangi kino qo‘shildi!</b>\n🎬 {escape(d['title'])}\n🔢 Kod: <code>{escape(d['code'])}</code>")
        await status.edit_text(f"✅ Kino qo‘shildi.\n🎯 Preview: {escape(focus)}\n🤖 Janr: {escape(genre or '-') }\n⭐ AI bahosi: {rating}/10")
    except Exception as e:
        logging.exception("Movie AI/publish failed"); await status.edit_text(f"❌ Xatolik: <code>{escape(str(e)[:500])}</code>")
    finally:
        import shutil; shutil.rmtree(tmp_dir,ignore_errors=True)
    await state.clear()

@dp.message(AddMovie.media)
async def movie_wrong(message): await message.answer("❌ To‘liq video yuboring.")

@dp.callback_query(F.data=="movie_channel")
async def movie_channel(call,state):
    if not await admin_right(call.from_user.id,"movies"): return await call.answer("⛔",show_alert=True)
    await state.set_state(MovieChannel.chat_id); await call.message.answer("🎥 Kino kanalining @username yoki chat ID sini yuboring. Masalan: <code>@my_kino_channel</code>"); await call.answer()
@dp.message(MovieChannel.chat_id)
async def movie_channel_id(message,state):
    await state.update_data(chat_id=message.text.strip()); await state.set_state(MovieChannel.username); await message.answer("🔗 Kanal username sini yuboring (@ bilan yoki -). Public kanal bo‘lsa shu username tugmadagi link uchun ishlatiladi.")
@dp.message(MovieChannel.username)
async def movie_channel_username(message,state):
    d=await state.get_data(); username="" if message.text.strip()=="-" else message.text.strip().lstrip("@")
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO settings(key,value) VALUES('movie_channel_id',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(d["chat_id"],))
        await db.execute("INSERT INTO settings(key,value) VALUES('movie_channel_username',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(username,)); await db.commit()
    await state.clear(); await message.answer("✅ Kino kanali saqlandi.")

@dp.callback_query(F.data=="add_episode")
async def add_episode(call,state):
    if not await admin_right(call.from_user.id,"movies"): return await call.answer("⛔",show_alert=True)
    await state.set_state(AddEpisode.code); await call.message.answer("📺 Asosiy kino kodi:"); await call.answer()
@dp.message(AddEpisode.code)
async def ep_code(message,state):
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT id,title FROM movies WHERE code=?",(message.text.strip(),)); r=await cur.fetchone()
    if not r: return await message.answer("❌ Kino topilmadi.")
    await state.update_data(movie_id=r[0],movie_title=r[1]); await state.set_state(AddEpisode.episode); await message.answer("🔢 Qism raqami:")
@dp.message(AddEpisode.episode)
async def ep_no(message,state):
    try: n=int(message.text.strip()); assert n>0
    except: return await message.answer("❌ Musbat son.")
    await state.update_data(episode=n); await state.set_state(AddEpisode.title); await message.answer("📝 Qism nomi yoki - :")
@dp.message(AddEpisode.title)
async def ep_title(message,state):
    await state.update_data(title="" if message.text.strip()=="-" else message.text.strip()); await state.set_state(AddEpisode.media); await message.answer("🎥 Qism videosi:")
@dp.message(AddEpisode.media,F.video)
async def ep_media(message,state):
    d=await state.get_data()
    try:
        async with aiosqlite.connect(DB) as db:
            await db.execute("""INSERT INTO episodes(movie_id,episode_no,title,media_type,file_id,created_at)
            VALUES(?,?,?,?,?,?)""",(d["movie_id"],d["episode"],d["title"],"video",message.video.file_id,datetime.now().isoformat())); await db.commit()
    except aiosqlite.IntegrityError: return await message.answer("❌ Bu qism mavjud.")
    await log_action(message.from_user.id,"Qism qo'shildi",f"{d['movie_id']} {d['episode']}")
    await notify_all("notify_episodes",f"📺 <b>Yangi qism chiqdi!</b>\n🎬 {escape(d['movie_title'])}\n🔢 {d['episode']}-qism")
    await state.clear(); await message.answer("✅ Qism qo'shildi.")
@dp.message(AddEpisode.media)
async def ep_wrong(message): await message.answer("❌ Video yuboring.")

async def video_duration(path):
    proc=await asyncio.create_subprocess_exec("ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",path,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    out,_=await proc.communicate()
    try: return float(out.decode().strip())
    except: return 0.0

async def make_preview(src,dst,start,seconds=None):
    seconds=int(seconds or PREVIEW_SECONDS)
    proc=await asyncio.create_subprocess_exec("ffmpeg","-y","-ss",str(start),"-i",src,"-t",str(seconds),"-vf","scale=-2:720","-c:v","libx264","-preset","veryfast","-c:a","aac","-movflags","+faststart",dst,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    _,err=await proc.communicate()
    if proc.returncode!=0: raise RuntimeError("Preview yaratilmadi: "+err.decode(errors="ignore")[-500:])

async def ai_analyze_movie(path, focus="auto"):
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY .env faylida sozlanmagan")
    frame_dir=Path(tempfile.mkdtemp(prefix="kino_frames_"))
    try:
        # Videodan reprezentativ kadrlar: video uzunligidan kelib chiqib bir tekis tanlanadi.
        duration=await video_duration(path)
        count=max(8,min(AI_FRAME_COUNT,40))
        proc=await asyncio.create_subprocess_exec("ffmpeg","-y","-i",path,"-vf",f"fps={count}/{max(duration,1)},scale=768:-1","-frames:v",str(count),str(frame_dir/"frame_%02d.jpg"),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        _,err=await proc.communicate()
        frames=sorted(frame_dir.glob("*.jpg"))
        if not frames: raise RuntimeError("Video kadrlari olinmadi")
        focus_map={"auto":"AI o‘zi eng qiziq sahnani tanlasin","romantic":"romantik yoki ishqiy sahnani top","action":"jang/action sahnasini top","comedy":"kulgili yoki komedik sahnani top","horror":"qo‘rqinchli sahnani top","drama":"dramatik/emotsional sahnani top","thriller":"sirli/triller sahnasini top"}
        focus_text=focus_map.get(focus,focus_map["auto"])
        content=[{'type':'input_text','text':f'Bu kino/serial videosidan olingan kadrlarni tahlil qil. {focus_text}. Janr(lar), qisqa qiziqarli tavsif, 1-10 baho, kanal postining tepasiga qo‘yiladigan qisqa clickbait uslubidagi jumla va eng qiziq sahnaga yaqin vaqtni aniqlashga harakat qil. Kadrlar video davomida bir tekis tanlangan. Faqat JSON qaytar: {"genre":"...","description":"...","rating":8.5,"hook":"Bunaqa kino boshqa chiqmasa kerak...","highlight_start":90}. hook 1 qisqa jumla bo‘lsin, yolg‘on spoiler yoki haddan tashqari va’da bermasin.'}]
        for f in frames:
            b64=base64.b64encode(f.read_bytes()).decode()
            content.append({"type":"input_image","image_url":f"data:image/jpeg;base64,{b64}"})
        payload={"model":AI_MODEL,"input":[{"role":"user","content":content}],"max_output_tokens":500}
        def _call_openai():
            req=urllib.request.Request("https://api.openai.com/v1/responses",data=json.dumps(payload).encode("utf-8"),headers={"Authorization":f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"},method="POST")
            try:
                with urllib.request.urlopen(req,timeout=180) as r:
                    return json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                body=e.read().decode("utf-8",errors="ignore")
                raise RuntimeError(f"OpenAI API xatosi {e.code}: {body[:500]}")
        data=await asyncio.to_thread(_call_openai)
        parts=[]
        for item in data.get("output",[]):
            for c in item.get("content",[]):
                if c.get("type") in {"output_text","text"} and c.get("text"):
                    parts.append(c["text"])
        text="".join(parts).strip()
        text=re.sub(r"^```(?:json)?|```$","",text).strip()
        return json.loads(text)
    finally:
        import shutil; shutil.rmtree(frame_dir,ignore_errors=True)

async def publish_movie_preview(mid,data,analysis,preview_path):
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT value FROM settings WHERE key='movie_channel_id'"); r=await cur.fetchone(); channel_id=r[0] if r else ""
        cur=await db.execute("SELECT value FROM settings WHERE key='movie_channel_username'"); r=await cur.fetchone(); channel_username=r[0] if r else ""
    if not channel_id: return
    me=await bot.get_me()
    bot_username=me.username
    link=f"https://t.me/{bot_username}?start=movie_{data['code']}"
    rating=analysis.get("rating",0)
    genre=analysis.get("genre") or data.get("genre") or "-"
    desc=analysis.get("description") or data.get("description") or "-"
    hook=analysis.get("hook") or "🔥 Bu sahnani ko‘rgandan keyin kino yanada qiziq bo‘ladi..."
    access=data.get("access_mode","all")
    access_text={"all":"🌐 Hamma uchun","selected":"👤 Tanlanganlar uchun"}.get(access,access)
    caption=(f"✨ <b>{escape(str(hook))}</b>\n\n"
             f"🎬 <b>{escape(data['title'])}</b>\n"
             f"🎭 Janr: <b>{escape(str(genre))}</b>\n"
             f"⭐ Kino bahosi: <b>{rating}/10</b>\n"
             f"{escape(str(desc))}\n\n"
             f"🔢 Kino kodi: <code>{escape(str(data['code']))}</code>\n"
             f"🔐 Kirish: {access_text}")
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎬 Kinoni ko‘rish",url=link)]])
    # iOS uslubidagi sticker uchun Telegram sticker file_id .env orqali beriladi.
    if AI_STICKER_FILE_ID:
        try:
            await bot.send_sticker(chat_id=channel_id,sticker=AI_STICKER_FILE_ID)
        except Exception:
            logging.warning("AI_STICKER_FILE_ID yuborilmadi",exc_info=True)
    await bot.send_video(chat_id=channel_id,video=FSInputFile(preview_path),caption=caption,reply_markup=kb)

async def send_movie(message,movie):
    mid,code,title,desc,genre,year,mt,file_id,views,vip_only,access_mode,created=movie
    uid=message.from_user.id
    if access_mode=="vip" and not await is_vip(uid):
        lang=await get_lang(uid)
        return await message.answer(tr(lang,"vip_required"),reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 VIP ga obuna bo‘lish",callback_data="vip_menu")]]))
    if access_mode=="selected":
        async with aiosqlite.connect(DB) as db:
            cur=await db.execute("SELECT 1 FROM movie_access WHERE movie_id=? AND user_id=?",(mid,uid)); allowed=await cur.fetchone()
        if not allowed:
            return await message.answer("🔒 Bu kino faqat tanlangan foydalanuvchilar uchun.")
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE movies SET views=views+1 WHERE id=?",(mid,))
        await db.execute("INSERT INTO movie_watch_history(user_id,movie_id,watched_at) VALUES(?,?,?) ON CONFLICT(user_id,movie_id) DO UPDATE SET watched_at=excluded.watched_at",(message.from_user.id,mid,datetime.now().isoformat()))
        await db.commit()
        cur=await db.execute("SELECT COALESCE(ROUND(AVG(rating),2),0) FROM ratings WHERE movie_id=?",(mid,)); avg=(await cur.fetchone())[0]
    text=f"🎬 <b>{escape(title)}</b>\n"
    if year: text+=f"📅 {escape(year)}\n"
    if genre: text+=f"🎭 {escape(genre)}\n"
    if desc: text+=f"\n📝 {escape(desc)}\n"
    text+=f"\n🔢 Kod: <code>{escape(code)}</code>\n⭐ Reyting: {avg}"
    await message.answer_video(video=file_id,caption=text,reply_markup=movie_kb(mid))

@dp.callback_query(F.data.startswith("eps:"))
async def show_eps(call):
    mid=int(call.data.split(":")[1])
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT episode_no,title FROM episodes WHERE movie_id=? ORDER BY episode_no",(mid,)); rows=await cur.fetchall()
    if not rows: return await call.answer("📺 Qismlar yo'q.",show_alert=True)
    await call.message.answer("📺 <b>Qismlar:</b>",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"▶️ {n}-qism"+(f" — {t}" if t else ""),callback_data=f"playep:{mid}:{n}")]
        for n,t in rows]))
    await call.answer()

@dp.callback_query(F.data.startswith("playep:"))
async def play_ep(call):
    _,mid,ep=call.data.split(":"); mid=int(mid); ep=int(ep)
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT title,file_id FROM episodes WHERE movie_id=? AND episode_no=?",(mid,ep)); r=await cur.fetchone()
        if not r: return await call.answer("❌ Qism topilmadi.",show_alert=True)
        await db.execute("UPDATE episodes SET views=views+1 WHERE movie_id=? AND episode_no=?",(mid,ep)); await db.commit()
    await call.message.answer_video(video=r[1],caption=f"📺 <b>{escape(r[0] or 'Serial')}</b>\n🔢 {ep}-qism"); await call.answer()

@dp.callback_query(F.data.startswith("rate:"))
async def rate(call):
    _,mid,ra=call.data.split(":")
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO ratings(user_id,movie_id,rating) VALUES(?,?,?) ON CONFLICT(user_id,movie_id) DO UPDATE SET rating=excluded.rating",(call.from_user.id,int(mid),int(ra))); await db.commit()
    await call.answer(f"⭐ {ra} ball saqlandi!")

@dp.callback_query(F.data.startswith("fav:"))
async def favorite(call):
    mid=int(call.data.split(":")[1]); uid=call.from_user.id
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT 1 FROM favorites WHERE user_id=? AND movie_id=?",(uid,mid)); r=await cur.fetchone()
        if r: await db.execute("DELETE FROM favorites WHERE user_id=? AND movie_id=?",(uid,mid)); msg="❌ Sevimlilardan olindi."
        else: await db.execute("INSERT INTO favorites(user_id,movie_id) VALUES(?,?)",(uid,mid)); msg="❤️ Sevimlilarga qo'shildi."
        await db.commit()
    await call.answer(msg)

@dp.callback_query(F.data=="favorites")
async def favorites(call):
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("""SELECT m.code,m.title FROM favorites f JOIN movies m ON m.id=f.movie_id
        WHERE f.user_id=? ORDER BY m.title""",(call.from_user.id,)); rows=await cur.fetchall()
    await call.message.answer("❤️ <b>Sevimlilar</b>\n\n"+("\n".join(f"🎬 <code>{c}</code> — {escape(t)}" for c,t in rows) if rows else "📭 Hozircha yo‘q."),reply_markup=profile_kb())
    await call.answer()

@dp.callback_query(F.data=="movie_list")
async def movie_list(call):
    if not await admin_right(call.from_user.id,"movies"): return await call.answer("⛔",show_alert=True)
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT code,title,views,access_mode FROM movies ORDER BY id DESC LIMIT 100"); rows=await cur.fetchall()
    await call.message.answer("📋 <b>Kinolar</b>\n\n"+("\n".join(f"🔢 <code>{c}</code> — {escape(t)} — {v} 👁 — {vip}" for c,t,v,vip in rows) if rows else "📭 Yo'q.")); await call.answer()

# ============================================================
# PROFILE / RANKING
# ============================================================
def profile_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika",callback_data="profile_stats")],
        [InlineKeyboardButton(text="❤️ Yoqtirgan kinolar",callback_data="favorites")],
        [InlineKeyboardButton(text="🕘 Ko‘rilgan kinolar",callback_data="history")],
        [InlineKeyboardButton(text="👤 Profil ma’lumoti",callback_data="profile_info")],
        [InlineKeyboardButton(text="↩️ Orqaga",callback_data="back_home")],
    ])

@dp.callback_query(F.data=="profile")
async def profile(call):
    await call.message.answer("👤 <b>Profil bo‘limi</b>\n\nKerakli bo‘limni tanlang:",reply_markup=profile_kb())
    await call.answer()

@dp.callback_query(F.data=="profile_stats")
async def profile_stats(call):
    uid=call.from_user.id
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT COUNT(*) FROM movie_watch_history WHERE user_id=?",(uid,)); watched=(await cur.fetchone())[0]
        cur=await db.execute("SELECT COUNT(*) FROM favorites WHERE user_id=?",(uid,)); fav=(await cur.fetchone())[0]
        cur=await db.execute("SELECT COALESCE(SUM(views),0) FROM movies"); total_views=(await cur.fetchone())[0]
    await call.message.answer(f"📊 <b>Mening statistikam</b>\n\n🎬 Ko‘rilgan kinolar: <b>{watched}</b>\n❤️ Yoqtirilganlar: <b>{fav}</b>\n👁 Botdagi jami ko‘rishlar: <b>{total_views}</b>",reply_markup=profile_kb())
    await call.answer()

@dp.callback_query(F.data=="profile_info")
async def profile_info(call):
    uid=call.from_user.id
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT username,full_name,joined_at FROM users WHERE id=?",(uid,)); u=await cur.fetchone()
    if not u: return await call.answer("❌ Profil topilmadi.",show_alert=True)
    await call.message.answer(f"👤 <b>Profil</b>\n\n🆔 <code>{uid}</code>\n👤 @{escape(u[0] or '-')}\n📝 {escape(u[1] or '-')}\n📅 Qo‘shilgan: {escape(u[2] or '-')}",reply_markup=profile_kb())
    await call.answer()

@dp.callback_query(F.data=="history")
async def history(call):
    uid=call.from_user.id
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("""SELECT m.code,m.title,h.watched_at FROM movie_watch_history h JOIN movies m ON m.id=h.movie_id WHERE h.user_id=? ORDER BY h.watched_at DESC LIMIT 30""",(uid,)); rows=await cur.fetchall()
    text="🕘 <b>Ko‘rilgan kinolar</b>\n\n"+ ("\n".join(f"🎬 <code>{c}</code> — {escape(t)}" for c,t,_ in rows) if rows else "📭 Hali kino ko‘rilmagan.")
    await call.message.answer(text,reply_markup=profile_kb()); await call.answer()

@dp.callback_query(F.data=="back_home")
async def back_home(call):
    lang=await get_lang(call.from_user.id)
    await call.message.answer(tr(lang,"welcome"),reply_markup=user_kb(lang)); await call.answer()

@dp.callback_query(F.data=="ranking")
async def ranking(call):
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("""SELECT u.id,u.username,COUNT(h.movie_id) AS c\n        FROM users u LEFT JOIN movie_watch_history h ON h.user_id=u.id\n        WHERE u.banned=0 GROUP BY u.id ORDER BY c DESC,u.id LIMIT 20""")
        rows=await cur.fetchall()
    text="🏆 <b>User Reytingi</b>\n\n"
    for i,(uid,username,c) in enumerate(rows,1):
        text+=f"{i}. @{escape(username or str(uid))} — 🎬 {c}\n"
    await call.message.answer(text if rows else "📭 Reyting hali bo'sh.")
    await call.answer()

# ============================================================
# BULK MOVIE MANAGEMENT
# ============================================================
@dp.callback_query(F.data=="bulk_movies")
async def bulk_movies(call):
    if not await admin_right(call.from_user.id,"movies"): return await call.answer("⛔",show_alert=True)
    await call.message.answer("🛠 <b>Ommaviy kino boshqaruvi</b>",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Kodlar bo'yicha o'chirish",callback_data="bulk_delete")],
        [InlineKeyboardButton(text="✏️ Kod bo'yicha tahrirlash",callback_data="bulk_edit")],
    ])); await call.answer()

class BulkDelete(StatesGroup): codes=State()
class BulkEdit(StatesGroup): codes=State(); field=State(); value=State()

@dp.callback_query(F.data=="bulk_delete")
async def bulk_delete_start(call,state):
    if not await admin_right(call.from_user.id,"movies"): return await call.answer("⛔",show_alert=True)
    await state.set_state(BulkDelete.codes); await call.message.answer("🗑 O'chiriladigan kino kodlarini vergul bilan yuboring. Masalan: <code>101,102,103</code>"); await call.answer()

@dp.message(BulkDelete.codes)
async def bulk_delete_do(message,state):
    codes=[x.strip() for x in message.text.split(",") if x.strip()]
    if not codes: return await message.answer("❌ Kodlar topilmadi.")
    async with aiosqlite.connect(DB) as db:
        q=','.join('?' for _ in codes)
        cur=await db.execute(f"SELECT id FROM movies WHERE code IN ({q})",codes); mids=[r[0] for r in await cur.fetchall()]
        await db.execute(f"DELETE FROM movie_access WHERE movie_id IN (SELECT id FROM movies WHERE code IN ({q}))",codes)
        await db.execute(f"DELETE FROM movies WHERE code IN ({q})",codes)
        if mids:
            q2=','.join('?' for _ in mids)
            await db.execute(f"DELETE FROM episodes WHERE movie_id IN ({q2})",mids)
            await db.execute(f"DELETE FROM ratings WHERE movie_id IN ({q2})",mids)
            await db.execute(f"DELETE FROM favorites WHERE movie_id IN ({q2})",mids)
            await db.execute(f"DELETE FROM movie_watch_history WHERE movie_id IN ({q2})",mids)
        await db.commit()
    await log_action(message.from_user.id,"Ommaviy kino o'chirildi",','.join(codes)); await state.clear(); await message.answer(f"✅ {len(mids)} ta kino o'chirildi.")

@dp.callback_query(F.data=="bulk_edit")
async def bulk_edit_start(call,state):
    if not await admin_right(call.from_user.id,"movies"): return await call.answer("⛔",show_alert=True)
    await state.set_state(BulkEdit.codes); await call.message.answer("✏️ Tahrirlanadigan kino kodlarini vergul bilan yuboring:"); await call.answer()

@dp.message(BulkEdit.codes)
async def bulk_edit_codes(message,state):
    codes=[x.strip() for x in message.text.split(",") if x.strip()]
    if not codes: return await message.answer("❌ Kodlar topilmadi.")
    await state.update_data(codes=codes); await state.set_state(BulkEdit.field)
    await message.answer("Qaysi maydon? <code>title</code>, <code>description</code>, <code>genre</code>, <code>year</code>, <code>vip_only</code> (1=VIP, 0=oddiy)")

@dp.message(BulkEdit.field)
async def bulk_edit_field(message,state):
    field=message.text.strip().lower()
    if field not in {"title","description","genre","year","vip_only"}: return await message.answer("❌ Noto'g'ri maydon.")
    await state.update_data(field=field); await state.set_state(BulkEdit.value); await message.answer("✏️ Yangi qiymatni yuboring:")

@dp.message(BulkEdit.value)
async def bulk_edit_value(message,state):
    d=await state.get_data(); codes=d["codes"]; field=d["field"]; value=message.text.strip()
    q=','.join('?' for _ in codes)
    async with aiosqlite.connect(DB) as db:
        await db.execute(f"UPDATE movies SET {field}=? WHERE code IN ({q})",[value,*codes]); await db.commit()
    await log_action(message.from_user.id,"Ommaviy kino tahrirlandi",f"{field}: {','.join(codes)}")
    await state.clear(); await message.answer(f"✅ {len(codes)} ta kod uchun {field} yangilandi.")

# ============================================================
# ============================================================
# ============================================================
# BROADCAST
# ============================================================
@dp.callback_query(F.data=="broadcast_start")
async def broadcast_start(call,state):
    if not await admin_right(call.from_user.id,"broadcast"): return await call.answer("⛔",show_alert=True)
    await state.set_state(Broadcast.source); await call.message.answer("📨 Yuboriladigan xabarni shu yerga yuboring."); await call.answer()
@dp.message(Broadcast.source)
async def broadcast_source(message,state):
    await state.update_data(chat_id=message.chat.id,message_id=message.message_id); await state.set_state(Broadcast.button)
    await message.answer("🔘 Tugma kerak bo'lsa: <code>Matn | https://...</code>\nKerak bo'lmasa -")
@dp.message(Broadcast.button)
async def broadcast_do(message,state):
    d=await state.get_data(); button_text=button_url=None
    text=(message.text or "").strip()
    if text!="-":
        p=text.split("|",1)
        if len(p)!=2: return await message.answer("❌ Format noto'g'ri.")
        button_text,button_url=p[0].strip(),p[1].strip()
        if not button_text or not re.fullmatch(r"https?://\S+",button_url):
            return await message.answer("❌ Tugma uchun to'g'ri matn va http(s) link kiriting.")
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT id FROM users WHERE banned=0"); users=[r[0] for r in await cur.fetchall()]
    await state.update_data(button_text=button_text,button_url=button_url,recipient_count=len(users))
    await state.set_state(Broadcast.confirm)
    await message.answer(f"📨 <b>Ommaviy xabar tayyor</b>\nQabul qiluvchilar: {len(users)}\n\nHaqiqatan yuborilsinmi?",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yuborishni tasdiqlash",callback_data="broadcast_confirm"),
         InlineKeyboardButton(text="❌ Bekor qilish",callback_data="broadcast_cancel")]
    ]))

@dp.callback_query(F.data=="broadcast_confirm",Broadcast.confirm)
async def broadcast_confirm(call,state):
    if not await admin_right(call.from_user.id,"broadcast"):
        await state.clear()
        return await call.answer("⛔ Ruxsat yo'q",show_alert=True)
    d=await state.get_data()
    await state.clear()
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT id FROM users WHERE banned=0"); users=[r[0] for r in await cur.fetchall()]
    sent=failed=0
    for uid in users:
        try:
            mk=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=d["button_text"],url=d["button_url"])]]) if d.get("button_text") else None
            await bot.copy_message(uid,d["chat_id"],d["message_id"],reply_markup=mk); sent+=1
        except Exception as e:
            failed+=1
            logging.warning("Broadcast failed for %s: %s",uid,e)
        await asyncio.sleep(0.035)
    await log_action(call.from_user.id,"Broadcast yuborildi",f"sent={sent},failed={failed}")
    await call.message.answer(f"📨 Tarqatish tugadi.\n✅ {sent}\n❌ {failed}")
    await call.answer("Tarqatish yakunlandi")

@dp.callback_query(F.data=="broadcast_cancel",Broadcast.confirm)
async def broadcast_cancel(call,state):
    await state.clear()
    await call.answer("Bekor qilindi")
    await call.message.answer("🛑 Ommaviy xabar bekor qilindi. Hech kimga yuborilmadi.")

@dp.callback_query(F.data=="forward_broadcast_start")
async def forward_broadcast_start(call,state):
    if not await admin_right(call.from_user.id,"broadcast"): return await call.answer("⛔",show_alert=True)
    await state.set_state(ForwardBroadcast.source)
    await call.message.answer("↪️ Barcha a’zolarga forward qilinadigan xabarni shu yerga yuboring. Xabar aynan Telegram forward ko‘rinishida yuboriladi.")
    await call.answer()

@dp.message(ForwardBroadcast.source)
async def forward_broadcast_do(message,state):
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT id FROM users WHERE banned=0")
        users=[r[0] for r in await cur.fetchall()]
    await state.update_data(chat_id=message.chat.id,message_id=message.message_id,recipient_count=len(users))
    await state.set_state(ForwardBroadcast.confirm)
    await message.answer(f"↪️ <b>Forward xabar tayyor</b>\nQabul qiluvchilar: {len(users)}\n\nHaqiqatan forward qilinsinmi?",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Forward qilish",callback_data="forward_broadcast_confirm"),
         InlineKeyboardButton(text="❌ Bekor qilish",callback_data="forward_broadcast_cancel")]
    ]))

@dp.callback_query(F.data=="forward_broadcast_confirm",ForwardBroadcast.confirm)
async def forward_broadcast_confirm(call,state):
    if not await admin_right(call.from_user.id,"broadcast"):
        await state.clear()
        return await call.answer("⛔ Ruxsat yo'q",show_alert=True)
    d=await state.get_data()
    await state.clear()
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT id FROM users WHERE banned=0")
        users=[r[0] for r in await cur.fetchall()]
    sent=failed=0
    for uid in users:
        try:
            await bot.forward_message(chat_id=uid,from_chat_id=d["chat_id"],message_id=d["message_id"])
            sent+=1
        except Exception as e:
            failed+=1
            logging.warning("Forward broadcast failed for %s: %s",uid,e)
        await asyncio.sleep(0.035)
    await log_action(call.from_user.id,"Forward broadcast yuborildi",f"sent={sent},failed={failed}")
    await call.message.answer(f"↪️ Forward tugadi.\n✅ {sent}\n❌ {failed}")
    await call.answer("Forward yakunlandi")

@dp.callback_query(F.data=="forward_broadcast_cancel",ForwardBroadcast.confirm)
async def forward_broadcast_cancel(call,state):
    await state.clear()
    await call.answer("Bekor qilindi")
    await call.message.answer("🛑 Forward bekor qilindi. Hech kimga yuborilmadi.")

# ============================================================
# SUPPORT ADMIN
# ============================================================
@dp.callback_query(F.data=="support_admin")
async def support_admin(call):
    if not await admin_right(call.from_user.id,"support"): return await call.answer("⛔",show_alert=True)
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("""SELECT id,user_id,message,created_at FROM support_tickets
        WHERE status='open' ORDER BY id DESC LIMIT 30"""); rows=await cur.fetchall()
    if not rows: return await call.message.answer("📭 Ochiq murojaatlar yo'q.")
    for tid,uid,text,created in rows:
        await call.message.answer(f"🆘 <b>#{tid}</b>\n👤 <code>{uid}</code>\n{escape(text)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Javob",callback_data=f"support_reply:{uid}:{tid}")],
                [InlineKeyboardButton(text="✅ Yopish",callback_data=f"support_close:{tid}")]
            ]))
    await call.answer()

class SupportReply(StatesGroup): uid=State(); ticket=State(); text=State()
@dp.callback_query(F.data.startswith("support_reply:"))
async def support_reply(call,state):
    if not await admin_right(call.from_user.id,"support"): return await call.answer("⛔",show_alert=True)
    _,uid,tid=call.data.split(":"); await state.update_data(uid=int(uid),ticket=int(tid)); await state.set_state(SupportReply.text)
    await call.message.answer("↩️ Userga yuboriladigan javobni yozing."); await call.answer()
@dp.message(SupportReply.text)
async def support_reply_send(message,state):
    d=await state.get_data()
    try:
        await bot.send_message(d["uid"],f"🆘 <b>Support javobi:</b>\n\n{escape(message.text or '')}")
        async with aiosqlite.connect(DB) as db:
            await db.execute("UPDATE support_tickets SET status='answered',answered_at=? WHERE id=?",(datetime.now().isoformat(),d["ticket"])); await db.commit()
        await log_action(message.from_user.id,"Supportga javob berildi",f"ticket={d['ticket']}")
        await message.answer("✅ Javob yuborildi.")
    except: await message.answer("❌ Userga yuborib bo'lmadi.")
    await state.clear()

@dp.callback_query(F.data.startswith("support_close:"))
async def support_close(call):
    if not await admin_right(call.from_user.id,"support"): return await call.answer("⛔",show_alert=True)
    tid=int(call.data.split(":")[1])
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE support_tickets SET status='closed' WHERE id=?",(tid,)); await db.commit()
    await log_action(call.from_user.id,"Support yopildi",str(tid)); await call.answer("✅ Yopildi.")

# ============================================================
# ADMIN LOGS / STATS
# ============================================================
@dp.callback_query(F.data=="admin_logs")
async def admin_logs(call):
    if not await admin_right(call.from_user.id,"logs"): return await call.answer("⛔",show_alert=True)
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("SELECT admin_id,action,details,created_at FROM admin_logs ORDER BY id DESC LIMIT 50"); rows=await cur.fetchall()
    text="📝 <b>Admin Log</b>\n\n"
    for a,x,d,c in rows: text+=f"👤 <code>{a}</code>\n⚡ {escape(x)}\n📌 {escape(d)}\n🕐 {c}\n\n"
    await call.message.answer(text or "📭 Log bo'sh."); await call.answer()

@dp.callback_query(F.data=="advanced_stats")
async def stats(call):
    if not await admin_right(call.from_user.id,"stats"): return await call.answer("⛔",show_alert=True)
    async with aiosqlite.connect(DB) as db:
        async def one(sql):
            cur=await db.execute(sql); r=await cur.fetchone(); return r[0] if r else 0
        users=await one("SELECT COUNT(*) FROM users"); banned=await one("SELECT COUNT(*) FROM users WHERE banned=1")
        movies=await one("SELECT COUNT(*) FROM movies"); eps=await one("SELECT COUNT(*) FROM episodes")
        views=await one("SELECT COALESCE(SUM(views),0) FROM movies"); ev=await one("SELECT COALESCE(SUM(views),0) FROM episodes")
        vip=await one("SELECT COUNT(*) FROM users WHERE vip_until IS NOT NULL AND vip_until>datetime('now')")
        payments=await one("SELECT COUNT(*) FROM payments WHERE status='approved'")
        income=await one("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='approved'")
    await call.message.answer(f"""📊 <b>Statistika</b>
👥 Userlar: {users}
🚫 Banlangan: {banned}
🎬 Kinolar: {movies}
📺 Qismlar: {eps}
👁 Kino ko'rishlar: {views}
▶️ Qism ko'rishlar: {ev}
💎 Aktiv VIP: {vip}
🧾 Tasdiqlangan to'lovlar: {payments}
💰 Tushum: {income:,} so'm"""); await call.answer()

# ============================================================
# SMART NOTIFICATIONS
# ============================================================
async def notify_all(column,text):
    if column not in {"notify_movies","notify_episodes","notify_favorites","notify_vip","notify_announcements"}: return
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute(f"SELECT id FROM users WHERE banned=0 AND {column}=1"); users=[r[0] for r in await cur.fetchall()]
    for uid in users:
        try: await bot.send_message(uid,text)
        except: pass

async def vip_reminder_job():
    while True:
        try:
            now=datetime.now()
            async with aiosqlite.connect(DB) as db:
                cur=await db.execute("SELECT id,vip_until FROM users WHERE vip_until IS NOT NULL AND notify_vip=1")
                rows=await cur.fetchall()
            for uid,until in rows:
                try:
                    dt=datetime.fromisoformat(until); hours=(dt-now).total_seconds()/3600
                    if 23.5<=hours<=25.5 or 71.5<=hours<=73.5:
                        await bot.send_message(uid,f"🔔 💎 VIP muddatingiz {int(hours/24)+1} kun ichida tugaydi.")
                except: pass
        except Exception as e: logging.warning("VIP reminder: %s",e)
        await asyncio.sleep(3600)

# ============================================================
# AI WEB KINO QIDIRUV
# ============================================================
class AIWeb(StatesGroup): query=State()

@dp.callback_query(F.data=="ai_web_start")
async def ai_web_start(call,state):
    await state.set_state(AIWeb.query)
    await call.message.answer("🤖 <b>AI Kino qidiruv</b>\n\nKino nomini yozing. AI internetdan ma’lumot topib, qisqa ma’lumot beradi.\n\nMasalan: <code>Interstellar</code>")
    await call.answer()

@dp.message(AIWeb.query)
async def ai_web_query(message,state):
    query=(message.text or "").strip()
    if not query: return await message.answer("❌ Kino nomini yozing.")
    if not OPENAI_API_KEY:
        await state.clear(); return await message.answer("❌ OPENAI_API_KEY .env da sozlanmagan.")
    status=await message.answer("🌐🤖 AI web qidiruv ishlayapti...")
    try:
        payload={
            "model":AI_MODEL,
            "tools":[{"type":"web_search"}],
            "input":f"Kino haqida internetdan ishonchli ma’lumot top: {query}. O‘zbek tilida qisqa javob ber: nomi, yil, janr, reyting bo‘lsa, 2-3 gaplik mazmun. Faqat xavfsiz, umumiy kino ma’lumoti.",
            "max_output_tokens":700
        }
        def _call_web():
            req=urllib.request.Request("https://api.openai.com/v1/responses",data=json.dumps(payload).encode("utf-8"),headers={"Authorization":f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"},method="POST")
            try:
                with urllib.request.urlopen(req,timeout=90) as r: return json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                body=e.read().decode("utf-8",errors="ignore")
                raise RuntimeError(f"OpenAI API xatosi {e.code}: {body[:300]}")
        data=await asyncio.to_thread(_call_web)
        parts=[]
        for item in data.get("output",[]):
            for c in item.get("content",[]):
                if c.get("type") in {"output_text","text"} and c.get("text"): parts.append(c["text"])
        answer="".join(parts).strip()
        if not answer: raise RuntimeError("AI javob qaytarmadi")
        await status.edit_text("🤖 <b>AI Kino qidiruv</b>\n\n"+escape(answer))
    except Exception as e:
        logging.exception("AI web search failed")
        await status.edit_text("❌ AI web qidiruvda xatolik: <code>"+escape(str(e)[:400])+"</code>")
    finally:
        await state.clear()

@dp.callback_query(F.data=="ai_web_admin")
async def ai_web_admin(call):
    if not await admin_right(call.from_user.id,"movies"): return await call.answer("⛔",show_alert=True)
    await call.message.answer("🤖 <b>AI / Web</b>\n\n✅ Kino qiziq joyini AI orqali topish\n✅ 4 / 5 / 10 soniyalik preview\n✅ AI Kino qidiruv internet orqali ishlaydi\n\nModel: <code>"+escape(AI_MODEL)+"</code>\nAI kalit .env dagi <code>OPENAI_API_KEY</code> orqali olinadi.",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩️ Orqaga",callback_data="back_admin")]]))
    await call.answer()

@dp.callback_query(F.data=="back_admin")
async def back_admin(call):
    await call.message.answer("👑 <b>Admin panel</b>",reply_markup=admin_kb()); await call.answer()

# ============================================================
# START / CODE
# ============================================================
@dp.message(CommandStart())
async def start(message):
    await save_user(message)
    uid=message.from_user.id
    banned,reason=await is_banned(uid)
    if banned: return await message.answer(f"🚫 Siz botdan bloklangansiz.\nSabab: {escape(reason or '-')}")
    lang=await get_lang(uid)
    if lang not in T:
        return await message.answer(tr("uz","choose_lang"),reply_markup=lang_kb())
    if not await require_subscription(message):
        return
    parts=(message.text or "").split(maxsplit=1)
    if len(parts)==2 and parts[1].startswith("movie_"):
        code=parts[1][6:]
        async with aiosqlite.connect(DB) as db:
            cur=await db.execute("SELECT id,code,title,description,genre,year,media_type,file_id,views,vip_only,access_mode,created_at FROM movies WHERE code=?",(code,)); movie=await cur.fetchone()
        if movie: return await send_movie(message,movie)
    await message.answer(tr(lang,"welcome"),reply_markup=user_kb(lang))

@dp.message(Command("admin"))
async def admin_panel(message):
    await save_user(message)
    if not await admin_exists(message.from_user.id): return await message.answer("⛔ Siz admin emassiz.")
    await message.answer("👑 <b>Admin panel</b>",reply_markup=admin_kb())

@dp.message(F.text, F.chat.type == "private")
async def code_handler(message):
    # FSM handlers take precedence in aiogram.
    await save_user(message)
    uid=message.from_user.id; banned,reason=await is_banned(uid)
    if banned: return await message.answer(f"🚫 Siz bloklangansiz.\nSabab: {escape(reason or '-')}")
    if not await require_subscription(message): return
    code=message.text.strip()
    if not code.isdigit(): return
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute("""SELECT id,code,title,description,genre,year,media_type,file_id,views,vip_only,access_mode,created_at
        FROM movies WHERE code=?""",(code,)); movie=await cur.fetchone()
    if not movie: return await message.answer(tr(await get_lang(uid),"not_found"))
    await send_movie(message,movie)

# ================= WEB PANEL =================
def _web_role(request):
    key=request.headers.get("X-Panel-Key","") or request.query.get("key","")
    if WEB_OWNER_KEY and secrets.compare_digest(key,WEB_OWNER_KEY): return "owner"
    if WEB_ADMIN_KEY and secrets.compare_digest(key,WEB_ADMIN_KEY): return "admin"
    return None

async def web_panel(request):
    role=_web_role(request)
    if not role: return web.Response(status=401,text="Unauthorized. /panel?key=YOUR_KEY")
    async with aiosqlite.connect(DB) as db:
        u=(await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        m=(await (await db.execute("SELECT COUNT(*) FROM movies")).fetchone())[0]
        c=(await (await db.execute("SELECT COUNT(*) FROM channels")).fetchone())[0]
    key=escape(request.query.get("key",""),quote=True)
    custom_emoji_section=""
    if role=="owner":
        pack_name=escape(await get_setting("custom_emoji_pack"),quote=True)
        custom_emoji_section=f"""<section><h2>🎨 Custom emoji</h2><p>Telegram emoji to‘plami havolasi yoki nomini kiriting. Bo‘sh qoldirib saqlasangiz, custom emoji o‘chadi.</p><form method=post action='/panel/custom-emojis?key={key}'><input name=pack value="{pack_name}" placeholder='https://t.me/addemoji/emojiuzbek' style='width:65%'><button>To‘plamni saqlash</button></form></section>"""
    html=f"""<!doctype html><meta charset=utf-8><meta name=viewport content=width=device-width,initial-scale=1><title>Kino Bot Panel</title><style>body{{font:16px Arial;max-width:1100px;margin:auto;padding:20px}}input,button{{padding:10px;margin:4px}}.card{{display:inline-block;border:1px solid #ddd;border-radius:10px;padding:15px;margin:5px}}section{{border:1px solid #ddd;border-radius:12px;padding:15px;margin:15px 0}}</style><h1>🎬 Kino Bot Panel</h1><p>Role: <b>{role}</b></p><div class=card>👥 {u} users</div><div class=card>🎬 {m} movies</div><div class=card>📢 {c} channels</div><section><h2>📢 Majburiy kanal/guruh</h2><p>Qo‘shilgan kanal va guruhlar botdagi obuna oynasida foydalanuvchilarga ko‘rinadi. Bot kanal/guruhda admin bo‘lishi shart; yopiq kanal/guruh uchun taklif havolasi avtomatik yaratiladi.</p><form method=post action='/panel/channel?key={key}'><input name=title placeholder='Kanal nomi'><input name=chat_id placeholder='@kanal yoki -100...'><input name=username placeholder='username'><button>Qo‘shish</button></form></section>{custom_emoji_section}<section><h2>⚙️ Sozlamalar</h2><form method=post action='/panel/settings?key={key}'><input name=key_name placeholder='setting key'><input name=value placeholder='value'><button>Saqlash</button></form></section><section><h2>🎥 Katta video upload</h2><form method=post action='/panel/upload?key={key}' enctype=multipart/form-data><input name=code placeholder='Kino kodi'><input name=title placeholder='Kino nomi'><input type=file name=video><button>Serverga yuklash</button></form><p>Upload oqim bilan diskka yoziladi. Telegram orqali yuboriladigan fayllar esa Telegram Bot API limitlariga bog‘liq.</p></section>"""
    return web.Response(text=html,content_type="text/html")

async def web_channel(request):
    if _web_role(request) not in {"owner","admin"}: return web.Response(status=403,text="Forbidden")
    d=await request.post(); chat_id=str(d.get("chat_id") or "").strip()
    if not chat_id: return web.Response(status=400,text="chat_id required")
    try:
        chat=await bot.get_chat(chat_id)
    except TelegramAPIError as e:
        return web.Response(status=400,text=f"Telegram chatni topmadi: {e}")
    if chat.type not in ("channel","group","supergroup"):
        return web.Response(status=400,text="Chat kanal yoki guruh bo'lishi kerak")
    try:
        bot_member=await bot.get_chat_member(chat_id=chat.id,user_id=bot.id)
    except TelegramAPIError as e:
        return web.Response(status=400,text=f"Botning chatdagi huquqlarini tekshirib bo'lmadi: {e}")
    if bot_member.status not in ("administrator","creator"):
        return web.Response(status=400,text="Botni kanal/guruhga admin qilib qayta urinib ko'ring")
    username=chat.username or ""
    if username:
        invite_link=f"https://t.me/{username}"
        kind="public"
    else:
        try:
            invite_link=(await bot.create_chat_invite_link(chat_id=chat.id)).invite_link
        except TelegramAPIError as e:
            return web.Response(
                status=400,
                text=f"Yopiq kanal/guruh uchun taklif havolasi yaratilmadi. Botga a'zo taklif qilish huquqini bering: {e}",
            )
        kind="private"
    try:
        saved=await save_required_channel(
            str(chat.id),chat.title or str(chat.id),username,invite_link,kind,
        )
    except aiosqlite.IntegrityError:
        return web.Response(status=409,text="Channel already exists")
    if not saved:
        return web.Response(status=409,text=f"At most {MAX_REQUIRED_CHANNELS} required channels/groups are allowed")
    return web.Response(text="OK")

async def web_settings(request):
    if _web_role(request)!="owner": return web.Response(status=403,text="Owner only")
    d=await request.post(); k=str(d.get("key_name") or "").strip(); v=str(d.get("value") or "")
    if not k: return web.Response(status=400,text="key required")
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(k,v)); await db.commit()
    return web.Response(text="Saved")


async def web_custom_emojis(request):
    if _web_role(request)!="owner": return web.Response(status=403,text="Owner only")
    form=await request.post()
    pack=str(form.get("pack") or "").strip()
    if not pack:
        await set_setting("custom_emoji_pack","")
        CUSTOM_EMOJI_IDS.clear()
        return web.Response(text="Custom emoji to'plami o'chirildi.")
    try:
        pack_name=emoji_pack_name(pack)
    except ValueError as e:
        return web.Response(status=400,text=str(e))
    try:
        mapping=await fetch_custom_emoji_mapping(pack_name)
    except ValueError as e:
        return web.Response(status=400,text=str(e))
    except TelegramAPIError as e:
        logging.warning("Custom emoji pack load failed for %s: %s",pack_name,e)
        return web.Response(status=502,text=f"Telegram to'plamni yuklay olmadi: {e}")
    await set_setting("custom_emoji_pack",pack_name)
    CUSTOM_EMOJI_IDS.clear()
    CUSTOM_EMOJI_IDS.update(mapping)
    return web.Response(text=f"Custom emoji to'plami saqlandi ({len(mapping)} ta emoji).")


async def web_upload(request):
    if _web_role(request) not in {"owner","admin"}: return web.Response(status=403,text="Forbidden")
    reader=await request.multipart(); fields={}; path=None; total=0
    async for part in reader:
        if part.name=="video":
            Path("web_uploads").mkdir(exist_ok=True); path=Path("web_uploads")/(datetime.now().strftime("%Y%m%d_%H%M%S_")+secrets.token_hex(4)+"_"+Path(part.filename or "upload.mp4").name)
            with path.open("wb") as f:
                while True:
                    chunk=await part.read_chunk(1024*1024)
                    if not chunk: break
                    total+=len(chunk)
                    if total>MAX_UPLOAD_BYTES: path.unlink(missing_ok=True); return web.Response(status=413,text="MAX_UPLOAD_BYTES oshdi")
                    f.write(chunk)
        else: fields[part.name]=await part.text()
    if not path: return web.Response(status=400,text="Video topilmadi")
    path.with_suffix(path.suffix+".json").write_text(json.dumps(fields,ensure_ascii=False),encoding="utf-8")
    return web.Response(text=f"Uploaded: {path}")

async def start_web_server():
    app=web.Application(client_max_size=MAX_UPLOAD_BYTES); app.router.add_get("/healthz",web_health); app.router.add_get("/panel",web_panel); app.router.add_post("/panel/channel",web_channel); app.router.add_post("/panel/settings",web_settings); app.router.add_post("/panel/custom-emojis",web_custom_emojis); app.router.add_post("/panel/upload",web_upload)
    runner=web.AppRunner(app); await runner.setup(); await web.TCPSite(runner,WEB_HOST,WEB_PORT).start(); return runner

async def web_health(request):
    return web.Response(text="ok")

async def main():
    global CUSTOM_EMOJI_IDS
    await db_init()
    saved_pack=await get_setting("custom_emoji_pack")
    if saved_pack:
        try:
            pack_name=emoji_pack_name(saved_pack)
            CUSTOM_EMOJI_IDS=await fetch_custom_emoji_mapping(pack_name)
        except (ValueError,TelegramAPIError) as e:
            logging.error("Saved custom emoji pack could not be loaded: %s",e)
    web_runner=await start_web_server()
    await bot.delete_my_commands()
    await bot.set_my_commands([
        BotCommand(command="start",description="Botni boshlash"),
        BotCommand(command="admin",description="Admin panel")
    ], scope=BotCommandScopeAllPrivateChats())
    try:
        await dp.start_polling(bot)
    finally:
        await web_runner.cleanup()

if __name__=="__main__":
    asyncio.run(main())
