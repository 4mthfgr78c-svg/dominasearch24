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
        photo_file_id TEXT,
        age_verified BOOLEAN DEFAULT 0,
        is_domina BOOLEAN DEFAULT 0,
        domina_id INTEGER UNIQUE,
        registered BOOLEAN DEFAULT 0,
        domina_bio TEXT,
        dog_bio TEXT
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
    role_choice = State()
    domina_bio = State()
    dog_bio = State()

class EditState(StatesGroup):
    choice = State()
    new_name = State()
    new_gender = State()
    new_photo = State()
    new_domina_bio = State()
    new_dog_bio = State()

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

async def show_main_menu(message: types.Message, user_id: int = None):
    if user_id is None:
        user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT is_domina FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    is_domina = row[0] if row else False
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔍 Искать")],
        [KeyboardButton(text="❤️ Взаимные симпатии"), KeyboardButton(text="📨 Сообщения")],
        [KeyboardButton(text="👤 Моя анкета"), KeyboardButton(text="⚙️ Сбросить дизлайки")]
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

    await message.answer(
        "👑 *Добро пожаловать в официальный бот фемдом-комьюнити!* 👑\n\n"
        "Этот бот создан @dominamilla специально для знакомств в стиле FemDom.\n"
        "Здесь Домины и Псы могут найти друг друга в безопасной среде.\n\n"
        "🔞 *Вам есть 18+?*\n"
        "Пожалуйста, подтвердите возраст.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, мне есть 18+", callback_data="age_yes")],
            [InlineKeyboardButton(text="❌ Нет", callback_data="age_no")]
        ])
    )
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
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👠 Я Домина", callback_data="role_domina")],
        [InlineKeyboardButton(text="🦴 Я Пёс", callback_data="role_dog")]
    ])
    await message.answer("Вы регистрируетесь как Домина или Пёс?\n(Статус Домины позже подтвердит администратор)", reply_markup=kb)
    await state.set_state(RegState.role_choice)
    await message.answer("Пол сохранён.", reply_markup=ReplyKeyboardRemove())

@dp.callback_query(RegState.role_choice, F.data.in_(["role_domina", "role_dog"]))
async def reg_role(callback: types.CallbackQuery, state: FSMContext):
    role = callback.data.split("_")[1]
    await state.update_data(requested_role=role)
    if role == "domina":
        await callback.message.edit_text(
            "Расскажите о себе как о Домине:\n"
            "- Как давно в теме?\n"
            "- Что практикуете?\n"
            "- Ваши ожидания от Пса\n"
            "(Можете использовать эмодзи)"
        )
        await state.set_state(RegState.domina_bio)
    else:
        await callback.message.edit_text(
            "Расскажите о себе как о Псе:\n"
            "- Ваши табу, фетиши, игрушки\n"
            "- Что ищете в Домине\n"
            "(Можете использовать эмодзи)"
        )
        await state.set_state(RegState.dog_bio)
    await callback.answer()

@dp.message(RegState.domina_bio)
async def reg_domina_bio(message: types.Message, state: FSMContext):
    bio = message.text.strip()
    if len(bio) < 20:
        await message.answer("Пожалуйста, напишите подробнее (минимум 20 символов).")
        return
    await state.update_data(domina_bio=bio)
    await finish_registration(message, state)

@dp.message(RegState.dog_bio)
async def reg_dog_bio(message: types.Message, state: FSMContext):
    bio = message.text.strip()
    if len(bio) < 20:
        await message.answer("Пожалуйста, напишите подробнее (минимум 20 символов).")
        return
    await state.update_data(dog_bio=bio)
    await finish_registration(message, state)

