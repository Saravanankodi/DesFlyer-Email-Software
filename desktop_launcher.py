"""DesFlyer Windows desktop launcher.

Starts the existing Flask application and background email worker locally, then
opens the application in a native desktop webview. The web application itself
is unchanged, so existing routes/templates remain reusable.
"""

import os
import socket
import threading
import time
import webbrowser

from app import app
from services.campaign_service import run_worker


HOST = "127.0.0.1"
PORT = int(os.getenv("DESFLYER_PORT", "5173"))


def _wait_for_server(host, port, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def _run_server():
    try:
        from waitress import serve
        serve(app, host=HOST, port=PORT, threads=8)
    except ImportError:
        # Development fallback. The packaged desktop build includes Waitress.
        app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)


def main():
    server_thread = threading.Thread(target=_run_server, name="desflyer-web", daemon=True)
    server_thread.start()

    if not _wait_for_server(HOST, PORT):
        raise RuntimeError("DesFlyer could not start its local web server.")

    worker_thread = threading.Thread(target=run_worker, args=(app,), name="desflyer-worker", daemon=True)
    worker_thread.start()

    url = f"http://{HOST}:{PORT}/auth/login"
    try:
        import webview
        webview.create_window("DesFlyer Email Automation", url, width=1440, height=900, min_size=(1100, 700))
        webview.start()
    except ImportError:
        # Useful when developing before pywebview is installed.
        webbrowser.open(url)
        print(f"DesFlyer is running at {url}")
        server_thread.join()


if __name__ == "__main__":
    main()
