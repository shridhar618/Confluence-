import os
import sys

if sys.version_info < (3, 14):
    import eventlet

    eventlet.monkey_patch()

from app import create_app, socketio

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    debug = os.getenv("DEBUG", "1").lower() in {"1", "true", "yes", "on"}
    socketio.run(app, host="0.0.0.0", port=port, debug=debug, use_reloader=debug)
