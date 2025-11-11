import google.generativeai as genai
from jafar.config.settings import GEMINI_API_KEY
import json
import re
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

def ask_assistant(prompt: str, response_type: str = "text") -> dict:
    """
    Sends a prompt to the Gemini model and returns the parsed response.
    """
    # Добавляем инструкции для AI в зависимости от response_type
    if response_type == "code":
        prompt += "\n\nСгенерируй только Python-код, обернутый в ```python...```. Не добавляй пояснений."
    elif response_type == "plan":
        prompt += "\n\nСгенерируй подробный пошаговый план в формате Markdown. Не добавляй лишних слов."
    elif response_type == "json":
        prompt += "\n\nСгенерируй ответ в формате JSON. Не добавляй пояснений."

    try:
        console.print("[blue]📨 I send a request to Gemini...[/blue]")
        response = model.generate_content(prompt)
        console.print("[yellow]⏳ ...[/yellow]")
        
        raw_text = response.text.strip()
        result = robust_parse_response(raw_text)

        # Унифицируем формат
        if result["type"] == "code":
            return {"command": result["content"], "explanation": None, "note": None}
        elif result["type"] == "json":
            return {"command": None, "explanation": result["content"], "note": None}
        else:
            return {"command": None, "explanation": result["content"], "note": None}
            
    except Exception as e:
        return {
            "command": None,
            "explanation": f"Не удалось получить ответ от Gemini.",
            "note": f"Ошибка: {e}",
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
