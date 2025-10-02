import time
import logging

# Konfigurer logging
logging.basicConfig(filename='circuit_breaker.log', level=logging.INFO)

class CircuitBreaker:
    def __init__(self, threshold=0.10):
        self.threshold = threshold
        self.last_price = None
        self.trading_active = True

    def update_price(self, current_price):
        if self.last_price is None:
            self.last_price = current_price
            return

        drawdown = (self.last_price - current_price) / self.last_price
        if drawdown >= self.threshold:
            self.pause_trading()
        else:
            self.last_price = current_price

    def pause_trading(self):
        if self.trading_active:
            self.trading_active = False
            logging.info(f'Trading paused due to {self.threshold * 100}% drawdown at {time.strftime("%Y-%m-%d %H:%M:%S")}.)
            print("Trading paused.")

    def resume_trading(self):
        if not self.trading_active:
            self.trading_active = True
            logging.info(f'Trading resumed at {time.strftime("%Y-%m-%d %H:%M:%S")}.)
            print("Trading resumed.")

# Eksempel på hvordan CircuitBreaker kan brukes
# cb = CircuitBreaker()
# while True:
#     current_price = get_current_price()  # Implementer denne funksjonen for å hente nåværende pris
#     cb.update_price(current_price)
#     time.sleep(60)  # Sjekk prisen hvert minutt