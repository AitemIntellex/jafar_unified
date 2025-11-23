import time
import argparse
import os
import sys
from datetime import datetime, timedelta

# Добавляем корневую директорию проекта в sys.path для корректных импортов
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from jafar.utils.topstepx_api_client import TopstepXClient
from jafar.cli.muxlisa_voice_output_handler import speak_muxlisa_text
from jafar.cli.telegram_handler import send_long_telegram_message

# --- Константы ---
INITIAL_POLL_INTERVAL_SECONDS = 15
SUBSEQUENT_POLL_INTERVAL_SECONDS = 30
MONITOR_TIMEOUT_HOURS = 8   # Максимальное время работы монитора (в часах)
LOG_DIR = os.path.join(project_root, "logs", "trade_agents")
os.makedirs(LOG_DIR, exist_ok=True)

def log_message(agent_id, message):
    """Записывает сообщение в лог-файл агента."""
    log_file = os.path.join(LOG_DIR, f"agent_{agent_id}.log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def check_order_status(client, account_id, order_id, agent_id):
    """Проверяет статус конкретного ордера."""
    try:
        # Ищем ордер за последние 24 часа
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        response = client.get_orders(account_id, start_time, end_time)
        
        if response and response.get("orders"):
            for order in response["orders"]:
                if order.get("id") == order_id:
                    return order # Возвращаем полный объект ордера
        return None
    except Exception as e:
        log_message(agent_id, f"ERROR: Ошибка при проверке статуса ордера: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Фоновый Агент Сопровождения Сделки.")
    parser.add_argument("--order-id", type=int, required=True)
    parser.add_argument("--account-id", type=int, required=True)
    parser.add_argument("--contract-id", type=str, required=True)
    parser.add_argument("--expected-side", type=str, required=True)
    args = parser.parse_args()

    agent_id = f"order_{args.order_id}"
    log_message(agent_id, f"--- [ФАЗА 1] Агент запущен. Цель: ордер #{args.order_id} ({args.expected_side} {args.contract_id}) ---")

    start_time = time.time()
    
    try:
        client = TopstepXClient()
    except Exception as e:
        log_message(agent_id, f"CRITICAL: Не удалось инициализировать API клиент: {e}")
        return

    # =========================================================================
    # --- ФАЗА 1: Мониторинг исполнения ордера ---
    # =========================================================================
    order_filled = False
    first_check = True
    while not order_filled:
        # --- Проверка таймаута ---
        if time.time() - start_time > MONITOR_TIMEOUT_HOURS * 3600:
            log_message(agent_id, "TIMEOUT: Таймаут мониторинга. Ордер не был исполнен за 8 часов. Завершение.")
            notification_text = f"Diqqat! #{args.order_id} raqamli order monitoringi 8 soatdan keyin vaqt tugashi bilan yakunlandi."
            # speak_muxlisa_text(notification_text) # Раскомментировать позже
            send_long_telegram_message(f"⚠️ **Agent Timeout (Phase 1)**\nOrder ID: #{args.order_id}\nContract: {args.contract_id}")
            return # Завершаем работу

        log_message(agent_id, "PHASE 1: Проверка статуса ордера...")
        order_details = check_order_status(client, args.account_id, args.order_id, agent_id)

        if order_details:
            status = order_details.get("status")
            log_message(agent_id, f"PHASE 1: Текущий статус ордера: {status}")
            
            # Статус 2: Filled (Исполнен)
            if status == 2:
                log_message(agent_id, "SUCCESS: Ордер исполнен! Переход ко второй фазе.")
                notification_text = f"Janob, sizning {args.expected_side} {args.contract_id} uchun qo'yilgan #{args.order_id} raqamli orderiz ishga tushdi. Pozitsiya ochiq. Savdoni kuzatish rejimiga o'taman."
                # speak_muxlisa_text(notification_text) # Раскомментировать позже
                send_long_telegram_message(f"✅ **Ордер Исполнен!**\nID: #{args.order_id}\nИнструмент: {args.contract_id}\n\nАгент переходит в режим сопровождения сделки.")
                order_filled = True
                continue # Переходим к следующей фазе
            
            # Статусы завершения: Cancelled, Rejected
            elif status in [3, 4]:
                status_text = "Cancelled" if status == 3 else "Rejected"
                log_message(agent_id, f"TERMINATED: Ордер {status_text}. Завершение работы агента.")
                notification_text = f"Janob, sizning #{args.order_id} raqamli orderiz {status_text.lower()} qilindi."
                # speak_muxlisa_text(notification_text) # Раскомментировать позже
                send_long_telegram_message(f"❌ **Ордер {status_text}**\nID: #{args.order_id}\nИнструмент: {args.contract_id}")
                return # Завершаем работу
        else:
            log_message(agent_id, "PHASE 1: Не удалось получить детали ордера. Повторная проверка через 30 сек.")

        # --- Ожидание перед следующей проверкой ---
        if first_check:
            time.sleep(INITIAL_POLL_INTERVAL_SECONDS)
            first_check = False
        else:
            time.sleep(SUBSEQUENT_POLL_INTERVAL_SECONDS)

    # =========================================================================
    # --- ФАЗА 2: Сопровождение открытой позиции ---
    # =========================================================================
    log_message(agent_id, "--- [ФАЗА 2] Начало сопровождения открытой позиции. (Логика будет добавлена) ---")
    
    # Здесь будет цикл, который каждые 3 минуты собирает данные,
    # обращается к Gemini и принимает решения.
    # Пока что просто завершаем работу для теста.
    
    log_message(agent_id, "--- Агент завершил работу ---")


if __name__ == "__main__":
    main()
