import os
from rich.console import Console
from rich.panel import Panel
import threading
import tempfile
import subprocess
import sys
import queue
import time

from google.cloud import texttospeech

console = Console()

# Очередь для сообщений TTS
tts_queue = queue.Queue()

# Инициализация клиента Google Cloud Text-to-Speech
client = texttospeech.TextToSpeechClient()

def tts_thread_worker():
    """Рабочий поток для озвучивания сообщений из очереди с помощью Google Cloud TTS."""
    while True:
        text = tts_queue.get()
        if text is None: # Сигнал для завершения потока
            break
        try:

            synthesis_input = texttospeech.SynthesisInput(text=text)

            # Выбор мужского русского голоса
            voice = texttospeech.VoiceSelectionParams(
                language_code="ru-RU",
                name="ru-RU-Wavenet-D", # Мужской голос, более естественный
                ssml_gender=texttospeech.SsmlVoiceGender.MALE,
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )

            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )

            # Воспроизводим аудиофайл
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                fp.write(response.audio_content)
                audio_file_path = fp.name

            if os.name == 'posix': # macOS, Linux
                if sys.platform == 'darwin': # macOS
                    subprocess.run(["afplay", audio_file_path], check=True)
                else: # Linux
                    subprocess.run(["mpg123", audio_file_path], check=True) # Предполагаем mpg123 установлен
            elif os.name == 'nt': # Windows
                subprocess.run(["start", audio_file_path], shell=True, check=True) # Для Windows

            os.remove(audio_file_path) # Удаляем временный файл после воспроизведения
        except Exception as e:
            console.print(f"[red]Ошибка при озвучивании в потоке (Google Cloud TTS): {e}[/red]")
        finally:
            time.sleep(0.2) # Небольшая задержка, чтобы звук полностью прекратился
        tts_queue.task_done()

# Запускаем поток TTS при инициализации модуля
tts_worker_thread = threading.Thread(target=tts_thread_worker, daemon=True)
tts_worker_thread.start()

def speak_response(text):
    """Помещает текстовый ответ в очередь для озвучивания."""
    tts_queue.put(text)
