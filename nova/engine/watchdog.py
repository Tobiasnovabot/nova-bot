from threading import Thread, Event
import time
try:
    from sdnotify import SystemdNotifier
except Exception:  # fallback hvis sdnotify ikke er installert
    class SystemdNotifier:
        def __init__(self): pass
        def notify(self, *_, **__): pass

def start_watchdog(interval_s: int = 10):
    """Starter en enkel systemd WATCHDOG keepalive i egen tråd."""
    n = SystemdNotifier()
    stop = Event()
    def loop():
        while not stop.is_set():
            n.notify("WATCHDOG=1")
            time.sleep(interval_s)
    t = Thread(target=loop, daemon=True)
    t.start()
    return stop
