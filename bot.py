import sqlite3
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, 
    InlineKeyboardButton, WebAppInfo, LabeledPrice, PreCheckoutQuery
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ==================== КОНФИГУРАЦИЯ ====================
TOKEN = "8308059482:AAF6vQVcBOuKPYCGx27cXvjCDq-USSYz36o"
OPENROUTER_API_KEY = "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"
ADMIN_ID = 8196658213  # Твой UID

WEB_APP_URL = "https://example.com/index.html" # Замени на реальную HTTPS ссылку!
PRICE_XTR = 100  
DB_NAME = "vylazka_users.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

class AuthForm(StatesGroup):
    waiting_for_api = State()


# ==================== БАЗА ДАННЫХ ====================
def db_init():
    with sqlite3.connect(DB_NAME) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                api_key TEXT,
                has_access INTEGER DEFAULT 0,
                joined_at TEXT
            )
        """)
        try: db.execute("ALTER TABLE users ADD COLUMN api_key TEXT")
        except sqlite3.OperationalError: pass
        db.commit()

def get_user_data(user_id: int):
    with sqlite3.connect(DB_NAME) as db:
        cur = db.execute("SELECT api_key, has_access FROM users WHERE user_id = ?", (user_id,))
        return cur.fetchone()

def register_user(u):
    with sqlite3.connect(DB_NAME) as db:
        db.execute("""
            INSERT OR IGNORE INTO users (user_id, username, full_name, api_key, has_access, joined_at)
            VALUES (?, ?, ?, NULL, 0, ?)
        """, (u.id, u.username, u.full_name, datetime.now().isoformat()))
        db.commit()

def save_user_api(user_id: int, api_key: str):
    with sqlite3.connect(DB_NAME) as db:
        db.execute("UPDATE users SET api_key = ?, has_access = 1 WHERE user_id = ?", (api_key, user_id))
        db.commit()

def get_stats():
    with sqlite3.connect(DB_NAME) as db:
        total = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active = db.execute("SELECT COUNT(*) FROM users WHERE has_access = 1").fetchone()[0]
        return total, active


# ==================== КЛАВИАТУРЫ ====================
def kb_play(api_key: str):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🔦 ПОДКЛЮЧИТЬСЯ К БУНКЕРУ", 
            web_app=WebAppInfo(url=f"{WEB_APP_URL}?api={api_key}")
        )
    ]])

def kb_auth():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Ввести свой OpenRouter API", callback_data="enter_api")],
        [InlineKeyboardButton(text=f"⭐️ Купить готовый ключ системы ({PRICE_XTR} ⭐️)", callback_data="buy_access")],
        [InlineKeyboardButton(text="❓ Что за игра?", callback_data="about")]
    ])


# ==================== ТЕКСТЫ ====================
TEXT_INTRO = """
🔦 **ПЕРЕХВАТ ЛОКАЛЬНОЙ ЧАСТОТЫ**

Вы подключились к закрытому чату группы из 14 студентов. Несколько часов назад они спустились в заброшенный советский бункер. Сейчас связь с ними обрывается.

**Ваш телефон — их единственная нить к спасению.** Сюжет генерируется нейросетью в реальном времени под ваш стиль общения. 

⚠️ *Для синхронизации нейросети с сессией требуется шлюз OpenRouter.*
"""

TEXT_ABOUT = """
🧠 **ПАРАМЕТРЫ СИСТЕМЫ:**

1. **Никаких скриптов:** ИИ-режиссер на лету решает, кто выживет, основываясь на ваших ответах.
2. **Имитация Telegram:** Полное погружение в интерфейс чата.
3. **Бесплатный режим:** Вы можете получить ключ бесплатно на `openrouter.ai` и вставить его сюда.

