from app import create_app
from config import ProductionConfig

# WSGI application callable for production servers (Gunicorn, uWSGI, etc.)
app = create_app(ProductionConfig)

if __name__ == "__main__":
    app.run()
