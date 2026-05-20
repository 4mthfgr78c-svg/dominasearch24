# ========== ДОБАВИТЬ В БАЗУ ТАБЛИЦЫ ==========
# users: user_id, username, name, gender
# likes: from_user, to_user, status
# matches: user1, user2

# ========== РЕГИСТРАЦИЯ ==========
@router.message(F.text == "/start")
async def start(msg, state):
    if not msg.from_user.username:
        await msg.answer("❌ Задайте username в Telegram и нажмите /start")
        return
    # проверка регистрации, затем запрос имени и пола

# ========== ПОИСК (только противоположный пол) ==========
@router.message(F.text == "/search")
async def search(msg):
    my_gender = получить_пол(msg.from_user.id)
    target_gender = 'ж' if my_gender == 'м' else 'м'
    # выборка анкет: чужой пол, не пролайканных, не из matches
    # вывод первой анкеты с кнопками "Лайк" и "Следующая"

# ========== ЛАЙК ==========
@router.callback_query(F.data.startswith("like_"))
async def like(call):
    from_user = call.from_user.id
    to_user = int(call.data.split("_")[1])
    # записать лайк в таблицу likes (status='pending')
    # проверить встречный лайк: если есть, создать взаимку (matches, статус 'matched')
    # уведомить обоих о взаимности
    # для девушек: просто сохранить лайк, для парней: ждать взаимности

# ========== КТО МЕНЯ ЛАЙКНУЛ (только для девушек) ==========
@router.message(F.text == "/my_likes")
async def my_likes(msg):
    if пол != 'ж': return await msg.answer("Только для девушек")
    # показать список username из likes где to_user = msg.from_user и status='pending'
    # кнопка "Написать" (можно через /msg @username)