*При покупке за Звезды выдается вечный системный ключ.*
"""


# ==================== ХЭНДЛЕРЫ ====================

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    register_user(message.from_user)
    
    if message.from_user.id == ADMIN_ID:
        save_user_api(ADMIN_ID, OPENROUTER_API_KEY)
        await message.answer("👑 **Авторизация создателя подтверждена.**", reply_markup=kb_play(OPENROUTER_API_KEY))
        return

    data = get_user_data(message.from_user.id)
    if data and data[1] == 1 and data[0]:
        await message.answer("📡 **Связь с объектом восстановлена.** Они ждут.", reply_markup=kb_play(data[0]))
    else:
        await message.answer(TEXT_INTRO, parse_mode="Markdown", reply_markup=kb_auth())


@dp.callback_query(F.data == "about")
async def cb_about(call: CallbackQuery):
    await call.message.edit_text(TEXT_ABOUT, parse_mode="Markdown", reply_markup=kb_auth())
    await call.answer()


@dp.callback_query(F.data == "enter_api")
async def cb_enter_api(call: CallbackQuery, state: FSMContext):
    await state.set_state(AuthForm.waiting_for_api)
    await call.message.edit_text(
        "🔑 **ВВОД API-КЛЮЧА**\n\n"
        "Отправьте следующим сообщением ваш ключ от OpenRouter (начинается на `sk-or-v1-...`).\n\n"
        "*Получить его бесплатно можно за 1 минуту на openrouter.ai (Settings -> Keys)*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Отмена", callback_data="cancel")]])
    )
    await call.answer()


@dp.callback_query(F.data == "cancel")
async def cb_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(TEXT_INTRO, parse_mode="Markdown", reply_markup=kb_auth())


@dp.message(AuthForm.waiting_for_api)
async def process_api(message: Message, state: FSMContext):
    key = message.text.strip()
    if not key.startswith("sk-or-"):
        await message.answer("⚠️ Неверный формат ключа. Он должен начинаться на `sk-or-v1-...`\nПопробуйте еще раз или нажмите /start")
        return
        
    save_user_api(message.from_user.id, key)
    await state.clear()
    await message.answer("✅ **ШЛЮЗ НАСТРОЕН.** Канал связи открыт.", parse_mode="Markdown", reply_markup=kb_play(key))


@dp.callback_query(F.data == "buy_access")
async def cb_buy(call: CallbackQuery):
    await bot.send_invoice(
        chat_id=call.message.chat.id,
        title="Декодер частоты «Объект-404»",
        description="Выделенный нейросетевой ключ для игры",
        payload="paid_api",
        currency="XTR",
        prices=[LabeledPrice(label="Ключ системы", amount=PRICE_XTR)]
    )
    await call.answer()


@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@dp.message(F.successful_payment)
async def on_pay_success(message: Message):
    master = OPENROUTER_API_KEY
    save_user_api(message.from_user.id, master)
    
    await message.answer(
        f"🔓 **ОПЛАТА ПОЛУЧЕНА. ДОСТУП РАЗРЕШЕН.**\n\n"
        f"Ваш персональный системный API-ключ:\n"
        f"`{master}`\n\n"
        f"*Он автоматически интегрирован в кнопку ниже. Скопируйте ключ, если захотите продолжить сессию из обычного браузера.*",
        parse_mode="Markdown",
        reply_markup=kb_play(master)
    )


# ==================== АДМИНКА ====================
@dp.message(Command("stats"))
async def adm_stats(m: Message):
    if m.from_user.id != ADMIN_ID: return
    tot, act = get_stats()
    await m.answer(f"📊 **База Бункера:**\nВсего нажавших /start: `{tot}`\nС готовым ключом: `{act}`", parse_mode="Markdown")

@dp.message(Command("give"))
async def adm_give(m: Message):
    if m.from_user.id != ADMIN_ID: return
    try:
        tid = int(m.text.split()[1])
        save_user_api(tid, OPENROUTER_API_KEY)
        await m.answer(f"✅ Юзеру `{tid}` прописан системный ключ.")
    except: await m.answer("Формат: `/give 123456789`")

async def main():
    db_init()
    logging.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