async def finish_registration(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    username = message.from_user.username or ""
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute('''INSERT INTO users 
                  (user_id, username, name, gender, photo_file_id, age_verified, is_domina, registered, domina_bio, dog_bio) 
                  VALUES (?,?,?,?,?,?,?,?,?,?)''',
                (user_id, username, data['name'], data['gender'], data['photo'], data['age_verified'],
                 False, 1, data.get('domina_bio', ''), data.get('dog_bio', '')))
    conn.commit()
    conn.close()
    await message.answer(
        "✅ Регистрация завершена! Вы зарегистрированы как Пёс (если выбрали Домину — статус выдаст админ).\n"
        "Админ @dominamilla может выдать вам статус Домины после проверки.\n"
        "Теперь вы можете искать анкеты."
    )
    await show_main_menu(message, user_id)
    await state.clear()

# ---------- АДМИН-КОМАНДЫ ----------
@dp.message(F.text.startswith("/make_domina"))
async def make_domina(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("Нет прав.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /make_domina @username")
        return
    username = parts[1].lstrip('@')
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id, is_domina FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    if not row:
        await message.answer(f"Пользователь @{username} не найден.")
        conn.close()
        return
    user_id, is_domina = row
    if is_domina:
        await message.answer(f"@{username} уже является Доминой.")
        conn.close()
        return
    domina_id = generate_domina_id()
    cur.execute("UPDATE users SET is_domina=1, domina_id=? WHERE user_id=?", (domina_id, user_id))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Пользователю @{username} выдан статус Домины с ID {domina_id}.")
    try:
        await bot.send_message(user_id, f"🎉 Поздравляем! Админ выдал вам статус Домины. Ваш DominaID: {domina_id}.\nТеперь вы видите анкеты псов, а псы видят вас.")
    except:
        pass

@dp.message(F.text.startswith("/remove_domina"))
async def remove_domina(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /remove_domina @username")
        return
    username = parts[1].lstrip('@')
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_domina=0, domina_id=NULL WHERE username=?", (username,))
    conn.commit()
    conn.close()
    await message.answer(f"Статус Домины удалён у @{username}.")

@dp.message(F.text == "/list_dominas")
async def list_dominas(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, name, domina_id FROM users WHERE is_domina=1")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        await message.answer("Нет Домин.")
        return
    text = "👠 Список Домин:\n"
    for uid, uname, name, did in rows:
        text += f"ID {did} — {name} (@{uname})\n"
    await message.answer(text)

@dp.message(F.text.startswith("/checkid "))
async def check_id(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /checkid 123456")
        return
    try:
        did = int(parts[1])
    except:
        await message.answer("ID должен быть числом.")
        return
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT name FROM users WHERE is_domina=1 AND domina_id=?", (did,))
    row = cur.fetchone()
    conn.close()
    if row:
        await message.answer(f"👠 Домина {row[0]} (ID {did}) существует.")
    else:
        await message.answer("Домина с таким ID не найдена.")

# ---------- ПОИСК АНКЕТ ----------
@dp.message(F.text == "🔍 Искать")
async def search(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT is_domina FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        await message.answer("Сначала /start")
        conn.close()
        return
    my_role = row[0]  # 1 = Домина, 0 = Пёс
    if my_role == 1:
        # Домина ищет всех псов
        condition = "is_domina = 0"
    else:
        # Пёс ищет только верифицированных домин
        condition = "is_domina = 1"
    cur.execute(f'''
        SELECT user_id, name, photo_file_id, username, is_domina, domina_id, domina_bio, dog_bio
        FROM users
        WHERE {condition} AND user_id != ?
          AND user_id NOT IN (SELECT to_user FROM likes WHERE from_user=?)
          AND user_id NOT IN (SELECT to_user FROM dislikes WHERE from_user=?)
          AND user_id NOT IN (SELECT user2 FROM matches WHERE user1=?)
          AND user_id NOT IN (SELECT user1 FROM matches WHERE user2=?)
    ''', (user_id, user_id, user_id, user_id, user_id))
    candidates = cur.fetchall()
    conn.close()
    if not candidates:
        await message.answer("Нет новых анкет.")
        return
    if not hasattr(dp, "temp_candidates"):
        dp.temp_candidates = {}
    dp.temp_candidates[user_id] = candidates
    await show_candidate(message, candidates, 0)

async def show_candidate(message: types.Message, candidates, index):
    if index >= len(candidates):
        await message.answer("Анкеты закончились.")
        return
    data = candidates[index]
    user_id, name, photo_id, username, is_domina, domina_id, domina_bio, dog_bio = data
    if is_domina:
        bio_text = domina_bio or "Нет описания"
        role_text = f"👠 Домина (ID {domina_id})"
    else:
        bio_text = dog_bio or "Нет описания"
        role_text = "🦴 Пёс"
    text = f"👤 {name}\n{role_text}\n\n📝 {bio_text}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❤️ Лайк", callback_data=f"like_{user_id}"),
         InlineKeyboardButton(text="👎 Дизлайк", callback_data=f"dislike_{user_id}")],
        [InlineKeyboardButton(text="➡️ Следующая", callback_data=f"next_{index+1}")]
    ])
    await message.answer_photo(photo=photo_id, caption=text, reply_markup=kb)

@dp.callback_query(F.data.startswith("next_"))
async def next_candidate(call: types.CallbackQuery):
    index = int(call.data.split("_")[1])
    candidates = dp.temp_candidates.get(call.from_user.id, [])
    await call.message.delete()
    await show_candidate(call.message, candidates, index)
    await call.answer()

@dp.callback_query(F.data.startswith("like_"))
async def like(call: types.CallbackQuery):
    from_user = call.from_user.id
    to_user = int(call.data.split("_")[1])
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM likes WHERE from_user=? AND to_user=?", (to_user, from_user))
    mutual = cur.fetchone()
    cur.execute("INSERT OR REPLACE INTO likes (from_user, to_user, status) VALUES (?,?,?)",
                (from_user, to_user, 'pending'))
    conn.commit()
    if mutual:
        cur.execute("UPDATE likes SET status='matched' WHERE (from_user=? AND to_user=?) OR (from_user=? AND to_user=?)",
                    (from_user, to_user, to_user, from_user))
        cur.execute("INSERT OR IGNORE INTO matches (user1, user2) VALUES (?,?)",
                    (min(from_user, to_user), max(from_user, to_user)))
        conn.commit()
        await call.message.answer("🎉 Взаимная симпатия! Теперь вы можете общаться в разделе «Взаимные симпатии».")
        await bot.send_message(to_user, f"У вас взаимная симпатия с @{call.from_user.username}!")
    else:
        await call.answer("Лайк отправлен! Если будет взаимность, мы сообщим.")
    conn.close()
    await call.message.delete()
    candidates = dp.temp_candidates.get(call.from_user.id, [])
    await show_candidate(call.message, candidates, 0)
    await call.answer()

@dp.callback_query(F.data.startswith("dislike_"))
async def dislike(call: types.CallbackQuery):
    from_user = call.from_user.id
    to_user = int(call.data.split("_")[1])
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO dislikes (from_user, to_user) VALUES (?,?)", (from_user, to_user))
    conn.commit()
    conn.close()
    await call.answer("👎 Анкета убрана, больше не покажется.")
    await call.message.delete()
    candidates = dp.temp_candidates.get(call.from_user.id, [])
    await show_candidate(call.message, candidates, 0)

# ---------- ВЗАИМНЫЕ СИМПАТИИ ----------
@dp.message(F.text == "❤️ Взаимные симпатии")
async def mutual_matches(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT user2 FROM matches WHERE user1=?
        UNION
        SELECT user1 FROM matches WHERE user2=?
    ''', (user_id, user_id))
    matches = cur.fetchall()
    if not matches:
        await message.answer("Пока нет взаимных симпатий.")
        conn.close()
        return
    text = "Ваши взаимки:\n"
    kb_buttons = []
    for (match_id,) in matches:
        cur.execute("SELECT name, username, is_domina FROM users WHERE user_id=?", (match_id,))
        name, username, is_domina = cur.fetchone()
        role = "👠" if is_domina else "🦴"
        text += f"- {role} {name} (@{username})\n"
        kb_buttons.append([InlineKeyboardButton(text=f"💬 Написать {name}", callback_data=f"chat_{match_id}")])
    conn.close()
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await message.answer(text, reply_markup=kb)

# ---------- ЧАТ ----------
@dp.callback_query(F.data.startswith("chat_"))
async def open_chat(call: types.CallbackQuery):
    partner_id = int(call.data.split("_")[1])
    if not hasattr(dp, "active_chats"):
        dp.active_chats = {}
    dp.active_chats[call.from_user.id] = partner_id
    await call.message.answer("Вы открыли диалог. Напишите сообщение собеседнику.\nЧтобы закончить, нажмите /endchat")
    await call.answer()

@dp.message(F.text, lambda msg: hasattr(dp, "active_chats") and msg.from_user.id in dp.active_chats)
async def send_message(message: types.Message):
    to_user = dp.active_chats[message.from_user.id]
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM matches WHERE (user1=? AND user2=?) OR (user1=? AND user2=?)",
                (message.from_user.id, to_user, to_user, message.from_user.id))
    if not cur.fetchone():
        del dp.active_chats[message.from_user.id]
        await message.answer("Взаимная симпатия удалена или истекла.")
        conn.close()
        return
    cur.execute("INSERT INTO messages (from_user, to_user, text) VALUES (?,?,?)",
                (message.from_user.id, to_user, message.text))
    conn.commit()
    await bot.send_message(to_user, f"💬 Сообщение от @{message.from_user.username}:\n{message.text}")
    await message.answer("✅ Сообщение отправлено.")
    conn.close()

@dp.message(F.text == "/endchat")
async def end_chat(message: types.Message):
    if hasattr(dp, "active_chats") and message.from_user.id in dp.active_chats:
        del dp.active_chats[message.from_user.id]
        await message.answer("Диалог закрыт. Используйте меню для новых чатов.")

@dp.message(F.text == "📨 Сообщения")
async def show_messages(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT from_user, to_user, text, timestamp FROM messages
        WHERE from_user=? OR to_user=?
        ORDER BY timestamp DESC LIMIT 20
    ''', (user_id, user_id))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        await message.answer("Нет сообщений.")
        return
    text = "📜 Последние сообщения:\n\n"
    for from_u, to_u, msg_text, ts in reversed(rows):
        other = to_u if from_u == user_id else from_u
        direction = "→" if from_u == user_id else "←"
        text += f"{direction} {other}: {msg_text[:50]}\n"
    await message.answer(text)

# ---------- СБРОС ДИЗЛАЙКОВ ----------
@dp.message(F.text == "⚙️ Сбросить дизлайки")
async def reset_dislikes(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM dislikes WHERE from_user=?", (user_id,))
    conn.commit()
    conn.close()
    await message.answer("✅ Список дизлайков очищен. Теперь ранее отклонённые анкеты снова будут показываться.")

# ---------- МОЯ АНКЕТА ----------
@dp.message(F.text == "👤 Моя анкета")
async def my_profile(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT name, gender, photo_file_id, is_domina, domina_id, domina_bio, dog_bio FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        await message.answer("Вы не зарегистрированы. /start")
        return
    name, gender, photo_id, is_domina, domina_id, domina_bio, dog_bio = row
    gender_str = "Мужчина" if gender == "м" else "Женщина"
    role_text = get_role_text(is_domina, domina_id)
    greeting = get_greeting(is_domina, name)
    if is_domina:
        bio_text = domina_bio or "Нет описания"
    else:
        bio_text = dog_bio or "Нет описания"
    caption = f"{greeting}\n{role_text}\n\nПол: {gender_str}\n\n📝 {bio_text}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать анкету", callback_data="edit_profile")]
    ])
    await message.answer_photo(photo=photo_id, caption=caption, reply_markup=kb)

