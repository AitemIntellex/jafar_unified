import os
from datetime import datetime
from pathlib import Path
from rich.console import Console

# Импортируем функцию для отправки сообщений
from src.jafar.cli.telegram_handler import send_long_telegram_message
from src.jafar.assistant_core.assistant_api import ask_gemini_assistant
from src.jafar.cli.mac_voice_output_handler import speak_mac_text
import re

console = Console()

def analyze_news(
    snippets: str,
    prompt_file: str,
    analysis_dir: Path,
    analysis_type: str,
) -> str:
    """
    Анализирует новостные фрагменты с помощью AI, отправляет отчет в Telegram и озвучивает сводку.
    """
    try:
        if not snippets:
            return "Новостные фрагменты не предоставлены для анализа."

        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt_template = f.read()

        prompt = prompt_template.format(snippets=snippets)

        console.print(f"[bold blue]🤖 Анализ {analysis_type} новостей с помощью AI...[/bold blue]")
        
        # Вызываем AI для анализа
        analysis_result_dict = ask_gemini_assistant(prompt)
        
        if not analysis_result_dict or "explanation" not in analysis_result_dict:
            return "Не удалось получить ответ от AI ассистента."
            
        full_analysis_text = analysis_result_dict["explanation"]

        # --- Отправка в Telegram ---
        console.print("[cyan]Отправка анализа в Telegram...[/cyan]")
        send_long_telegram_message(f"**Анализ по теме: {analysis_type.upper()}**\n\n{full_analysis_text}")

        # --- Извлечение и озвучивание голосовой сводки ---
        voice_summary = None
        summary_match = re.search(r'"voice_summary":\s*"(.*?)"', full_analysis_text, re.DOTALL)
        if summary_match:
            voice_summary = summary_match.group(1)
            console.print("\n[bold cyan]Озвучиваю краткую сводку (нажмите Ctrl+C для прерывания)...[/bold cyan]")
            speak_mac_text(voice_summary)
        else:
            console.print("[yellow]Голосовая сводка не найдена в ответе.[/yellow]")
            
        return full_analysis_text

    except Exception as e:
        console.print(f"[bold red]Произошла ошибка при анализе новостей: {e}[/bold red]")
        return ""

def extract_key_themes(
    snippets: str,
    prompt_file: str,
    analysis_dir: Path,
    analysis_type: str,
) -> str:
    """
    Извлекает ключевые темы из новостных фрагментов и автоматически отправляет отчет в Telegram.
    """
    try:
        if not snippets:
            return "Новостные фрагменты не предоставлены для анализа."

        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt_template = f.read()

        prompt = prompt_template.format(snippets=snippets)

        console.print(f"[bold blue]🤖 Извлечение ключевых тем из {analysis_type} новостей с помощью AI...[/bold blue]")
        console.print(f"GEMINI_PROMPT_FOR_ANALYSIS:\n{prompt}")

        return ""

    except Exception as e:
        console.print(f"[bold red]Произошла ошибка при извлечении ключевых тем: {e}[/bold red]")
        return ""