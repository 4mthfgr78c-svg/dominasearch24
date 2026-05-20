import sqlite3
import random
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "8810784260:AAFsTF1xOWt5jI1A1utJ-xyO5nUd_YtncsU"
ADMIN_USER_ID = 8117530336

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

# ---------- СОСТОЯНИЯ РЕГИСТРАЦИИ ----------
class RegState(StatesGroup):
    age_confirm = State()
    name = State()
    photo = State()
    gender = State()
    bio = State()

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

async def show_main_menu(message: types.Message):
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
        await show_main_menu(message)
        return
    # Подтверждение 18+
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
    await show_main_menu(message)
    await state.clear()

# ---------- АДМИН: ВЫДАЧА СТАТУСА ДОМИНЫ ----------
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
        await bot.send_message(user_id, f"🎉 Поздравляем! Админ выдал вам статус Домины. Ваш DominaID: {domina_id}. Теперь вы видите анкеты псов, и ваша анкета получила отметку 👠.")
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

# ---------- ПОИСК АНКЕТ (ДОМИНА ВИДИТ ПСОВ, ПЁС ВИДИТ ДОМИН) ----------
def get_target_role(user_id):
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT is_domina FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return 0 if row[0] else 1  # Домина ищет псов (0), пёс ищет Домин (1)

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
    need_role = 0 if my_role == 1 else 1  # Домина ищет псов (0), пёс ищет Домин (1)
    # Исключаем себя, уже пролайканных, дизлайкнутых, взаимки
    cur.execute('''
        SELECT user_id, name, bio, photo_file_id, username, is_domina, domina_id
        FROM users
        WHERE is_domina = ? AND user_id != ?
          AND user_id NOT IN (SELECT to_user FROM likes WHERE from_user=?)
          AND user_id NOT IN (SELECT to_user FROM dislikes WHERE from_user=?)
          AND user_id NOT IN (SELECT user2 FROM matches WHERE user1=?)
          AND user_id NOT IN (SELECT user1 FROM matches WHERE user2=?)
    ''', (need_role, user_id, user_id, user_id, user_id, user_id))
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
    user_id, name, bio, photo_id, username, is_domina, domina_id = candidates[index]
    # Формируем текст
    text = f"👤 {name}\n"
    if is_domina:
        text += f"👠 Домина (ID {domina_id})\n"
    else:
        text += "🦴 Пёс\n"
        if not domina_id:
            text += "⚠️ Непроверенный аккаунт (возможен скам)\n"
    text += f"\n📝 {bio}"
    # Показываем username только если взаимность уже есть? Нет, здесь не показываем никогда до взаимки.
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
    # Проверяем, есть ли встречный лайк
    cur.execute("SELECT 1 FROM likes WHERE from_user=? AND to_user=?", (to_user, from_user))
    mutual = cur.fetchone()
    cur.execute("INSERT OR REPLACE INTO likes (from_user, to_user, status) VALUES (?,?,?)",
                (from_user, to_user, 'pending'))
    conn.commit()
    if mutual:
        # Взаимность
        cur.execute("UPDATE likes SET status='matched' WHERE (from_user=? AND to_user=?) OR (from_user=? AND to_user=?)",
                    (from_user, to_user, to_user, from_user))
        cur.execute("INSERT OR IGNORE INTO matches (user1, user2) VALUES (?,?)",
                    (min(from_user, to_user), max(from_user, to_user)))
        conn.commit()
        # Уведомление о взаимности
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
    await call.message.answer(f"Вы открыли диалог. Напишите сообщение собеседнику.\nЧтобы закончить, нажмите /endchat")
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

# ---------- МОЯ АНКЕТА (ПРОСТАЯ ЗАГЛУШКА) ----------
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
    role = "👠 Домина" if is_domina else "🦴 Пёс"
    text = f"👤 {name} ({'Мужчина' if gender=='м' else 'Женщина'})\n{role}\n"
    if is_domina:
        text += f"DominaID: {domina_id}\n"
    else:
        text += "⚠️ Неподтверждённый аккаунт (может быть скам)\n"
    text += f"\n📝 {bio}"
    await message.answer_photo(photo=photo_id, caption=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать (скоро)", callback_data="edit_profile")]
    ]))

@dp.callback_query(F.data == "edit_profile")
async def edit_profile(call: types.CallbackQuery):
    await call.message.answer("Редактирование анкеты будет доступно позже.")
    await call.answer()

# ---------- ЗАПУСК ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())