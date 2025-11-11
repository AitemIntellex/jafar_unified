# checkers/check_internet.py
import socket

def check_internet_status(host="8.8.8.8", port=53, timeout=2):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return "connected"
    except Exception:
        return "offline"
