"""
Legacy entrypoint shim for backward compatibility.
Delegates to app.py.
"""
from app import app, create_app

if __name__ == "__main__":
    port = app.config.get("PORT", 5001)
    host = app.config.get("HOST", "127.0.0.1")
    app.run(debug=app.config.get("DEBUG", True), host=host, port=port)
