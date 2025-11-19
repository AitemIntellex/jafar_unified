
import sys
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Добавляем путь к jafar_unified в sys.path и загружаем .env
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
load_dotenv()

from jafar.cli.btrade_handlers import _run_autonomous_monitoring

if __name__ == "__main__":
    # Передаем параметры в функцию мониторинга
    _run_autonomous_monitoring(
        contract_id='CON.F.US.MGC.Z25',
        instrument_query='gold',
        action='Long',
        entry_price=calculated,
        stop_loss=4057.0,
        take_profit=4100.0,
        position_size=50,
        account_id='14497974',
        tick_size=0.1
    )
