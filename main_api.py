# api/main_api.py (Minimal Debug Version)
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/api/main_api")
def hello_world():
    return {"message": "Hello from the Python backend!"}

@app.get("/ui")
def get_ui_page():
    return HTMLResponse("<h1>UI Page Works!</h1>")