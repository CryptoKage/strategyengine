# api/main_api.py (Minimal Vercel Test Version with root_path)
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os

# Get the root path from Vercel's environment variables if it exists
# This helps FastAPI generate correct docs and URLs behind Vercel's proxy
ROOT_PATH = os.getenv("ROOT_PATH", "") 

app = FastAPI(root_path=ROOT_PATH)

# The root of our app, now at the root of the deployment
@app.get("/")
def read_root():
    return {"message": "API Root is active. Go to /ui to see the page."}

# This will handle requests to your-url.com/ui
@app.get("/ui")
def get_ui_page():
    return HTMLResponse("<h1>UI Page Loaded Successfully! Vercel Routing Works!</h1>")
        
# This will handle requests to your-url.com/api/test
@app.get("/api/test")
def test_endpoint():
    return {"status": "ok", "endpoint": "/api/test"}