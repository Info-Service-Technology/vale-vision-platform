import os
import threading

import uvicorn
from worker import main as start_worker
from app.api import app


def start_worker_thread() -> None:
    thread = threading.Thread(target=start_worker, daemon=True, name="inference-worker")
    thread.start()
    return thread


def main() -> None:
    start_worker_thread()

    port = int(os.getenv("INFERENCE_API_PORT", "8001"))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
