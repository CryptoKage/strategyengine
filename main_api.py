# api/main_api.py (Minimal Vercel Test Version for Explicit Routing)
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# No root_path needed for this explicit routing method
app = FastAPI()

# This handles requests to the root: your-url.vercel.app/
@app.get("/")
def read_root():
    return {"message": "API Root is active. Please navigate to /ui"}

# This handles requests to: your-url.vercel.app/ui
@app.get("/ui")
def get_ui_page():
    return HTMLResponse("<h1>UI Page Loaded! Explicit routing works.</h1>")