# ---------- РЕДАКТИРОВАНИЕ ----------
@dp.callback_query(F.data == "edit_profile")
async def edit_profile_start(call: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Имя", callback_data="edit_name")],
        [InlineKeyboardButton(text="Пол", callback_data="edit_gender")],
        [InlineKeyboardButton(text="Фото", callback_data="edit_photo")],
        [InlineKeyboardButton(text="Описание", callback_data="edit_bio")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="edit_cancel")]
    ])
    await call.message.answer("Что хотите изменить?", reply_markup=kb)
    await state.set_state(EditState.choice)
    await call.answer()

@dp.callback_query(EditState.choice, F.data == "edit_name")
async def edit_name(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Введите новое имя:")
    await state.set_state(EditState.new_name)
    await call.answer()

@dp.message(EditState.new_name)
async def update_name(message: types.Message, state: FSMContext):
    new_name = message.text.strip()
    if len(new_name) < 2:
        await message.answer("Слишком короткое имя.")
        return
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET name=? WHERE user_id=?", (new_name, user_id))
    conn.commit()
    conn.close()
    await message.answer("Имя обновлено!")
    await state.clear()
    await my_profile(message)

@dp.callback_query(EditState.choice, F.data == "edit_gender")
async def edit_gender(call: types.CallbackQuery, state: FSMContext):
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="М"), KeyboardButton(text="Ж")]], resize_keyboard=True, one_time_keyboard=True)
    await call.message.answer("Выберите пол:", reply_markup=kb)
    await state.set_state(EditState.new_gender)
    await call.answer()

