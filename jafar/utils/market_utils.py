from datetime import datetime
import pytz

def get_current_trading_session():
    """
    Determines the current trading session(s) based on UTC time.
    Considers Tokyo, London, and New York sessions, including overlaps.
    """
    # Define session times in UTC
    # Note: These are approximate and don't account for Daylight Saving Time for simplicity.
    # A more robust solution would use a library that handles DST.
    SESSIONS = {
        "Азиатская (Токио)": {"start": 0, "end": 9},
        "Европейская (Лондон)": {"start": 7, "end": 16},
        "Американская (Нью-Йорк)": {"start": 12, "end": 21},
    }

    now_utc = datetime.now(pytz.utc)
    current_hour = now_utc.hour

    active_sessions = []
    for session, times in SESSIONS.items():
        # Handle sessions that cross midnight (like Tokyo if we were using local time)
        if times["start"] <= times["end"]:
            if times["start"] <= current_hour < times["end"]:
                active_sessions.append(session)
        else: # For sessions crossing midnight, e.g., start=23, end=8
            if current_hour >= times["start"] or current_hour < times["end"]:
                active_sessions.append(session)

    if len(active_sessions) > 1:
        # Specifically identify the most important overlap
        if "Европейская (Лондон)" in active_sessions and "Американская (Нью-Йорк)" in active_sessions:
            return "Пересечение сессий: Лондон и Нью-Йорк (самая высокая волатильность)"
        return f"Пересечение сессий: {', '.join(active_sessions)}"
    elif active_sessions:
        return active_sessions[0]
    else:
        return "Межсессионный период (низкая ликвидность)"
