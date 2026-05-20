from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import asyncio

TOKEN = "8810784260:AAFsTF1xOWt5jI1A1utJ-xyO5nUd_YtncsU"
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(F.text == "/start")
async def start(message: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Искать")],
            [KeyboardButton(text="❤️ Взаимные симпатии"), KeyboardButton(text="📨 Сообщения")],
            [KeyboardButton(text="👤 Моя анкета"), KeyboardButton(text="⚙️ Сбросить дизлайки")]
        ],
        resize_keyboard=True
    )
    await message.answer("Главное меню с кнопками работает!", reply_markup=kb)

@dp.message(F.text == "🔍 Искать")
async def search(message: types.Message):
    await message.answer("Тут будет поиск анкет")

@dp.message(F.text == "❤️ Взаимные симпатии")
async def matches(message: types.Message):
    await message.answer("Список взаимных симпатий")

@dp.message(F.text == "📨 Сообщения")
async def msgs(message: types.Message):
    await message.answer("Нет сообщений")

@dp.message(F.text == "👤 Моя анкета")
async def profile(message: types.Message):
    await message.answer("Редактирование анкеты пока в разработке")

@dp.message(F.text == "⚙️ Сбросить дизлайки")
async def reset_dislikes(message: types.Message):
    await message.answer("Дизлайки сброшены")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())