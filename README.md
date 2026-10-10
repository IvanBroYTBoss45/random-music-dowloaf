# 🎵 Music Year Bot

A Telegram bot built with **aiogram 3.x** that downloads the top 20 "best songs" for each year from 2000 to 2026, converts them to MP3, and sends them straight to the chat.

## ✨ Features

- 🔍 Searches tracks via `yt-dlp` using the query `best songs {year}`
- 🎧 Converts audio to MP3 192 kbps via `ffmpeg`
- 🗃️ Keeps a SQLite cache — already sent tracks are not duplicated
- 🚀 Fully asynchronous, doesn't block the bot while downloading
- 🧹 Automatically deletes MP3 files after sending

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Telegram Bot API | `aiogram 3.x` |
| Downloading | `yt-dlp` |
| Conversion | `static-ffmpeg` + `ffmpeg` |
| Cache | `sqlite3` |
| Async | `asyncio` |

## 📦 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your_user/music-year-bot.git
   cd music-year-bot