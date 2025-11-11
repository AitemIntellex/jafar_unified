import os
import time
import pyaudio
import pvporcupine
import struct
import re
import random
import traceback
import numpy as np
from dotenv import load_dotenv
import google.generativeai as genai
from thefuzz import fuzz

# Локальные импорты
from .speech import speak_text, stt_from_buffer
from .audio_utils import calibrate_noise_level
from jafar.cli.atrade_handlers import atrade_command
from ..cli.interactive_analyzer import start_interactive_analysis

# --- Конфигурация ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
PICOVOICE_ACCESS_KEY = os.environ.get("PICOVOICE_ACCESS_KEY")

# --- Глобальные переменные ---
REC_RATE = 16000
CONVERSATION_TIMEOUT_S = 20
SILENCE_DURATION_S = 0.7

# --- Вспомогательная функция для нечеткого поиска ---
def is_command_present(text, keywords, threshold=75):
    """Проверяет, присутствует ли одно из ключевых слов в тексте с определенным порогом схожести."""
    for keyword in keywords:
        if fuzz.partial_ratio(keyword, text) >= threshold:
            return True
    return False

# --- Основной цикл диалога ---
def handle_conversation(mic_stream, porcupine, interrupt_event, queue):
    """Управляет полным циклом диалога с динамической калибровкой шума и состоянием."""
    print("[DEBUG] ==> Entered handle_conversation.")
    
    is_speaking = False
    conversation_state = "normal" 

    def speak_and_set_flag(text_func, text):
        nonlocal is_speaking
        is_speaking = True
        queue.put({"type": "status", "value": "Говорю"})
        result = text_func(text, interrupt_event)
        is_speaking = False
        return result

    print("Динамическая калибровка...")
    queue.put({"type": "status", "value": "Обработка"})
    silence_threshold = calibrate_noise_level(mic_stream, porcupine.frame_length, porcupine.sample_rate, duration=1.0)
    print(f"Новый порог тишины: {silence_threshold:.2f}")

    model_pro = genai.GenerativeModel('models/gemini-2.5-pro')
    
    last_interaction_time = time.time()
    print("[DEBUG] Starting main conversation loop...")

    while time.time() - last_interaction_time < CONVERSATION_TIMEOUT_S:
        print("[DEBUG] Top of the main loop. Listening...")
        print("Слушаю вашу команду...")
        queue.put({"type": "status", "value": "Слушаю"})
        
        # ... (audio recording logic from previous stable version) ...
        frames = []
        recording = False
        silence_frames = 0
        max_silence_frames = int((porcupine.sample_rate / porcupine.frame_length) * SILENCE_DURATION_S)
        warmup_frames_count = 0
        MIN_WARMUP_FRAMES = 3
        
        print("[DEBUG] Starting audio recording loop...")
        while True:
            if time.time() - last_interaction_time > CONVERSATION_TIMEOUT_S:
                print("[DEBUG] Conversation timeout reached inside recording loop.")
                return
            pcm_data = mic_stream.read(porcupine.frame_length, exception_on_overflow=False)
            if is_speaking: continue
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm_data)
            rms = np.sqrt(np.mean(np.array(pcm, dtype=float) ** 2))
            queue.put({"type": "rms", "value": rms})
            if rms > silence_threshold:
                silence_frames = 0
                if not recording:
                    warmup_frames_count += 1
                    if warmup_frames_count >= MIN_WARMUP_FRAMES:
                        print("[DEBUG] Recording started.")
                        recording = True
                if recording:
                    frames.append(pcm_data)
            elif recording:
                silence_frames += 1
                if silence_frames > max_silence_frames:
                    print("[DEBUG] Silence detected. Exiting recording loop.")
                    break
            else:
                warmup_frames_count = 0
        
        if not frames: continue
        
        user_text_uzbek = stt_from_buffer(None, b"".join(frames), "uz")
        
        if not user_text_uzbek:
            print("Речь не распознана.")
            continue
            
        print(f"Вы: {user_text_uzbek}")
        user_text_uzbek_lower = user_text_uzbek.lower()

        # --- ЯНГИ МАНТИҚ ---
        # 1. Тезкор жавоблар
        if "assalomu aleykum" in user_text_uzbek_lower:
            speak_and_set_flag(speak_text, "Va alaykum assalom")
            last_interaction_time = time.time()
            continue

        # 2. Командаларни аниқлаш
        NEWS_KEYWORDS = ["nima gap", "yangiliklar", "novosti"]
        SUPER_ANALYSIS_KEYWORDS = ["tahlil", "analiz", "bozorni ko'r", "super tahlil"]
        EXIT_KEYWORDS = ["xayr", "rahmat", "yetarli", "ko'rishguncha", "bo'ldi"]

        if is_command_present(user_text_uzbek_lower, SUPER_ANALYSIS_KEYWORDS):
            speak_and_set_flag(speak_text, "Qaysi instrumentni tahlil qilamiz?")
            conversation_state = "awaiting_atrade_instrument"
        elif is_command_present(user_text_uzbek_lower, NEWS_KEYWORDS):
            speak_and_set_flag(speak_text, "Qaysi mavzu bo'yicha yangiliklar kerak?")
            conversation_state = "awaiting_news_topic"
        elif is_command_present(user_text_uzbek_lower, EXIT_KEYWORDS):
            speak_and_set_flag(speak_text, "Yaxshi, janob.")
            break
        
        # 3. Агар команда бўлмаса, ҳолатни текшириш
        elif conversation_state == "awaiting_atrade_instrument":
            speak_and_set_flag(speak_text, f"{user_text_uzbek} uchun super tahlil boshlanmoqda...")
            atrade_command(user_text_uzbek)
            conversation_state = "normal"
        elif conversation_state == "awaiting_news_topic":
            speak_and_set_flag(speak_text, f"{user_text_uzbek} bo'yicha yangiliklar tahlilini boshlayapman.")
            start_interactive_analysis(user_text_uzbek)
            conversation_state = "normal"
            
        # 4. Агар ҳеч нарса мос келмаса, бу оддий чат
        else:
            print("Джафар думает...")
            response = model_pro.generate_content(f"You are a helpful assistant named Jafar. User asks in Uzbek: '{user_text_uzbek}'. Respond in Uzbek (Latin script).")
            speak_and_set_flag(speak_text, response.text)
        
        last_interaction_time = time.time()

    print("[DEBUG] <== Exiting handle_conversation.")

