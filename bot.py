import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm import State, StatesGroup, context
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import asyncio

# ===== НАСТРОЙКИ =====
TOKEN = "8810784260:AAFsTF1xOWt5jI1A1utJ-xyO5nUd_YtncsU"  # замени на реальный
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== БАЗА ДАННЫХ =====
def init_db():
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        name TEXT,
        gender TEXT CHECK(gender IN ('м','ж'))
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user INTEGER,
        to_user INTEGER,
        status TEXT DEFAULT 'pending'
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user1 INTEGER,
        user2 INTEGER
    )''')
    conn.commit()
    conn.close()

init_db()

# ===== РЕГИСТРАЦИЯ =====
class RegState(StatesGroup):
    name = State()
    gender = State()

@dp.message(F.text == "/start")
async def cmd_start(msg: types.Message, state: FSMContext):
    if not msg.from_user.username:
        await msg.answer("❌ Установите username в Telegram и нажмите /start снова")
        return
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE user_id=?", (msg.from_user.id,))
    if cur.fetchone():
        await msg.answer("Вы уже зарегистрированы. /search")
        conn.close()
        return
    conn.close()
    await msg.answer("Как вас зовут?")
    await state.set_state(RegState.name)

@dp.message(RegState.name)
async def reg_name(msg: types.Message, state: FSMContext):
    await state.update_data(name=msg.text)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="М"), KeyboardButton(text="Ж")]], resize_keyboard=True)
    await msg.answer("Ваш пол:", reply_markup=kb)
    await state.set_state(RegState.gender)

@dp.message(RegState.gender, F.text.in_(["М","Ж"]))
async def reg_gender(msg: types.Message, state: FSMContext):
    gender = "м" if msg.text == "М" else "ж"
    data = await state.get_data()
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO users (user_id, username, name, gender) VALUES (?,?,?,?)",
                (msg.from_user.id, msg.from_user.username, data['name'], gender))
    conn.commit()
    conn.close()
    await msg.answer("✅ Регистрация завершена! /search", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()

# ===== ПОИСК =====
def get_opposite(gender):
    return "ж" if gender == "м" else "м"

@dp.message(F.text == "/search")
async def search(msg: types.Message):
    user_id = msg.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT gender FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        await msg.answer("Сначала /start")
        conn.close()
        return
    my_gender = row[0]
    target_gender = get_opposite(my_gender)
    cur.execute('''
        SELECT user_id, name, username FROM users
        WHERE gender = ? AND user_id != ?
        AND user_id NOT IN (SELECT to_user FROM likes WHERE from_user=?)
        AND user_id NOT IN (SELECT user2 FROM matches WHERE user1=?)
        AND user_id NOT IN (SELECT user1 FROM matches WHERE user2=?)
    ''', (target_gender, user_id, user_id, user_id, user_id))
    cand = cur.fetchone()
    conn.close()
    if not cand:
        await msg.answer("Нет новых анкет")
        return
    uid, name, username = cand
    text = f"{name} (@{username})"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❤️ Лайк", callback_data=f"like_{uid}")],
        [InlineKeyboardButton(text="➡️ Следующая", callback_data="next")]
    ])
    await msg.answer(text, reply_markup=kb)

# ===== ЛАЙК =====
@dp.callback_query(F.data.startswith("like_"))
async def like_callback(call: types.CallbackQuery):
    from_user = call.from_user.id
    to_user = int(call.data.split("_")[1])
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO likes (from_user, to_user, status) VALUES (?,?,?)",
                (from_user, to_user, 'pending'))
    conn.commit()
    cur.execute("SELECT status FROM likes WHERE from_user=? AND to_user=?", (to_user, from_user))
    mutual = cur.fetchone()
    if mutual and mutual[0] == 'pending':
        cur.execute("UPDATE likes SET status='matched' WHERE (from_user=? AND to_user=?) OR (from_user=? AND to_user=?)",
                    (from_user, to_user, to_user, from_user))
        cur.execute("INSERT INTO matches (user1, user2) VALUES (?,?)", (from_user, to_user))
        conn.commit()
        await call.message.answer("🎉 Взаимная симпатия! Можете общаться")
        await bot.send_message(to_user, f"Взаимная симпатия с @{call.from_user.username}!")
    else:
        await call.answer("Лайк сохранён")
    await call.message.delete()
    await search(call.message)
    conn.close()

@dp.callback_query(F.data == "next")
async def next_callback(call: types.CallbackQuery):
    await call.message.delete()
    await search(call.message)

# ===== ДЛЯ ДЕВУШЕК: СПИСОК ЛАЙКНУВШИХ =====
@dp.message(F.text == "/my_likes")
async def my_likes(msg: types.Message):
    user_id = msg.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT gender FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row or row[0] != 'ж':
        await msg.answer("Только для девушек")
        conn.close()
        return
    cur.execute('''
        SELECT u.username, u.name FROM likes l
        JOIN users u ON l.from_user = u.user_id
        WHERE l.to_user = ? AND l.status = 'pending'
    ''', (user_id,))
    likes = cur.fetchall()
    conn.close()
    if not likes:
        await msg.answer("Никто не лайкнул")
        return
    text = "❤️ Тебя лайкнули:\n" + "\n".join([f"- {name} (@{username})" for username, name in likes])
    await msg.answer(text)

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())