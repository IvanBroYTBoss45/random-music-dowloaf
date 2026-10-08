import os
import asyncio
import sqlite3
import random
import subprocess
import static_ffmpeg
from pathlib import Path
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage

# --- НАСТРОЙКИ ---
BOT_TOKEN = "ТВОЙ_ТОКЕН_ЗДЕСЬ"  # <-- вставь свой токен
ADMIN_ID = 123456789  # <-- твой Telegram ID
START_YEAR = 2000
END_YEAR = 2026
TRACKS_PER_YEAR = 20
OUTPUT_DIR = "music_cache"
DB_PATH = "bot_music.db"

# --- ИНИЦИАЛИЗАЦИЯ static-ffmpeg ---
static_ffmpeg.add_paths()
FFMPEG_PATH = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()[0]
print(f"🎬 ffmpeg: {FFMPEG_PATH}")

# --- БАЗА ДАННЫХ ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS downloaded (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT UNIQUE,
                title TEXT,
                year INTEGER,
                timestamp TEXT
            )
        """)
        conn.commit()

def is_downloaded(video_id: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM downloaded WHERE video_id = ?", (video_id,))
        return cursor.fetchone() is not None

def mark_downloaded(video_id: str, title: str, year: int):
    import datetime
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO downloaded (video_id, title, year, timestamp) VALUES (?, ?, ?, ?)",
            (video_id, title, year, datetime.datetime.now().isoformat())
        )
        conn.commit()

def get_stats():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM downloaded")
        return cursor.fetchone()[0]

# --- БОТ ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Флаг, чтобы не запускать два процесса одновременно
is_running = False

def build_ytdlp_args(url: str) -> list:
    return [
        "yt-dlp",
        "--extractor-args", "youtube:player_client=android,ios",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "--add-header", "Accept-Language:ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "--ffmpeg-location", FFMPEG_PATH,
        "--sleep-interval", "1",
        "--max-sleep-interval", "3",
        "--retries", "5",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "320",
        "-o", f"{OUTPUT_DIR}/%(id)s.%(ext)s",
        url
    ]

def search_year(year: int) -> list:
    """Ищет треки за год и возвращает список (video_id, title)."""
    search_query = f"after:{year}0101 before:{year}1231"
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--extractor-args", "youtube:player_client=android,ios",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "--add-header", "Accept-Language:ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "--flat-playlist",
                "--print", "%(id)s|%(title)s",
                "--no-warnings",
                f"ytsearch{TRACKS_PER_YEAR * 3}:{search_query}"
            ],
            capture_output=True, text=True, check=True, encoding="utf-8"
        )
        tracks = []
        for line in result.stdout.splitlines():
            if "|" in line:
                vid, title = line.split("|", 1)
                tracks.append((vid.strip(), title.strip()))
        return tracks
    except Exception as e:
        print(f"[ПОИСК] Ошибка за {year}: {e}")
        return []

async def download_and_send(video_id: str, title: str, year: int) -> bool:
    """Скачивает трек, отправляет в ТГ, записывает в БД."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    file_path = f"{OUTPUT_DIR}/{video_id}.mp3"

    # Скачиваем
    try:
        subprocess.run(build_ytdlp_args(url), check=True, capture_output=True)
    except Exception as e:
        print(f"[СКАЧИВАНИЕ] Ошибка {video_id}: {e}")
        return False

    # Проверяем, что файл есть
    if not os.path.exists(file_path):
        print(f"[ФАЙЛ] Не найден: {file_path}")
        return False

    # Отправляем в ТГ
    try:
        audio = FSInputFile(file_path, filename=f"{title}.mp3")
        await bot.send_audio(ADMIN_ID, audio, title=title)
    except Exception as e:
        print(f"[ОТПРАВКА] Ошибка {video_id}: {e}")
        return False

    # Записываем в БД
    mark_downloaded(video_id, title, year)

    # Удаляем локальный файл (чтобы не жрал место)
    try:
        os.remove(file_path)
    except:
        pass

    return True

async def download_process(message: Message):
    """Основной процесс: с 2000 по 2026, по 20 треков в год."""
    global is_running
    if is_running:
        await message.answer("⚠️ Уже качаю! Подожди, пока закончу.")
        return

    is_running = True
    await message.answer(
        f"🎶 Начинаю качать треки с {START_YEAR} по {END_YEAR}.\n"
        f"📊 По {TRACKS_PER_YEAR} треков в год.\n"
        f"🎵 Формат: MP3 320 kbps\n"
        f"📥 Уже скачано: {get_stats()}\n\n"
        f"Буду скидывать по одному. Это займёт пару часов."
    )

    total_downloaded = 0
    try:
        for year in range(START_YEAR, END_YEAR + 1):
            await message.answer(f"🔎 Ищу треки за {year} год...")
            tracks = search_year(year)
            if not tracks:
                await message.answer(f"⚠️ Не нашёл треки за {year} год.")
                continue

            random.shuffle(tracks)
            selected = tracks[:TRACKS_PER_YEAR]

            for i, (vid, title) in enumerate(selected, 1):
                if is_downloaded(vid):
                    continue  # Уже качали — пропускаем

                success = await download_and_send(vid, title, year)
                if success:
                    total_downloaded += 1
                    # Пишем прогресс каждые 5 треков
                    if total_downloaded % 5 == 0:
                        await message.answer(f"✅ Скачано {total_downloaded} треков (всего в БД: {get_stats()})")

                # Пауза между треками
                await asyncio.sleep(2)

        await message.answer(
            f"🎉 Готово!\n"
            f"📊 Всего скачано в этой сессии: {total_downloaded}\n"
            f"💾 Всего в базе: {get_stats()}"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    finally:
        is_running = False

@dp.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer(
        "🎶 Привет! Я качаю случайные треки с 2000 по 2026.\n\n"
        "Команды:\n"
        "/start — начать скачивание\n"
        "/stats — статистика\n"
        "/reset — сбросить базу (осторожно!)"
    )

@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    await message.answer(f"💾 Всего скачано треков: {get_stats()}")

@dp.message(Command("reset"))
async def reset_cmd(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Только для админа.")
        return
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM downloaded")
        conn.commit()
    await message.answer("🗑️ База очищена.")

# --- ЗАПУСК ---
async def main():
    init_db()
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    print("🤖 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
