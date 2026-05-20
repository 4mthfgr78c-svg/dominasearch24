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
    await message.answer("Бот работает! Нажми любую кнопку.", reply_markup=kb)

@dp.message(F.text)
async def echo(message: types.Message):
    await message.answer(f"Вы нажали: {message.text}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())