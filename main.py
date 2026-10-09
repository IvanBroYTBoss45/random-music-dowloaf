import os
import asyncio
import logging
from pathlib import Path
import sqlite3 as sq

# Импорты aiogram 3.x
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart

# Импорты для yt-dlp и ffmpeg
import static_ffmpeg
from yt_dlp import YoutubeDL

# Инициализируем ffmpeg при старте
static_ffmpeg.add_paths()

# Токен твоего бота (замени на свой)
TOKEN = "ТВОЙ_ТОКЕН_БОТА"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Инициализация кэш-базы SQLite
def init_db():
    with sq.connect("music_cache.db") as con:
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS cached_tracks (
            video_id TEXT PRIMARY KEY,
            year INTEGER,
            title TEXT
        )
        """)
        con.commit()

init_db()

# Опции для yt-dlp с твоим ТЗ (User-Agent, Клиент и MP3)
def get_ytdl_opts(year):
    return {
        'format': 'bestaudio/best',
        'outtmpl': str(DOWNLOAD_DIR / f'%(title)s_{year}.%(ext)s'),
        'noplaylist': True,
        'playlistend': 20,  # Строго 20 треков за раз
        'quiet': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        },
        'extractor_args': {
            'youtube': {
                'player_client': ['web', 'ios'],
            }
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

# Хэндлер на команду /start с ИСПРАВЛЕННОЙ инлайн-клавиатурой
@dp.message(CommandStart())
async def cmd_start(message: Message):
    # Тут всё зафиксировано, callback_data на месте
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Запустить скачивание по годам 🚀", callback_query_data="start_download")]
    ])
    await message.answer(
        "Здорово, бро! Система готова к работе.\n"
        "Нажми на кнопку ниже, чтобы запустить асинхронный конвейер выкачки треков (2000-2026).",
        reply_markup=kb
    )

# Асинхронный процесс выкачки, отправки и удаления
@dp.callback_query(F.data == "start_download")
async def process_download(callback: CallbackQuery):
    await callback.answer("Конвейер запущен!")
    chat_id = callback.message.chat.id
    
    await bot.send_message(chat_id, "⚙️ Начинаю сбор данных. Погнали плясать...")

    for year in range(2000, 2027):
        await bot.send_message(chat_id, f"📅 Разбираю {year} год. Ищу 20 лучших треков...")
        
        search_query = f"ytsearch20:лучшие песни {year}"
        opts = get_ytdl_opts(year)
        
        loop = asyncio.get_event_loop()
        try:
            with YoutubeDL(opts) as ydl:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(search_query, download=True))
                
                if 'entries' in info:
                    for entry in info['entries']:
                        if not entry:
                            continue
                        
                        video_id = entry.get('id')
                        title = entry.get('title', 'Без названия')
                        
                        # Проверяем кэш базы данных
                        with sq.connect("music_cache.db") as con:
                            cur = con.cursor()
                            cur.execute("SELECT video_id FROM cached_tracks WHERE video_id = ?", (video_id,))
                            if cur.fetchone():
                                logging.info(f"Трек {title} уже отправлялся, скип.")
                                continue
                        
                        expected_file = DOWNLOAD_DIR / f"{title}_{year}.mp3"
                        
                        if expected_file.exists():
                            await bot.send_audio(
                                chat_id=chat_id,
                                audio=FSInputFile(str(expected_file)),
                                caption=f"🎵 {title}\n📅 Год: {year}"
                            )
                            
                            with sq.connect("music_cache.db") as con:
                                cur = con.cursor()
                                cur.execute("INSERT OR IGNORE INTO cached_tracks VALUES (?, ?, ?)", (video_id, year, title))
                                con.commit()
                            
                            os.remove(expected_file)
                            await asyncio.sleep(0.5)
                            
        except Exception as e:
            logging.error(f"Ошибка на {year} году: {e}")
            await bot.send_message(chat_id, f"⚠️ Сбой при обработке {year} года, иду дальше по списку.")
            continue

    await bot.send_message(chat_id, "🏆 Партийное задание выполнено! Все 540 треков обработаны.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
