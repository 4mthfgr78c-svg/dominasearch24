import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Кнопки главного меню
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Анкета дня")],
        [KeyboardButton(text="✏️ Моя анкета"), KeyboardButton(text="📋 Список участников")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет! Это бот знакомств. Выбери действие:", reply_markup=main_kb)

@dp.message(lambda msg: msg.text == "🔍 Анкета дня")
async def daily_profile(message: types.Message):
    await message.answer("Пока здесь заглушка. Позже покажу случайную анкету.")

@dp.message(lambda msg: msg.text == "✏️ Моя анкета")
async def my_profile(message: types.Message):
    await message.answer("Редактирование анкеты. Заполни: возраст, город, о себе. Скоро сделаю.")

@dp.message(lambda msg: msg.text == "📋 Список участников")
async def list_profiles(message: types.Message):
    await message.answer("Список участников появятся позже.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())