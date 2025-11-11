import os
from rich.console import Console
from google.cloud import texttospeech
from google.cloud.texttospeech_v1.services.text_to_speech import TextToSpeechClient
from dotenv import load_dotenv
from pathlib import Path
import re

# Загружаем переменные окружения из корневой папки проекта
dotenv_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=dotenv_path)

console = Console()

# Инициализация клиента Google Text-to-Speech
try:
    client = texttospeech.TextToSpeechClient()
except Exception as e:
    console.print(f"[bold red]Ошибка инициализации клиента Google Text-to-Speech: {e}[/bold red]")
    console.print("[bold yellow]Убедитесь, что переменная окружения GOOGLE_APPLICATION_CREDENTIALS установлена и указывает на корректный JSON-файл ключа сервисного аккаунта.[/bold yellow]")
    client = None

# Вспомогательная функция для синтеза и воспроизведения
def _synthesize_and_play(text, lang_code, voice_name):
    if client is None: return
    try:
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=lang_code,
            name=voice_name,
            ssml_gender=texttospeech.SsmlVoiceGender.MALE
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        temp_audio_file = Path("temp_audio.mp3")
        with open(temp_audio_file, "wb") as out:
            out.write(response.audio_content)
        
        # Воспроизводим аудио (для macOS)
        os.system(f"afplay {temp_audio_file}")
        
        # Удаляем временный файл
        temp_audio_file.unlink()

        console.print(f"[green]✅ Часть сообщения озвучена.[/green]")
    except Exception as e:
        console.print(f"[bold red]❌ Ошибка при озвучивании части сообщения: {e}[/bold red]")

def speak_message(message_or_file_path: str, lang_code: str = "ru-RU", voice_name: str = "ru-RU-Standard-D"):
    """
    Воспроизводит текстовое сообщение голосом с использованием Google Cloud Text-to-Speech API.
    Принимает либо текст, либо путь к файлу (если начинается с '--file ').
    Может принимать опциональный параметр --voice для выбора голоса.
    Требует настройки GOOGLE_APPLICATION_CREDENTIALS.
    """
    if client is None:
        console.print("[bold red]Клиент Google Text-to-Speech не инициализирован. Голосовой вывод недоступен.[/bold red]")
        return

    args_list = message_or_file_path.split()
    custom_voice_name = voice_name
    
    # Ищем и извлекаем аргумент --voice
    if "--voice" in args_list:
        try:
            voice_index = args_list.index("--voice") + 1
            if voice_index < len(args_list):
                custom_voice_name = args_list[voice_index]
                # Удаляем --voice и его значение из списка аргументов
                args_list.pop(voice_index)
                args_list.pop(voice_index - 1)
            else:
                console.print("[bold red]Ошибка: --voice указан без значения.[/bold red]")
                return
        except (ValueError, IndexError):
            console.print("[bold red]Ошибка парсинга аргумента --voice.[/bold red]")
            return

    # Собираем оставшиеся аргументы обратно в строку
    remaining_args = " ".join(args_list)

    text_to_speak = ""
    if remaining_args.startswith('--file '):
        file_path_str = remaining_args[len('--file '):].strip()
        file_path = Path(file_path_str)
        if file_path.is_file():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text_to_speak = f.read()
            except Exception as e:
                console.print(f"[bold red]Ошибка чтения файла для озвучивания: {e}[/bold red]")
                return
        else:
            console.print(f"[bold red]Ошибка: Файл для озвучивания не найден: {file_path}[/bold red]")
            return
    else:
        text_to_speak = remaining_args

    if not text_to_speak.strip():
        console.print("[bold yellow]Нет текста для озвучивания.[/bold yellow]")
        return

    # Очищаем текст от символов Markdown перед озвучиванием
    cleaned_text = re.sub(r'```(?:python|json|bash|)', '', text_to_speak) # Удаляем начало блока кода
    cleaned_text = re.sub(r'```', '', cleaned_text) # Удаляем конец блока кода
    cleaned_text = re.sub(r'[\{\}]', '', cleaned_text) # Удаляем фигурные скобки
    cleaned_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text_to_speak) # Удаляем **жирный**
    cleaned_text = re.sub(r'\* ([^*]+)', r'\1', cleaned_text) # Удаляем * списки
    cleaned_text = re.sub(r'---', '', cleaned_text) # Удаляем ---
    cleaned_text = re.sub(r'\[\d+\]', '', cleaned_text) # Удаляем ссылки типа [1]
    cleaned_text = re.sub(r'_([^_]+)_', r'\1', cleaned_text) # Удаляем _подчеркивания_
    cleaned_text = re.sub(r'`([^`]+)`', r'\1', cleaned_text) # Удаляем `обратные апострофы` (для inline code)
    cleaned_text = re.sub(r'#+', '', cleaned_text) # Удаляем символы # (заголовки)
    cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text) # Сжимаем множественные пустые строки

    # Логика разбиения текста на части
    parts = cleaned_text.split('\n\n') # Разбиваем по абзацам
    
    for part in parts:
        if part.strip():
            if len(part.encode('utf-8')) > 4500: # Если часть слишком длинная, разбиваем по предложениям
                sentences = re.split(r'(?<=[.!?])\s+', part)
                current_part = ""
                for sentence in sentences:
                    if len((current_part + sentence).encode('utf-8')) < 4500:
                        current_part += sentence + " "
                    else:
                        _synthesize_and_play(current_part.strip(), lang_code, custom_voice_name)
                        current_part = sentence + " "
                if current_part.strip():
                    _synthesize_and_play(current_part.strip(), lang_code, custom_voice_name)
            else:
                _synthesize_and_play(part.strip(), lang_code, custom_voice_name)
