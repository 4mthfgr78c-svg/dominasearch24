import sqlite3
import random
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "8810784260:AAFsTF1xOWt5jI1A1utJ-xyO5nUd_YtncsU"
ADMIN_USER_ID = 8117530336  # ЗАМЕНИТЕ НА ВАШ ID

# ID кастомных эмодзи (получить через @getidsbot, если есть Premium)
# Если не заданы — кнопки будут без иконок
DOMINA_EMOJI_ID = None      # например "1234567890123456789"
DOG_EMOJI_ID = None
SUCCESS_EMOJI_ID = None
DANGER_EMOJI_ID = None

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ---------- БАЗА ДАННЫХ ----------
def init_db():
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        name TEXT,
        gender TEXT,
        bio TEXT,
        photo_file_id TEXT,
        age_verified BOOLEAN DEFAULT 0,
        is_domina BOOLEAN DEFAULT 0,
        domina_id INTEGER UNIQUE,
        registered BOOLEAN DEFAULT 0
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS likes (
        from_user INTEGER,
        to_user INTEGER,
        status TEXT,
        PRIMARY KEY (from_user, to_user)
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS dislikes (
        from_user INTEGER,
        to_user INTEGER,
        PRIMARY KEY (from_user, to_user)
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS matches (
        user1 INTEGER,
        user2 INTEGER,
        PRIMARY KEY (user1, user2)
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user INTEGER,
        to_user INTEGER,
        text TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

init_db()

# ---------- СОСТОЯНИЯ ----------
class RegState(StatesGroup):
    age_confirm = State()
    name = State()
    photo = State()
    gender = State()
    bio = State()

class EditState(StatesGroup):
    choice = State()
    new_name = State()
    new_bio = State()
    new_photo = State()
    new_gender = State()

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
def generate_domina_id():
    while True:
        new_id = random.randint(100000, 999999)
        conn = sqlite3.connect('dating.db')
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE domina_id=?", (new_id,))
        if not cur.fetchone():
            conn.close()
            return new_id
        conn.close()

def is_admin(user_id):
    return user_id == ADMIN_USER_ID

def get_role_text(is_domina: bool, domina_id: int = None) -> str:
    if is_domina:
        return f"👠 Домина\n🏷 ID: {domina_id}"
    else:
        return "🦴 Пёс"

def get_greeting(is_domina: bool, name: str) -> str:
    if is_domina:
        return f"Приветствую Вас, Госпожа {name}! 👠"
    else:
        return f"Йоу, {name}! Слушай сюда, пёсик. 🦴"

def get_respectful_prefix(is_domina: bool) -> str:
    return "Уважаемая " if is_domina else ""

async def show_main_menu(message: types.Message, user_id: int = None):
    if user_id is None:
        user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT is_domina FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    is_domina = row[0] if row else False
    # Кнопки с возможными кастомными эмодзи
    def btn(text, emoji_id=None):
        return KeyboardButton(text=text, icon_custom_emoji_id=emoji_id) if emoji_id else KeyboardButton(text=text)
    kb = ReplyKeyboardMarkup(keyboard=[
        [btn("🔍 Искать", DOMINA_EMOJI_ID if is_domina else DOG_EMOJI_ID)],
        [btn("❤️ Взаимные симпатии"), btn("📨 Сообщения")],
        [btn("👤 Моя анкета"), btn("⚙️ Сбросить дизлайки")]
    ], resize_keyboard=True)
    await message.answer("Главное меню:", reply_markup=kb)

# ---------- СТАРТ И РЕГИСТРАЦИЯ ----------
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT registered FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        await show_main_menu(message, user_id)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, мне есть 18+", callback_data="age_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="age_no")]
    ])
    await message.answer("🔞 Вам есть 18 лет?", reply_markup=kb)
    await state.set_state(RegState.age_confirm)

@dp.callback_query(RegState.age_confirm, F.data == "age_yes")
async def age_yes(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите ваше имя (как хотите, чтобы к вам обращались):")
    await state.update_data(age_verified=True)
    await state.set_state(RegState.name)
    await callback.answer()

@dp.callback_query(RegState.age_confirm, F.data == "age_no")
async def age_no(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("До свидания. Бот доступен только для пользователей старше 18 лет.")
    await state.clear()
    await callback.answer()

@dp.message(RegState.name)
async def reg_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Слишком короткое имя. Напишите хотя бы 2 символа.")
        return
    await state.update_data(name=name)
    await message.answer("Отправьте ваше фото (одно, самое лучшее):")
    await state.set_state(RegState.photo)

@dp.message(RegState.photo, F.photo)
async def reg_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1].file_id
    await state.update_data(photo=photo)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="М"), KeyboardButton(text="Ж")]], resize_keyboard=True)
    await message.answer("Ваш пол:", reply_markup=kb)
    await state.set_state(RegState.gender)

@dp.message(RegState.photo)
async def reg_photo_error(message: types.Message):
    await message.answer("Пожалуйста, отправьте фото (изображение).")

@dp.message(RegState.gender, F.text.in_(["М", "Ж"]))
async def reg_gender(message: types.Message, state: FSMContext):
    gender = "м" if message.text == "М" else "ж"
    await state.update_data(gender=gender)
    await message.answer("Расскажите немного о себе (хобби, интересы):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(RegState.bio)

@dp.message(RegState.gender)
async def reg_gender_error(message: types.Message):
    await message.answer("Пожалуйста, выберите пол кнопкой: М или Ж")

@dp.message(RegState.bio)
async def reg_bio(message: types.Message, state: FSMContext):
    bio = message.text.strip()
    if len(bio) < 10:
        await message.answer("Напишите хотя бы 10 символов о себе.")
        return
    data = await state.get_data()
    user_id = message.from_user.id
    username = message.from_user.username or ""
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute('''INSERT INTO users 
                  (user_id, username, name, gender, bio, photo_file_id, age_verified, is_domina, registered) 
                  VALUES (?,?,?,?,?,?,?,?,1)''',
                (user_id, username, data['name'], data['gender'], bio, data['photo'], data['age_verified'], False))
    conn.commit()
    conn.close()
    await message.answer("✅ Регистрация завершена! Вы — Пёс (обычный пользователь).\nАдмин может выдать вам статус Домины позже.")
    await show_main_menu(message, user_id)
    await state.clear()

# ---------- РЕДАКТИРОВАНИЕ АНКЕТЫ ----------
@dp.message(F.text == "👤 Моя анкета")
async def my_profile(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT name, gender, bio, photo_file_id, is_domina, domina_id FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        await message.answer("Вы не зарегистрированы. /start")
        return
    name, gender, bio, photo_id, is_domina, domina_id = row
    gender_str = "Мужчина" if gender == "м" else "Женщина"
    role_text = get_role_text(is_domina, domina_id)
    greeting = get_greeting(is_domina, name)
    caption = f"{greeting}\n