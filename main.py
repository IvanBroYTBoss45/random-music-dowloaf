import subprocess
import random
import os
import static_ffmpeg

# --- Настройки ---
START_YEAR = 2000
END_YEAR = 2026
TRACKS_PER_YEAR = 20   # <-- вернули 20
OUTPUT_DIR = "random_music_tracks"

# --- Инициализация static-ffmpeg ---
static_ffmpeg.add_paths()
FFMPEG_PATH = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()[0]
print(f"🎬 Используется ffmpeg: {FFMPEG_PATH}")


def download_tracks_for_year(year):
    print(f"\n🔎 Ищем треки за {year} год...")
    
    search_query = f"after:{year}0101 before:{year}1231"
    
    try:
        # Шаг 1: Поиск ссылок через Android-клиент
        result = subprocess.run(
            [
                "yt-dlp",
                "--extractor-args", "youtube:player_client=android",
                "--flat-playlist",
                "--print", "urls",
                "--no-warnings",
                f"ytsearch{TRACKS_PER_YEAR * 3}:{search_query}"
            ],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8"
        )
        
        all_urls = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        
        if not all_urls:
            print(f"⚠️  Не удалось найти треки за {year} год.")
            return
        
        selected_urls = random.sample(all_urls, min(TRACKS_PER_YEAR, len(all_urls)))
        print(f"📥 Скачиваем {len(selected_urls)} треков за {year} год...")
        
        for i, url in enumerate(selected_urls, 1):
            try:
                subprocess.run(
                    [
                        "yt-dlp",
                        "--extractor-args", "youtube:player_client=android,ios",
                        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                        "--add-header", "Accept-Language:ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                        "--ffmpeg-location", FFMPEG_PATH,
                        "--sleep-interval", "1",
                        "--max-sleep-interval", "3",
                        "-x",
                        "--audio-format", "mp3",
                        "--audio-quality", "0",
                        "-o", f"{OUTPUT_DIR}/%(title)s.%(ext)s",
                        url
                    ],
                    check=True,
                    encoding="utf-8"
                )
                print(f"  ✅ {i}/{len(selected_urls)} — скачано")
            except subprocess.CalledProcessError as e:
                print(f"  ❌ Ошибка при скачивании {url}: {e}")
                continue
                
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при поиске за {year} год:")
        print(f"   STDERR: {e.stderr}")
        print(f"   STDOUT: {e.stdout}")
    except Exception as e:
        print(f"❌ Непредвиденная ошибка за {year} год: {e}")


def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    print(f"🎶 Сбор случайных треков с {START_YEAR} по {END_YEAR} год")
    print(f"📊 По {TRACKS_PER_YEAR} треков в год")
    print(f"📁 Файлы будут сохранены в папку: {OUTPUT_DIR}")
    print("=" * 50)
    
    for year in range(START_YEAR, END_YEAR + 1):
        download_tracks_for_year(year)
    
    print("\n" + "=" * 50)
    print("✨ Готово! Всё собрано.")


if __name__ == "__main__":
    main()