@dp.message(EditState.new_gender, F.text.in_(["М", "Ж"]))
async def update_gender(message: types.Message, state: FSMContext):
    new_gender = "м" if message.text == "М" else "ж"
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET gender=? WHERE user_id=?", (new_gender, user_id))
    conn.commit()
    conn.close()
    await message.answer("Пол обновлён!", reply_markup=ReplyKeyboardRemove())
    await state.clear()
    await my_profile(message)

@dp.callback_query(EditState.choice, F.data == "edit_photo")
async def edit_photo(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Отправьте новое фото:")
    await state.set_state(EditState.new_photo)
    await call.answer()

@dp.message(EditState.new_photo, F.photo)
async def update_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET photo_file_id=? WHERE user_id=?", (photo_id, user_id))
    conn.commit()
    conn.close()
    await message.answer("Фото обновлено!")
    await state.clear()
    await my_profile(message)

@dp.callback_query(EditState.choice, F.data == "edit_bio")
async def edit_bio(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT is_domina FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    is_domina = row[0] if row else False
    if is_domina:
        await call.message.answer("Введите новое описание (как Домина):\n- Как давно в теме?\n- Что практикуете?\n- Ожидания от Пса")
        await state.set_state(EditState.new_domina_bio)
    else:
        await call.message.answer("Введите новое описание (как Пёс):\n- Табу, фетиши, игрушки\n- Что ищете в Домине")
        await state.set_state(EditState.new_dog_bio)
    await call.answer()

@dp.message(EditState.new_domina_bio)
async def update_domina_bio(message: types.Message, state: FSMContext):
    new_bio = message.text.strip()
    if len(new_bio) < 20:
        await message.answer("Слишком короткое описание. Напишите подробнее (минимум 20 символов).")
        return
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET domina_bio=? WHERE user_id=?", (new_bio, user_id))
    conn.commit()
    conn.close()
    await message.answer("Описание обновлено!")
    await state.clear()
    await my_profile(message)

@dp.message(EditState.new_dog_bio)
async def update_dog_bio(message: types.Message, state: FSMContext):
    new_bio = message.text.strip()
    if len(new_bio) < 20:
        await message.answer("Слишком короткое описание. Напишите подробнее (минимум 20 символов).")
        return
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET dog_bio=? WHERE user_id=?", (new_bio, user_id))
    conn.commit()
    conn.close()
    await message.answer("Описание обновлено!")
    await state.clear()
    await my_profile(message)

@dp.callback_query(EditState.choice, F.data == "edit_cancel")
async def cancel_edit(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("Редактирование отменено.")
    await my_profile(call.message)

# ---------- ЗАПУСК ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())