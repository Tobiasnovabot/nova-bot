import os
from uvicorn import run
from .app import app

if __name__ == "__main__":
    port = int(os.getenv("API_PORT", "8008"))
    run(app, host="127.0.0.1", port=port, log_level="info")
