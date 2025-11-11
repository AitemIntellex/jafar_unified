
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time
from io import StringIO

def fetch_and_save_economic_calendar_data():
    """
    Fetches economic calendar data from Investing.com for the next 24 hours,
    filters for high-importance news for major currencies, and saves it to a text file.
    Always fetches fresh data.
    """
    output_path = Path(__file__).parent.parent.parent / "temp" / "economic_calendar_data.txt"
    output_path.parent.mkdir(exist_ok=True)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    url = "https://www.investing.com/economic-calendar/"

    try:
        # print("Fetching fresh economic calendar...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        table = soup.find('table', {'id': 'economicCalendarData'})
        if not table:
            # print("Could not find the economic calendar table.")
            return

        df = pd.read_html(StringIO(str(table)))[0]
        
        # --- Data Cleaning and Processing ---
        df.dropna(how='all', inplace=True)
        df = df.iloc[:, [0, 1, 2, 3]]
        df.columns = ['Time', 'Currency', 'Importance', 'Event']
        df = df[df['Currency'].isin(['USD', 'EUR', 'GBP', 'JPY', 'CNY'])]
        df['Importance'] = df['Importance'].astype(str)
        df = df[df['Importance'].str.contains('bull bull bull', na=False)]
        df.drop('Importance', axis=1, inplace=True)
        df = df[df['Time'].str.contains(r'\d{1,2}:\d{2}', na=False)]
        df.reset_index(drop=True, inplace=True)

        if df.empty:
            result_string = "No high-importance economic events found for major currencies in the next 24 hours."
        else:
            result_string = "High-Importance Economic Events (Next 24h):\n"
            result_string += df.to_string(index=False)

        output_path.write_text(result_string, encoding="utf-8")
        # print(f"Fresh economic calendar data saved to {output_path}")

    except requests.RequestException as e:
        print(f"Error fetching data from Investing.com: {e}")
    except Exception as e:
        print(f"An error occurred during calendar processing: {e}")

def fetch_economic_calendar_data():
    """
    Fetches and returns economic calendar data as a string.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    url = "https://www.investing.com/economic-calendar/"

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        table = soup.find('table', {'id': 'economicCalendarData'})
        if not table:
            return "Не удалось найти таблицу экономического календаря."

        df = pd.read_html(StringIO(str(table)))[0]
        
        df.dropna(how='all', inplace=True)
        df = df.iloc[:, [0, 1, 2, 3]]
        df.columns = ['Time', 'Currency', 'Importance', 'Event']
        df = df[df['Currency'].isin(['USD', 'EUR', 'GBP', 'JPY', 'CNY'])]
        df['Importance'] = df['Importance'].astype(str)
        df = df[df['Importance'].str.contains('bull bull bull', na=False)]
        df.drop('Importance', axis=1, inplace=True)
        df = df[df['Time'].str.contains(r'\d{1,2}:\d{2}', na=False)]
        df.reset_index(drop=True, inplace=True)

        if df.empty:
            return "Важных экономических событий для основных валют в ближайшие 24 часа не найдено."
        else:
            return "Важные экономические события (24 часа):\n" + df.to_string(index=False)

    except Exception as e:
        return f"Ошибка при получении данных календаря: {e}"


if __name__ == '__main__':
    fetch_and_save_economic_calendar_data()
