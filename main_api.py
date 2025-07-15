#!/usr/bin/env python3
print("--- Starting Crypto Analysis API with Pluggable Strategies ---")

import sys, os, json, traceback, glob, importlib.util
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv; load_dotenv()

# Windows compatibility fix
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Optional libraries
try:
    import pandas as pd
    import pandas_ta as ta
    import ccxt
    DATA_LIBS_AVAILABLE = True
except ImportError:
    DATA_LIBS_AVAILABLE = False
    print("!!! WARNING: Data libs missing (pandas, pandas-ta, ccxt). Functionality limited.")

try:
    import openai
    import httpx
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("!!! WARNING: openai or httpx not installed. LLM features disabled.")

# Strategy config
ENABLED_STRATEGIES = [
    "sma_crossover_strategy","ema_simple_crossover","bollinger_band_mean_reversion",
    "macd_trend_strategy","rsi_mean_reversion","awesome_oscillator_zero_cross",
    "cci_strategy","chaikin_money_flow","hma_slope_trend_strategy",
    "rate_of_change_rocstrategy","stochastic_oscilator","trix_signal_line","vwap_cross_strategy"
]

LOADED_STRATEGIES_FOR_UI = {}
_INTERNAL_STRATEGY_MODULES = {}

# Absolute paths
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "api" / "templates"
STRATEGY_DIR = BASE_DIR / "api" / "strategies"

print("TEMPLATE DIR:", TEMPLATES_DIR)
print("STRATEGY DIR:", STRATEGY_DIR)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def load_strategies():
    global LOADED_STRATEGIES_FOR_UI, _INTERNAL_STRATEGY_MODULES
    LOADED_STRATEGIES_FOR_UI = {}
    _INTERNAL_STRATEGY_MODULES = {}

    files = glob.glob(str(STRATEGY_DIR / "*.py"))
    print("Found strategy files:", files)

    for filepath in files:
        name = Path(filepath).stem
        if name.startswith("__") or name not in ENABLED_STRATEGIES:
            continue
        try:
            spec = importlib.util.spec_from_file_location(name, filepath)
            if spec is None or spec.loader is None:
                print(f"!!! Spec error for {filepath}")
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            required = ['STRATEGY_NAME','calculate_strategy_indicators','run_strategy','STRATEGY_PARAMS_UI','get_chart_overlay_data']
            if not all(hasattr(module, r) for r in required):
                print(f"!!! Incomplete strategy {filepath}")
                continue

            _INTERNAL_STRATEGY_MODULES[name] = module
            LOADED_STRATEGIES_FOR_UI[name] = {
                "name": module.STRATEGY_NAME,
                "slug": getattr(module, 'STRATEGY_SLUG', name),
                "description": getattr(module, 'STRATEGY_DESCRIPTION', ""),
                "params_ui": getattr(module, 'STRATEGY_PARAMS_UI', {})
            }
            print("Loaded strategy:", module.STRATEGY_NAME)
        except Exception as e:
            print(f"!!! Error loading {filepath}: {e}")
            traceback.print_exc()

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_strategies()
    if not LOADED_STRATEGIES_FOR_UI:
        print("!!! WARNING: No strategies loaded.")
    yield
    print("--- Shutdown cleanup ---")

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/", response_class=HTMLResponse)
async def root():
    return "<h1>Not Found</h1>"

@app.get("/ui", response_class=HTMLResponse)
async def get_ui(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "analysis_results": None,
        "error_message": None,
        "request_params": None,
        "available_strategies": LOADED_STRATEGIES_FOR_UI
    })

@app.get("/analyze_ui_with_strategy", response_class=HTMLResponse)
async def analyze_ui_with_strategy(
    request: Request,
    exchange: str = Query("okx"),
    symbol: str = Query("BTC-USDT-SWAP"),
    timeframe: str = Query("4h"),
    strategy_module_name: str = Query(...)
):
    # Paste all your existing fetch, indicator, LLM and strategy logic here
    return templates.TemplateResponse("index.html", {
        "request": request,
        "analysis_results": {},  # your analysis results
        "error_message": None,
        "request_params": {},
        "available_strategies": LOADED_STRATEGIES_FOR_UI
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_api:app", host="127.0.0.1", port=8000, reload=True)