# --- Точка входа ---
def main(interrupt_event, queue, main_exit_event):
    pa = None
    porcupine = None
    mic_stream = None
    activation_count = 0
    GREETING_TITLES = ["janob", "maestro", "ustoz", "Timur aka"]

    try:
        # ... (porcupine and mic_stream initialization) ...
        project_root = os.path.abspath(os.path.dirname(__file__))
        # IMPORTANT: Adjust the path to the keyword file based on the new structure
        keyword_file_path = os.path.join(project_root, "..", "assets", "jafar_en_mac_v3_0_0.ppn") # Placeholder, we need to move the file

        if not PICOVOICE_ACCESS_KEY:
            print("Xatolik: PICOVOICE_ACCESS_KEY .env faylida topilmadi. 'Джафар' сўзи ишламайди.")
        else:
             porcupine = pvporcupine.create(
                access_key=PICOVOICE_ACCESS_KEY,
                keyword_paths=[keyword_file_path],
                sensitivities=[0.8]
            )
        
        pa = pyaudio.PyAudio()
        mic_stream = pa.open(
            rate=porcupine.sample_rate if porcupine else REC_RATE, 
            channels=1, 
            format=pyaudio.paInt16,
            input=True, 
            frames_per_buffer=porcupine.frame_length if porcupine else 512
        )
        
        print("Ожидание команды 'Джафар' или PTT...")
        queue.put({"type": "status", "value": "Ожидание"})
        
        while not main_exit_event.is_set():
            # PTT or Wake Word check
            pcm_data = mic_stream.read(porcupine.frame_length if porcupine else 512, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * (porcupine.frame_length if porcupine else 512), pcm_data)
            
            ptt_activated = False
            try:
                message = queue.get(block=False)
                if message.get("type") == "ptt_activate":
                    ptt_activated = True
            except Exception:
                pass

            wake_word_detected = porcupine and porcupine.process(pcm) >= 0

            if ptt_activated or wake_word_detected:
                print(f"\nАктивация {'через PTT' if ptt_activated else 'по слову'}!")
                
                activation_count += 1
                title = random.choice(GREETING_TITLES)
                if activation_count == 1:
                    speak_text(f"Assalomu aleykum, {title}", interrupt_event)
                else:
                    responses = [f"Labbay, {title}?", f"Eshitaman, {title}."]
                    speak_text(random.choice(responses), interrupt_event)

                handle_conversation(mic_stream, porcupine, interrupt_event, queue)
                print("Ожидание команды 'Джафар' или PTT...")
                queue.put({"type": "status", "value": "Ожидание"})

    except KeyboardInterrupt:
        print("\nВыход из jafar_core.")
    except Exception as e:
        print(f"Произошла ошибка в jafar_core: {e}")
        traceback.print_exc()
    finally:
        if porcupine: porcupine.delete()
        if mic_stream: mic_stream.close()
        if pa: pa.terminate()
        print("Ресурсы jafar_core освобождены.")
