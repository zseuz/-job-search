"""Punto de entrada:  py run.py  ->  http://localhost:5000"""
from app import create_app
from app.config import HOST, PORT

if __name__ == "__main__":
    create_app().run(host=HOST, port=PORT, debug=False)
