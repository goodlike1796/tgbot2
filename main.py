import os
import asyncio
import logging
import requests

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.getenv("TOKEN")
MY_CHAT_ID = int(os.getenv("MY_CHAT_ID"))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

message_map = {}


def search_music(query: str) -> dict | None:
    url = "https://itunes.apple.com/search"
    params = {
        "term": query,
        "media": "music",
        "entity": "song",
        "limit": 1
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("results"):
            return None
        track = data["results"][0]
        return {
            "track_name": track.get("trackName", "Неизвестно"),
            "artist_name": track.get("artistName", "Неизвестно"),
            "release_date": track.get("releaseDate", ""),
            "preview_url": track.get("previewUrl", ""),
            "track_view_url": track.get("trackViewUrl", ""),
            "artwork_url": track.get("artworkUrl60", ""),
        }
    except Exception:
        return None


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "Бот готов к работе!\n"
        "Нажми кнопку ниже, чтобы поделиться номером телефона,для того чтобы искать песни"
        "Для поиска музыки напиши:\n"
        "/music название песни",
        reply_markup=kb
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "Команды:\n"
        "/start — запустить бота\n"
        "/help — показать справку\n"
        "/music название — поиск песни\n\n"
    )


@dp.message(Command("music"))
async def cmd_music(message: types.Message):
    text = message.text.strip()
    if not text.startswith("/music"):
        await message.answer("Используй команду так: /music название песни")
        return

    query = text[len("/music"):].strip()
    if not query:
        await message.answer("Напиши название песни:\n/music название песни")
        return

    await message.answer(f"Ищу музыку: {query}...")

    track = search_music(query)
    if not track:
        await message.answer("Ничего не найдено. Попробуй другое название.")
        return

    info_text = (
        f"🎵 {track['track_name']}\n"
        f"👤 {track['artist_name']}\n"
        f"📅 Выпущена: {track['release_date'] or 'не указано'}\n"
        f"🔗 Ссылка: {track['track_view_url']}\n"
        f"🎧 Превью: {track['preview_url'] or 'нет'}"
    )

    if track["artwork_url"]:
        artwork_url = track["artwork_url"].replace("60x60", "300x300")
        await bot.send_photo(
            message.chat.id,
            photo=artwork_url,
            caption=info_text
        )
    else:
        await message.answer(info_text)

    user_name = message.from_user.first_name or "Пользователь"
    user_id = message.from_user.id
    admin_text = (
        f"🎵 Запрос на поиск музыки от {user_name} (ID: {user_id})\n"
        f"🔍 Запрос: {query}\n\n"
        f"{info_text}"
    )
    if track["artwork_url"]:
        artwork_url = track["artwork_url"].replace("60x60", "300x300")
        await bot.send_photo(
            MY_CHAT_ID,
            photo=artwork_url,
            caption=admin_text
        )
    else:
        await bot.send_message(MY_CHAT_ID, admin_text)


@dp.message(F.contact)
async def handle_contact(message: types.Message):
    contact = message.contact
    phone_number = contact.phone_number
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Пользователь"
    
    text = (
        f"📱 Пользователь поделился контактом:\n"
        f"👤 {user_name}\n"
        f"ID: {user_id}\n"
        f"📞 Номер: {phone_number}"
    )
    
    await message.answer(
        "Спасибо! Твой номер телефона отправлен.",
        reply_markup=None
    )
    await bot.send_message(MY_CHAT_ID, text)


@dp.message(F.chat.type == "private")
async def echo_to_user(message: types.Message):
    if message.from_user.id == MY_CHAT_ID:
        if message.reply_to_message:
            user_chat_id = message_map.get(message.reply_to_message.message_id)
            if user_chat_id:
                await bot.send_message(user_chat_id, message.text)
                await message.answer("Ответ отправлен пользователю.")
            else:
                await message.answer("Не нашёл, кому отвечать.")
        return

    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    username = message.from_user.username or ""
    uid = message.from_user.id

    full_name = f"{first_name} {last_name}".strip() or first_name or "Пользователь"
    username_str = f"@{username}" if username else ""

    text = (
        f"👤 {full_name} {username_str}\n"
        f"ID: {uid}\n"
        f"Текст: {message.text}"
    )

    sent = await bot.send_message(MY_CHAT_ID, text)
    message_map[sent.message_id] = message.chat.id
    await message.answer("")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
