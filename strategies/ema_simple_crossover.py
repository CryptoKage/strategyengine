# strategies/ema_simple_crossover.py
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional

STRATEGY_NAME = "Simple EMA Crossover"
STRATEGY_SLUG = "ema_simple_cross"
STRATEGY_DESCRIPTION = "Basic EMA crossover strategy. BUY on fast EMA crossing above slow EMA, SELL on cross below."
STRATEGY_PARAMS_UI = {
    "ema_fast_period": {"label": "Fast EMA Period", "default": 9, "type": "number", "min": 1, "max": 100},
    "ema_slow_period": {"label": "Slow EMA Period", "default": 21, "type": "number", "min": 2, "max": 200}
}

def calculate_strategy_indicators(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    fast_period = params.get('ema_fast_period', STRATEGY_PARAMS_UI['ema_fast_period']['default'])
    slow_period = params.get('ema_slow_period', STRATEGY_PARAMS_UI['ema_slow_period']['default'])
    if 'close' not in df.columns: return df
    # Corrected: Call ta on DataFrame
    ema_fast_series = df.ta.ema(close=df['close'], length=fast_period, append=False)
    ema_slow_series = df.ta.ema(close=df['close'], length=slow_period, append=False)
    if ema_fast_series is not None: df[f'EMA_{fast_period}'] = ema_fast_series
    if ema_slow_series is not None: df[f'EMA_{slow_period}'] = ema_slow_series
    return df

def run_strategy(df: pd.DataFrame, params: Dict[str, Any], current_position_type: Optional[str] = None) -> Dict[str, Any]:
    # (Logic remains same as previously provided, ensure it uses correct column names)
    fast_period = params.get('ema_fast_period'); slow_period = params.get('ema_slow_period')
    ema_fast_col = f'EMA_{fast_period}'; ema_slow_col = f'EMA_{slow_period}'
    signal_output = {"signal": "HOLD", "details": "Conditions not met."}
    if not all(c in df.columns for c in [ema_fast_col,ema_slow_col]) or len(df)<2 or df[ema_fast_col].iloc[-2:].isna().any() or df[ema_slow_col].iloc[-2:].isna().any(): return {"signal":"HOLD", "details":"EMA data missing/incomplete."}
    latest_fast=df[ema_fast_col].iloc[-1];prev_fast=df[ema_fast_col].iloc[-2];latest_slow=df[ema_slow_col].iloc[-1];prev_slow=df[ema_slow_col].iloc[-2]
    if (prev_fast<=prev_slow)and(latest_fast>latest_slow): signal_output={"signal":"BUY","details":f"EMA({fast_period}) crossed ABOVE EMA({slow_period})."}
    elif (prev_fast>=prev_slow)and(latest_fast<latest_slow): signal_output={"signal":"SELL","details":f"EMA({fast_period}) crossed BELOW EMA({slow_period})."}
    elif latest_fast>latest_slow: signal_output["details"]=f"EMA({fast_period}) > EMA({slow_period}) (Long Bias)."
    elif latest_fast<latest_slow: signal_output["details"]=f"EMA({fast_period}) < EMA({slow_period}) (Short Bias)."
    return signal_output

def get_chart_overlay_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    # (Logic remains same, ensure it uses correct column names and returns ms timestamps)
    chart_data={};fast_period=params.get('ema_fast_period');slow_period=params.get('ema_slow_period')
    ema_fast_col=f'EMA_{fast_period}';ema_slow_col=f'EMA_{slow_period}'; df_chart=df.copy()
    if not isinstance(df_chart.index, pd.DatetimeIndex): # Ensure datetime index
        if 'timestamp' in df_chart.columns: df_chart = df_chart.set_index(pd.to_datetime(df_chart['timestamp'], unit='ms'))
        else: return {} # Cannot proceed without time reference
    if ema_fast_col in df_chart:chart_data['ema_fast']=[{"time":int(i.timestamp()*1000),"value":r[ema_fast_col]} for i,r in df_chart[[ema_fast_col]].dropna().iterrows()]
    if ema_slow_col in df_chart:chart_data['ema_slow']=[{"time":int(i.timestamp()*1000),"value":r[ema_slow_col]} for i,r in df_chart[[ema_slow_col]].dropna().iterrows()]
    return chart_data