from jafar.assistant_core.assistant_api import ask_assistant
from jafar.cli.evolution import log_action


def observe_and_respond(command: str) -> str:
    """Логирует команду и получает максимально информативный ответ ассистента."""
    log_action(command)
    prompt = f"Команда в терминале: {command}\nЧто бы ты предложил сделать дальше?"
    result = ask_assistant(prompt)
    if isinstance(result, dict):
        return (
            result.get("message")
            or result.get("explanation")
            or result.get("response")
            or result.get("text")
            or ""
        )
    return str(result)
