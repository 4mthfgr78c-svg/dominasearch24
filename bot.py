import sqlite3
import random
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove
)

TOKEN = "8810784260:AAFsTF1xOWt5jI1A1utJ-xyO5nUd_YtncsU"
ADMIN_ID = 8117530336  # ЗАМЕНИТЕ НА ВАШ ID

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилища
user_data = {}      # временные данные при регистрации
active_chats = {}   # {user_id: partner_id}
temp_candidates = {}  # {user_id: список анкет}

# ---------- БАЗА ДАННЫХ ----------
def init_db():
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.executescript('''
        CREATE TABLE IF NOT EXISTS users (
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
        );
        CREATE TABLE IF NOT EXISTS likes (
            from_user INTEGER,
            to_user INTEGER,
            status TEXT,
            PRIMARY KEY (from_user, to_user)
        );
        CREATE TABLE IF NOT EXISTS dislikes (
            from_user INTEGER,
            to_user INTEGER,
            PRIMARY KEY (from_user, to_user)
        );
        CREATE TABLE IF NOT EXISTS matches (
            user1 INTEGER,
            user2 INTEGER,
            PRIMARY KEY (user1, user2)
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user INTEGER,
            to_user INTEGER,
            text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    conn.close()
init_db()

# ---------- ВСПОМОГАТЕЛЬНЫЕ ----------
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
    return user_id == ADMIN_ID

async def show_main_menu(message: types.Message):
    """Отправляет главное меню с кнопками (без лишнего текста)"""
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔍 Искать")],
        [KeyboardButton(text="❤️ Взаимные симпатии"), KeyboardButton(text="📨 Сообщения")],
        [KeyboardButton(text="👤 Моя анкета"), KeyboardButton(text="⚙️ Сбросить дизлайки")]
    ], resize_keyboard=True)
    await message.answer("👇", reply_markup=kb)

# ---------- ОПОВЕЩЕНИЕ О НОВЫХ ПОЛЬЗОВАТЕЛЯХ ----------
async def notify_new_user(new_user_id, is_domina):
    """Уведомляет всех пользователей противоположной роли"""
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    if is_domina:
        cur.execute("SELECT user_id FROM users WHERE is_domina=0 AND registered=1 AND user_id != ?", (new_user_id,))
        msg = "👠 *Новая Домина появилась в сообществе!*\nНажми /search, чтобы увидеть анкету."
    else:
        cur.execute("SELECT user_id FROM users WHERE is_domina=1 AND registered=1 AND user_id != ?", (new_user_id,))
        msg = "🐾 *Новый Пёс зарегистрировался!*\nНажми /search, чтобы найти его."
    users = cur.fetchall()
    conn.close()
    for (uid,) in users:
        try:
            await bot.send_message(uid, msg, parse_mode="Markdown")
        except:
            pass

# ---------- РЕГИСТРАЦИЯ ----------
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT registered FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        await show_main_menu(message)
        return
    user_data[user_id] = {"step": "age"}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, мне 18+", callback_data="age_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="age_no")]
    ])
    await message.answer("🔞 Вам есть 18 лет?", reply_markup=kb)

@dp.callback_query(lambda c: c.data in ["age_yes", "age_no"])
async def age_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if callback.data == "age_no":
        await callback.message.edit_text("До свидания.")
        user_data.pop(user_id, None)
        await callback.answer()
        return
    user_data[user_id] = {"step": "name", "age_verified": True}
    await callback.message.edit_text("Введите ваше имя (как хотите, чтобы к вам обращались):")
    await callback.answer()

@dp.message(lambda msg: msg.from_user.id in user_data and user_data[msg.from_user.id].get("step") == "name")
async def reg_name(message: types.Message):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Слишком короткое имя. Напишите хотя бы 2 символа.")
        return
    user_data[message.from_user.id]["name"] = name
    user_data[message.from_user.id]["step"] = "photo"
    await message.answer("Отправьте ваше фото (одно, лучшее):")

@dp.message(lambda msg: msg.from_user.id in user_data and user_data[msg.from_user.id].get("step") == "photo" and msg.photo)
async def reg_photo(message: types.Message):
    photo = message.photo[-1].file_id
    user_data[message.from_user.id]["photo"] = photo
    user_data[message.from_user.id]["step"] = "gender"
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="М"), KeyboardButton(text="Ж")]], resize_keyboard=True)
    await message.answer("Ваш пол:", reply_markup=kb)

@dp.message(lambda msg: msg.from_user.id in user_data and user_data[msg.from_user.id].get("step") == "photo" and not msg.photo)
async def reg_photo_error(message: types.Message):
    await message.answer("Пожалуйста, отправьте фото (изображение).")

@dp.message(lambda msg: msg.from_user.id in user_data and user_data[msg.from_user.id].get("step") == "gender" and msg.text in ["М", "Ж"])
async def reg_gender(message: types.Message):
    gender = "м" if message.text == "М" else "ж"
    user_data[message.from_user.id]["gender"] = gender
    user_data[message.from_user.id]["step"] = "role"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👠 Я Домина", callback_data="role_domina")],
        [InlineKeyboardButton(text="🦴 Я Пёс", callback_data="role_dog")]
    ])
    await message.answer("Вы регистрируетесь как Домина или Пёс?\n(Статус Домины позже выдаст администратор)", reply_markup=kb)
    await message.answer("Пол сохранён.", reply_markup=ReplyKeyboardRemove())

@dp.callback_query(lambda c: c.data in ["role_domina", "role_dog"])
async def role_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    role = callback.data.split("_")[1]
    user_data[user_id]["requested_role"] = role
    if role == "domina":
        await callback.message.edit_text(
            "Расскажите о себе как о Домине:\n"
            "- Как давно в теме?\n"
            "- Что практикуете?\n"
            "- Ваши ожидания от Пса"
        )
        user_data[user_id]["step"] = "domina_bio"
    else:
        await callback.message.edit_text(
            "Расскажите о себе как о Псе:\n"
            "- Ваши табу, фетиши, игрушки\n"
            "- Что ищете в Домине"
        )
        user_data[user_id]["step"] = "dog_bio"
    await callback.answer()

@dp.message(lambda msg: msg.from_user.id in user_data and user_data[msg.from_user.id].get("step") == "domina_bio")
async def reg_domina_bio(message: types.Message):
    bio = message.text.strip()
    if len(bio) < 20:
        await message.answer("Минимум 20 символов.")
        return
    user_data[message.from_user.id]["domina_bio"] = bio
    await finish_registration(message)

@dp.message(lambda msg: msg.from_user.id in user_data and user_data[msg.from_user.id].get("step") == "dog_bio")
async def reg_dog_bio(message: types.Message):
    bio = message.text.strip()
    if len(bio) < 20:
        await message.answer("Минимум 20 символов.")
        return
    user_data[message.from_user.id]["dog_bio"] = bio
    await finish_registration(message)

async def finish_registration(message: types.Message):
    user_id = message.from_user.id
    data = user_data[user_id]
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
    # Уведомление о новом пользователе (пёс)
    await notify_new_user(user_id, is_domina=False)
    del user_data[user_id]
    await message.answer("✅ Регистрация завершена! Вы зарегистрированы как Пёс (если выбрали Домину — статус выдаст админ).\nТеперь вы можете искать анкеты.", reply_markup=ReplyKeyboardRemove())
    await show_main_menu(message)

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
    # Уведомление о новой Домине
    await notify_new_user(user_id, is_domina=True)
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

@dp.message(F.text.startswith("/broadcast"))
async def broadcast(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("Нет прав.")
        return
    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        await message.answer("Использование: /broadcast Текст рассылки")
        return
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE registered=1")
    users = cur.fetchall()
    conn.close()
    if not users:
        await message.answer("Нет зарегистрированных пользователей.")
        return
    sent = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, f"📢 *Рассылка от администратора:*\n\n{text}", parse_mode="Markdown")
            sent += 1
            await asyncio.sleep(0.05)  # небольшая пауза, чтобы не упереться в лимиты
        except:
            pass
    await message.answer(f"✅ Рассылка отправлена {sent} пользователям.")

# ---------- ПОИСК (С КНОПКОЙ НАПИСАТЬ ДЛЯ ДОМИНЫ) ----------
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
        condition = "is_domina = 0"
    else:
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
    temp_candidates[user_id] = candidates
    await show_candidate(message, candidates, 0)

async def show_candidate(message: types.Message, candidates, index):
    if index >= len(candidates):
        await message.answer("Анкеты закончились.")
        return
    data = candidates[index]
    uid, name, photo_id, username, is_domina, domina_id, domina_bio, dog_bio = data
    if is_domina:
        bio_text = domina_bio or "Нет описания"
        role_text = f"👠 Домина (ID {domina_id})"
    else:
        bio_text = dog_bio or "Нет описания"
        role_text = "🦴 Пёс"
    text = f"👤 {name}\n{role_text}\n\n📝 {bio_text}"

    # Определяем, кто смотрит
    viewer_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT is_domina FROM users WHERE user_id=?", (viewer_id,))
    row = cur.fetchone()
    conn.close()
    viewer_is_domina = row[0] if row else False

    buttons = []
    if viewer_is_domina and not is_domina:   # Дomina смотрит на пса
        buttons.append([InlineKeyboardButton(text="💬 Написать", callback_data=f"write_{uid}")])
    buttons.append([InlineKeyboardButton(text="❤️ Лайк", callback_data=f"like_{uid}"),
                    InlineKeyboardButton(text="👎 Дизлайк", callback_data=f"dislike_{uid}")])
    buttons.append([InlineKeyboardButton(text="➡️ Следующая", callback_data=f"next_{index+1}")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer_photo(photo=photo_id, caption=text, reply_markup=kb)

@dp.callback_query(F.data.startswith("next_"))
async def next_candidate(call: types.CallbackQuery):
    index = int(call.data.split("_")[1])
    candidates = temp_candidates.get(call.from_user.id, [])
    if not candidates:
        await call.message.answer("Список анкет пуст, начните поиск заново.")
        await call.answer()
        return
    await call.message.delete()
    await show_candidate(call.message, candidates, index)
    await call.answer()

@dp.callback_query(F.data.startswith("like_"))
async def like(call: types.CallbackQuery):
    from_user = call.from_user.id
    to_user = int(call.data.split("_")[1])
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM likes WHERE from_user=? AND to_user=?", (from_user, to_user))
    if cur.fetchone():
        await call.answer("Вы уже лайкали эту анкету.", show_alert=True)
        conn.close()
        return
    cur.execute("SELECT 1 FROM likes WHERE from_user=? AND to_user=?", (to_user, from_user))
    mutual = cur.fetchone()
    cur.execute("INSERT INTO likes (from_user, to_user, status) VALUES (?,?,?)",
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
    await search(call.message)

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
    await search(call.message)

@dp.callback_query(F.data.startswith("write_"))
async def write_first(call: types.CallbackQuery):
    from_user = call.from_user.id
    to_user = int(call.data.split("_")[1])
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT is_domina FROM users WHERE user_id=?", (from_user,))
    row = cur.fetchone()
    if not row or not row[0]:
        await call.answer("Только Домина может писать первой.", show_alert=True)
        conn.close()
        return
    conn.close()
    active_chats[from_user] = to_user
    await call.message.answer("✅ Диалог открыт. Напишите сообщение.\nДля закрытия /endchat")
    await call.answer()

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
    rows = cur.fetchall()
    if not rows:
        await message.answer("Пока нет взаимных симпатий.")
        conn.close()
        return
    text = "Ваши взаимки:\n"
    kb_buttons = []
    for (match_id,) in rows:
        cur.execute("SELECT name, username, is_domina FROM users WHERE user_id=?", (match_id,))
        name, username, is_domina = cur.fetchone()
        role = "👠" if is_domina else "🦴"
        text += f"- {role} {name} (@{username})\n"
        kb_buttons.append([InlineKeyboardButton(text=f"💬 Написать {name}", callback_data=f"chat_{match_id}")])
    conn.close()
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("chat_"))
async def open_chat_from_match(call: types.CallbackQuery):
    partner_id = int(call.data.split("_")[1])
    active_chats[call.from_user.id] = partner_id
    await call.message.answer("✅ Диалог открыт. Напишите сообщение.\n/endchat - закрыть")
    await call.answer()

# ---------- ОТПРАВКА СООБЩЕНИЙ И КНОПКА "ОТВЕТИТЬ" ----------
@dp.message(F.text, lambda msg: msg.from_user.id in active_chats)
async def send_message(message: types.Message):
    to_user = active_chats[message.from_user.id]
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    # Проверяем, есть ли взаимная симпатия (или разрешено писать без неё)
    cur.execute("SELECT 1 FROM matches WHERE (user1=? AND user2=?) OR (user1=? AND user2=?)",
                (message.from_user.id, to_user, to_user, message.from_user.id))
    if not cur.fetchone():
        # Если нет взаимности, проверяем, не Домина ли пишет (уже проверили при write_)
        cur.execute("SELECT is_domina FROM users WHERE user_id=?", (message.from_user.id,))
        row = cur.fetchone()
        if not row or not row[0]:
            await message.answer("❌ Нет взаимной симпатии. Вы не можете писать этому пользователю.")
            conn.close()
            return
    cur.execute("INSERT INTO messages (from_user, to_user, text) VALUES (?,?,?)",
                (message.from_user.id, to_user, message.text))
    conn.commit()
    # Отправляем получателю с кнопкой "Ответить"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Ответить", callback_data=f"reply_{message.from_user.id}")]
    ])
    await bot.send_message(to_user,
                           f"💬 Новое сообщение от @{message.from_user.username}:\n\n{message.text}",
                           reply_markup=kb)
    await message.answer("✅ Сообщение отправлено.")
    conn.close()

@dp.callback_query(F.data.startswith("reply_"))
async def reply_to_message(call: types.CallbackQuery):
    from_user = call.from_user.id
    to_user = int(call.data.split("_")[1])
    active_chats[from_user] = to_user
    await call.message.answer("✅ Вы ответили. Напишите ваше сообщение.\n/endchat - закрыть")
    await call.answer()

@dp.message(F.text == "/endchat")
async def end_chat(message: types.Message):
    if message.from_user.id in active_chats:
        del active_chats[message.from_user.id]
        await message.answer("✅ Диалог закрыт.")

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
        conn2 = sqlite3.connect('dating.db')
        cur2 = conn2.cursor()
        cur2.execute("SELECT username FROM users WHERE user_id=?", (other,))
        uname_row = cur2.fetchone()
        conn2.close()
        other_name = f"@{uname_row[0]}" if uname_row else str(other)
        text += f"{direction} {other_name}: {msg_text[:50]}\n"
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

# ---------- МОЯ АНКЕТА И РЕДАКТИРОВАНИЕ ----------
edit_data = {}

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
    if is_domina:
        role_text = f"👠 Домина\n🏷 ID: {domina_id}"
        bio_text = domina_bio or "Нет описания"
        greeting = f"Приветствую Вас, Госпожа {name}! 👠"
    else:
        role_text = "🦴 Пёс"
        bio_text = dog_bio or "Нет описания"
        greeting = f"Йоу, {name}! Слушай сюда, пёсик. 🦴"
    caption = f"{greeting}\n{role_text}\n\nПол: {gender_str}\n\n📝 {bio_text}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать анкету", callback_data="edit_profile")]
    ])
    await message.answer_photo(photo=photo_id, caption=caption, reply_markup=kb)

@dp.callback_query(F.data == "edit_profile")
async def edit_start(call: types.CallbackQuery):
    user_id = call.from_user.id
    edit_data[user_id] = {"step": "menu"}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Имя", callback_data="edit_name")],
        [InlineKeyboardButton(text="Пол", callback_data="edit_gender")],
        [InlineKeyboardButton(text="Фото", callback_data="edit_photo")],
        [InlineKeyboardButton(text="Описание", callback_data="edit_bio")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="edit_cancel")]
    ])
    await call.message.answer("Что хотите изменить?", reply_markup=kb)
    await call.answer()

@dp.callback_query(lambda c: c.data.startswith("edit_") and c.data != "edit_profile")
async def edit_choice(call: types.CallbackQuery):
    user_id = call.from_user.id
    action = call.data.split("_")[1]
    if action == "cancel":
        edit_data.pop(user_id, None)
        await call.message.answer("Редактирование отменено.")
        await my_profile(call.message)
        await call.answer()
        return
    edit_data[user_id]["step"] = f"wait_{action}"
    if action == "name":
        await call.message.answer("Введите новое имя:")
    elif action == "gender":
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="М"), KeyboardButton(text="Ж")]], resize_keyboard=True)
        await call.message.answer("Выберите пол:", reply_markup=kb)
    elif action == "photo":
        await call.message.answer("Отправьте новое фото:")
    elif action == "bio":
        conn = sqlite3.connect('dating.db')
        cur = conn.cursor()
        cur.execute("SELECT is_domina FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        conn.close()
        is_domina = row[0] if row else False
        if is_domina:
            await call.message.answer("Введите новое описание (Домина):\n- Как давно в теме?\n- Что практикуете?\n- Ожидания от Пса")
        else:
            await call.message.answer("Введите новое описание (Пёс):\n- Табу, фетиши, игрушки\n- Что ищете в Домине")
    await call.answer()

@dp.message(lambda msg: msg.from_user.id in edit_data and edit_data[msg.from_user.id].get("step") == "wait_name")
async def update_name(message: types.Message):
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
    del edit_data[user_id]
    await message.answer("✅ Имя обновлено!")
    await my_profile(message)

@dp.message(lambda msg: msg.from_user.id in edit_data and edit_data[msg.from_user.id].get("step") == "wait_gender" and msg.text in ["М", "Ж"])
async def update_gender(message: types.Message):
    new_gender = "м" if message.text == "М" else "ж"
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET gender=? WHERE user_id=?", (new_gender, user_id))
    conn.commit()
    conn.close()
    del edit_data[user_id]
    await message.answer("✅ Пол обновлён!", reply_markup=ReplyKeyboardRemove())
    await my_profile(message)

@dp.message(lambda msg: msg.from_user.id in edit_data and edit_data[msg.from_user.id].get("step") == "wait_photo" and msg.photo)
async def update_photo(message: types.Message):
    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET photo_file_id=? WHERE user_id=?", (photo_id, user_id))
    conn.commit()
    conn.close()
    del edit_data[user_id]
    await message.answer("✅ Фото обновлено!")
    await my_profile(message)

@dp.message(lambda msg: msg.from_user.id in edit_data and edit_data[msg.from_user.id].get("step") == "wait_bio")
async def update_bio(message: types.Message):
    new_bio = message.text.strip()
    if len(new_bio) < 20:
        await message.answer("Минимум 20 символов.")
        return
    user_id = message.from_user.id
    conn = sqlite3.connect('dating.db')
    cur = conn.cursor()
    cur.execute("SELECT is_domina FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    is_domina = row[0] if row else False
    if is_domina:
        cur.execute("UPDATE users SET domina_bio=? WHERE user_id=?", (new_bio, user_id))
    else:
        cur.execute("UPDATE users SET dog_bio=? WHERE user_id=?", (new_bio, user_id))
    conn.commit()
    conn.close()
    del edit_data[user_id]
    await message.answer("✅ Описание обновлено!")
    await my_profile(message)

# ---------- ЗАПУСК ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())