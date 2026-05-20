import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import asyncio

TOKEN = "8810784260:AAFsTF1xOWt5jI1A1utJ-xyO5nUd_YtncsU"
bot = Bot(token=TOKEN)
dp = Dispatcher()

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
        photo_file_id TEXT
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
class ProfileStates(StatesGroup):
    waiting_gender = State()
    waiting_name = State()
    waiting_bio = State()
    waiting_photo = State()

# ---------- СТАРТ ----------
@dp.message(F.text == "/start")
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    if cur.fetchone():
        conn.close()
        await show_main_menu(message)
        return
    conn.close()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨 Мужской", callback_data="gender_м")],
        [InlineKeyboardButton(text="👩 Женский", callback_data="gender_ж")]
    ])
    await message.answer("Добро пожаловать в бот знакомств!\nВыберите ваш пол:", reply_markup=kb)
    await state.set_state(ProfileStates.waiting_gender)

@dp.callback_query(ProfileStates.waiting_gender, F.data.startswith("gender_"))
async def set_gender(callback: types.CallbackQuery, state: FSMContext):
    gender = callback.data.split("_")[1]
    await state.update_data(gender=gender)
    await callback.message.edit_text("Введите ваше имя (как хотите, чтобы к вам обращались):")
    await state.set_state(ProfileStates.waiting_name)
    await callback.answer()

@dp.message(ProfileStates.waiting_name)
async def set_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Имя слишком короткое. Напишите хотя бы 2 символа.")
        return
    await state.update_data(name=name)
    await message.answer("Расскажите немного о себе (хобби, интересы, чего ищете):")
    await state.set_state(ProfileStates.waiting_bio)

@dp.message(ProfileStates.waiting_bio)
async def set_bio(message: types.Message, state: FSMContext):
    bio = message.text.strip()
    if len(bio) < 10:
        await message.answer("Пожалуйста, напишите хотя бы 10 символов о себе.")
        return
    await state.update_data(bio=bio)
    await message.answer("Теперь отправьте **одно фото** (самое лучшее).\nОно будет показываться в анкете.", parse_mode="Markdown")
    await state.set_state(ProfileStates.waiting_photo)

@dp.message(ProfileStates.waiting_photo, F.photo)
async def set_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1].file_id
    data = await state.get_data()
    user_id = message.from_user.id
    username = message.from_user.username or ""
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO users (user_id, username, name, gender, bio, photo_file_id) VALUES (?,?,?,?,?,?)",
                (user_id, username, data['name'], data['gender'], data['bio'], photo))
    conn.commit()
    conn.close()
    await message.answer("✅ Анкета создана! Теперь можно искать пару.", reply_markup=ReplyKeyboardRemove())
    await show_main_menu(message)
    await state.clear()

@dp.message(ProfileStates.waiting_photo)
async def photo_error(message: types.Message):
    await message.answer("Пожалуйста, отправьте именно фото (картинку).")

# ---------- ГЛАВНОЕ МЕНЮ ----------
async def show_main_menu(message: types.Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔍 Искать анкеты")],
        [KeyboardButton(text="❤️ Взаимные симпатии"), KeyboardButton(text="📨 Сообщения")],
        [KeyboardButton(text="👤 Моя анкета"), KeyboardButton(text="⚙️ Сбросить дизлайки")]
    ], resize_keyboard=True)
    await message.answer("Главное меню:", reply_markup=kb)

@dp.message(F.text == "👤 Моя анкета")
async def my_profile(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT name, gender, bio, photo_file_id FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        await message.answer("Вы не зарегистрированы. Нажмите /start")
        return
    name, gender, bio, photo_id = row
    caption = f"👤 {name} ({'Мужской' if gender=='м' else 'Женский'})\n\n{bio}"
    await message.answer_photo(photo=photo_id, caption=caption, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_profile")]
    ]))

@dp.callback_query(F.data == "edit_profile")
async def edit_profile(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Напишите новую информацию о себе:")
    await state.set_state(ProfileStates.waiting_bio)
    await call.answer()

# ---------- ПОИСК ----------
@dp.message(F.text == "🔍 Искать анкеты")
async def search_profiles(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT gender FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        await message.answer("Сначала /start")
        conn.close()
        return
    my_gender = row[0]
    target_gender = "ж" if my_gender == "м" else "м"
    cur.execute('''
        SELECT user_id, name, bio, photo_file_id, username FROM users
        WHERE gender = ? AND user_id != ?
        AND user_id NOT IN (SELECT to_user FROM likes WHERE from_user=?)
        AND user_id NOT IN (SELECT to_user FROM dislikes WHERE from_user=?)
        AND user_id NOT IN (SELECT user2 FROM matches WHERE user1=?)
        AND user_id NOT IN (SELECT user1 FROM matches WHERE user2=?)
    ''', (target_gender, user_id, user_id, user_id, user_id, user_id))
    candidates = cur.fetchall()
    conn.close()
    if not candidates:
        await message.answer("Нет новых анкет. Зайдите позже.")
        return
    if not hasattr(dp, "temp_candidates"):
        dp.temp_candidates = {}
    dp.temp_candidates[message.chat.id] = candidates
    await show_candidate(message, candidates, 0)

async def show_candidate(message: types.Message, candidates, index):
    if index >= len(candidates):
        await message.answer("Анкеты закончились.")
        return
    user_id, name, bio, photo_id, username = candidates[index]
    text = f"👤 {name} (@{username})\n\n📝 {bio}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❤️ Лайк", callback_data=f"like_{user_id}"),
         InlineKeyboardButton(text="👎 Дизлайк", callback_data=f"dislike_{user_id}")],
        [InlineKeyboardButton(text="➡️ Следующая", callback_data=f"next_{index+1}")]
    ])
    await message.answer_photo(photo=photo_id, caption=text, reply_markup=kb)

@dp.callback_query(F.data.startswith("next_"))
async def next_candidate(call: types.CallbackQuery):
    index = int(call.data.split("_")[1])
    candidates = dp.temp_candidates.get(call.message.chat.id, [])
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
    candidates = dp.temp_candidates.get(call.message.chat.id, [])
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
    candidates = dp.temp_candidates.get(call.message.chat.id, [])
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
        cur.execute("SELECT name, username FROM users WHERE user_id=?", (match_id,))
        name, username = cur.fetchone()
        text += f"- {name} (@{username})\n"
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

# ---------- ЗАПУСК ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())