import re
import os
import shlex
import subprocess
import time
import whisper
import numpy as np
import requests
from pathlib import Path

# --- .env faylini yuklash (run.py'ga ko'chirildi) ---
MUXLISA_API_KEY = os.environ.get("MUXLISA_API_KEY")
STT_PROVIDER = os.environ.get("STT_PROVIDER", "whisper")

# --- Константы ---
REC_RATE = 16000
# Use a path relative to the project root for temporary files
TEMP_AUDIO_FILE = Path(__file__).parent.parent / "temp" / "output.wav"
AUDIO_ASSETS_DIR = Path(__file__).parent.parent / "assets" / "audio"

# --- Инициализация моделей ---
def init_whisper_model(model_size="base"):
    """Загружает и возвращает модель Whisper."""
    if STT_PROVIDER == "whisper":
        print(f"Загрузка локальной модели Whisper '{model_size}'...")
        model = whisper.load_model(model_size)
        print("Модель Whisper загружена.")
        return model
    return None

# --- Функции STT ---
def stt_from_buffer(model, audio_buffer: bytes, language: str) -> str:
    """
    Распознает речь из аудио-буфера, используя выбранный STT провайдер.
    """
    if STT_PROVIDER == "muxlisa":
        return stt_muxlisa(audio_buffer)
    else:
        return stt_whisper(model, audio_buffer, language)

def stt_whisper(model, audio_buffer: bytes, language: str) -> str:
    """
    Распознает речь с помощью локальной модели Whisper.
    """
    if not model:
        print("Ошибка: Модель Whisper не загружена.")
        return ""
    try:
        audio_np = np.frombuffer(audio_buffer, dtype=np.int16).astype(np.float32) / 32768.0
        result = model.transcribe(audio_np, fp16=False, language=language)
        return result['text'].strip()
    except Exception as e:
        print(f"Ошибка локального STT (Whisper): {e}")
        return ""

def stt_muxlisa(audio_buffer: bytes) -> str:
    """
    Распознает речь с помощью API от Muxlisa AI.
    """
    if not MUXLISA_API_KEY:
        print("Ошибка: API ключ для Muxlisa не найден в .env файле.")
        return ""
    temp_audio_path = Path(__file__).parent.parent / "temp" / "stt_input.wav"
    os.makedirs(temp_audio_path.parent, exist_ok=True)
    import wave
    with wave.open(str(temp_audio_path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(REC_RATE)
        wf.writeframes(audio_buffer)
    try:
        url = 'https://service.muxlisa.uz/api/v2/stt'
        headers = {'x-api-key': MUXLISA_API_KEY}
        with open(temp_audio_path, 'rb') as f:
            files = {'audio': (temp_audio_path.name, f, 'audio/wav')}
            response = requests.post(url, headers=headers, files=files)
        if response.status_code == 200:
            return response.json().get("text", "")
        else:
            print(f"Ошибка от Muxlisa STT API: {response.status_code} - {response.text}")
            return ""
    except Exception as e:
        print(f"Ошибка STT (Muxlisa): {e}")
        return ""
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

# --- Функции TTS ---
def speak_text(text: str, interrupt_event):
    """
    Озвучивает текст, используя предварительно записанные аудиофайлы или API от Muxlisa AI.
    """
    if interrupt_event.is_set() or not text.strip():
        return

    # 1. Проверка на наличие готового аудиофайла
    cleaned_text_for_filename = "".join([word[0] for word in text.lower().split() if word])
    pre_recorded_file = AUDIO_ASSETS_DIR / f"{cleaned_text_for_filename}.wav"

    if pre_recorded_file.exists():
        command = f"afplay {shlex.quote(str(pre_recorded_file))}"
        process = subprocess.Popen(command, shell=True)
        while process.poll() is None:
            if interrupt_event.is_set():
                process.terminate()
                break
            time.sleep(0.1)
        return

    # 2. Если файла нет, используем Muxlisa API
    if not MUXLISA_API_KEY:
        print("Ошибка: API ключ для Muxlisa не найден в .env файле.")
        return

    url = 'https://service.muxlisa.uz/api/v2/tts'
    headers = {'Content-Type': 'application/json', 'x-api-key': MUXLISA_API_KEY}
    payload = {"text": text, "speaker": 1, "rate": 1.2}

    process = None
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            os.makedirs(TEMP_AUDIO_FILE.parent, exist_ok=True)
            with open(TEMP_AUDIO_FILE, 'wb') as f:
                f.write(response.content)
            command = f"afplay {shlex.quote(str(TEMP_AUDIO_FILE))}"
            process = subprocess.Popen(command, shell=True)
            while process.poll() is None:
                if interrupt_event.is_set():
                    process.terminate()
                    break
                time.sleep(0.1)
        else:
            print(f"Ошибка от Muxlisa API: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Ошибка синтеза речи: {e}")
    finally:
        if process: process.wait()
        if os.path.exists(TEMP_AUDIO_FILE):
            os.remove(TEMP_AUDIO_FILE)

def speak_long_text(full_text: str, interrupt_event):
    """
    Разбивает длинный текст на предложения и озвучивает их по очереди.
    """
    if interrupt_event.is_set(): interrupt_event.clear()
    text_no_markdown = re.sub(r'[\*_`#]', '', full_text)
    sentences = re.split(r'(?<=[.!?])\s+', text_no_markdown)
    for sentence in sentences:
        if interrupt_event.is_set(): break
        if sentence:
            speak_text(sentence, interrupt_event)

def speak_streaming(response_stream, interrupt_event):
    """
    Озвучивает текст из потока по предложениям в реальном времени.
    """
    sentence_buffer = ""
    if interrupt_event.is_set(): interrupt_event.clear()
    for chunk in response_stream:
        if interrupt_event.is_set(): break
        try:
            text_part = chunk.text
        except ValueError:
            continue
        sentence_buffer += text_part
        if re.search(r'[.!?]', sentence_buffer):
            parts = re.split(r'(?<=[.!?])\s+', sentence_buffer)
            for part in parts[:-1]:
                if part:
                    speak_text(part, interrupt_event)
                    if interrupt_event.is_set(): break
            if interrupt_event.is_set(): break
            sentence_buffer = parts[-1]
    if not interrupt_event.is_set() and sentence_buffer.strip():
        speak_text(sentence_buffer, interrupt_event)
