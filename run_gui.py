"""
Launch the BTC MACD Bot web dashboard.

    python run_gui.py               # http://localhost:8080
    python run_gui.py --port 9090   # custom port
"""

import argparse
import logging
import webbrowser
import threading
import time

import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def _open_browser(port: int) -> None:
    time.sleep(1.2)
    webbrowser.open(f"http://localhost:{port}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BTC MACD Bot – Web GUI")
    parser.add_argument("--host",   default="0.0.0.0",  help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port",   default=8080, type=int, help="Port (default: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    if not args.no_browser:
        threading.Thread(target=_open_browser, args=(args.port,), daemon=True).start()

    print(f"\n  BTC MACD Bot Dashboard → http://localhost:{args.port}\n")
    uvicorn.run(
        "gui.server:app",
        host=args.host,
        port=args.port,
        log_level="warning",
        reload=False,
    )
