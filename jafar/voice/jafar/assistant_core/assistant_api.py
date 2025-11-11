from openai import OpenAI
from src.jafar.config.settings import OPENAI_API_KEY, OPENAI_ASSISTANT_ID, OPENAI_MODEL
from src.jafar.config.constants import JAFAR_THREAD_FILE
from src.jafar.utils.gemini_api import ask_gemini_text_only
import json
import re
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from src.jafar.utils.gemini_api import ask_gemini_text_only

console = Console()
client = OpenAI(api_key=OPENAI_API_KEY)


def ask_gemini_assistant(prompt: str) -> dict:
    """
    Sends a text prompt to the Gemini assistant and returns the parsed response.
    """
    console.print("[blue]📨 Отправка запроса в Gemini...[/blue]")
    try:
        response_text = ask_gemini_text_only(prompt)
        if "Ошибка:" in response_text:
            return {"explanation": response_text}
        
        # Возвращаем ответ в формате, совместимом с остальным кодом
        return {"explanation": response_text}
    except Exception as e:
        console.print(f"[red]Произошла ошибка при работе с Gemini: {e}[/red]")
        return {"explanation": f"Ошибка Gemini: {e}"}


def get_thread_id():
    """Retrieve or create a thread ID."""
    if JAFAR_THREAD_FILE.exists():
        return JAFAR_THREAD_FILE.read_text().strip()
    thread = client.beta.threads.create()
    JAFAR_THREAD_FILE.parent.mkdir(parents=True, exist_ok=True)
    JAFAR_THREAD_FILE.write_text(thread.id)
    return thread.id


def ask_assistant(prompt: str, response_type: str = "text") -> dict:
    """
    Sends a prompt to the assistant and returns the parsed response.
    Automatically recreates the thread if the current one is stuck.
    """
    # Добавляем инструкции для AI в зависимости от response_type
    if response_type == "code":
        prompt = "Сгенерируй только Python-код, обернутый в ```python...```. Не добавляй пояснений.\n\n" + prompt
    elif response_type == "plan":
        prompt = "Сгенерируй подробный пошаговый план в формате Markdown. Не добавляй лишних слов.\n\n" + prompt
    elif response_type == "json":
        prompt = "Сгенерируй ответ в формате JSON. Не добавляй пояснений.\n\n" + prompt
    elif response_type == "text":
        prompt = "Твой ответ должен содержать ТОЛЬКО запрошенный анализ. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО повторять промпт, новостные фрагменты, включать раздел \"Источники\", ссылки, рекламные материалы или любую другую дополнительную информацию, не относящуюся напрямую к анализу. Начни свой ответ СРАЗУ с анализа.\n\n" + prompt

    last_error = None

    for _ in range(2):  # Попробуем максимум дважды
        thread_id = get_thread_id()
        try:
            console.print("[blue]📨 I send a request...[/blue]")
            client.beta.threads.messages.create(
                thread_id=thread_id, role="user", content=prompt
            )

            # Poll the assistant (ждём завершения run)
            console.print("[yellow]⏳ ...[/yellow]")
            client.beta.threads.runs.create_and_poll(
                thread_id=thread_id, assistant_id=OPENAI_ASSISTANT_ID
            )

            messages = client.beta.threads.messages.list(thread_id=thread_id)

            # Extract the latest text message
            latest = next(
                (
                    block.text.value
                    for msg in messages.data
                    for block in msg.content
                    if hasattr(block, "text") and getattr(block, "text")
                ),
                "",
            )

            result = robust_parse_response(latest.strip())
            # Унифицируем формат
            if result["type"] == "code":
                return {"command": result["content"], "explanation": None, "note": None}
            elif result["type"] == "json":
                return {"command": None, "explanation": result["content"], "note": None}
            else:
                return {"command": None, "explanation": result["content"], "note": None}
        except Exception as e:
            last_error = e
            error_msg = str(e).lower()
            # Если "run is active" — значит thread завис, пересоздаём
            if "run is active" in error_msg or "while a run" in error_msg:
                console.print(
                    "[red]⚠️ Thread завис (run is active), пересоздаём thread...[/red]"
                )
                if JAFAR_THREAD_FILE.exists():
                    JAFAR_THREAD_FILE.unlink()
                continue
            else:
                raise
    return {
        "command": None,
        "explanation": "Не удалось получить ответ от ассистента (ошибка run/thread)",
        "note": f"Ошибка: {last_error}",
    }


import json
import re


def robust_parse_response(raw):
    # 1. Попробуй как json (прямой ответ)
    try:
        parsed_json = json.loads(raw)
        return {"type": "json", "content": parsed_json}
    except Exception:
        pass

    # 2. Ищи python-код внутри markdown блока
    code_match = re.search(r"```python(.*?)```", raw, re.DOTALL)
    if code_match:
        code = code_match.group(1).strip()
        return {"type": "code", "content": code}

    # 3. Ищи просто json-блок внутри markdown
    json_match = re.search(r"```json(.*?)```", raw, re.DOTALL)
    if json_match:
        try:
            parsed_json_block = json.loads(json_match.group(1).strip())
            return {"type": "json", "content": parsed_json_block}
        except Exception:
            pass

    # 4. Если ничего не вышло — это просто текст
    return {"type": "text", "content": raw}