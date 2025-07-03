# api/main_api.py (Minimal Vercel Test Version)
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# This handles the root URL of your deployment
@app.get("/")
def read_root():
    return {"message": "API Root is active. Go to /ui to see the page."}

# This specifically handles the /ui path
@app.get("/ui")
def get_ui_page():
    return HTMLResponse("<h1>UI Page Loaded Successfully!</h1>")
    
# This handles requests to /api/ (Vercel's typical path for API routes)
# The vercel.json will route to this.
@app.get("/api")
def read_api_root():
    return {"message": "API path /api is working."}
    
# A test endpoint to confirm routing
@app.get("/api/test")
def test_endpoint():
    return {"status": "ok", "endpoint": "/api/test"}