# strategies/macd_trend_strategy.py
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional

STRATEGY_NAME = "MACD Trend (Crossover)"
STRATEGY_SLUG = "macd_trend_crossover"
STRATEGY_DESCRIPTION = "Signals on MACD line crossing its signal line."
STRATEGY_PARAMS_UI = {
    "macd_fast_period": {"label": "MACD Fast EMA", "default": 12, "type": "number", "min": 1, "max": 50},
    "macd_slow_period": {"label": "MACD Slow EMA", "default": 26, "type": "number", "min": 2, "max": 100},
    "macd_signal_period": {"label": "MACD Signal EMA", "default": 9, "type": "number", "min": 1, "max": 50}
}

def calculate_strategy_indicators(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    fast=params.get('macd_fast_period'); slow=params.get('macd_slow_period'); signal=params.get('macd_signal_period')
    if 'close' not in df.columns: return df
    # Corrected: Call ta on DataFrame
    macd_output = df.ta.macd(close=df['close'], fast=fast, slow=slow, signal=signal, append=False)
    if macd_output is not None and not macd_output.empty:
        df[f'MACD_{fast}_{slow}_{signal}'] = macd_output[f'MACD_{fast}_{slow}_{signal}']
        df[f'MACDh_{fast}_{slow}_{signal}'] = macd_output[f'MACDh_{fast}_{slow}_{signal}']
        df[f'MACDs_{fast}_{slow}_{signal}'] = macd_output[f'MACDs_{fast}_{slow}_{signal}']
    return df

def run_strategy(df: pd.DataFrame, params: Dict[str, Any], current_position_type: Optional[str] = None) -> Dict[str, Any]:
    # (Logic remains same, ensure it uses correct column names)
    fast=params.get('macd_fast_period');slow=params.get('macd_slow_period');signal_p=params.get('macd_signal_period')
    macd_col=f'MACD_{fast}_{slow}_{signal_p}';sig_col=f'MACDs_{fast}_{slow}_{signal_p}';signal_output={"signal":"HOLD", "details":"MACD neutral."}
    if not all(c in df.columns for c in [macd_col,sig_col]) or len(df)<2 or df[macd_col].iloc[-2:].isna().any() or df[sig_col].iloc[-2:].isna().any(): return {"signal":"HOLD", "details":"MACD data missing/incomplete."}
    latest_macd=df[macd_col].iloc[-1];prev_macd=df[macd_col].iloc[-2];latest_sig=df[sig_col].iloc[-1];prev_sig=df[sig_col].iloc[-2]
    bull_cross=(prev_macd<=prev_sig)and(latest_macd>latest_sig);bear_cross=(prev_macd>=prev_sig)and(latest_macd<latest_sig)
    if bull_cross: signal_output={"signal":"BUY","details":f"MACD ({latest_macd:.2f}) crossed ABOVE Signal ({latest_sig:.2f})."}
    elif bear_cross: signal_output={"signal":"SELL","details":f"MACD ({latest_macd:.2f}) crossed BELOW Signal ({latest_sig:.2f})."}
    # ... (add CLOSE_LONG/SHORT logic if needed) ...
    elif latest_macd > latest_sig: signal_output["details"] = f"MACD ({latest_macd:.2f}) > Signal ({latest_sig:.2f}) (Bullish Momentum)."
    elif latest_macd < latest_sig: signal_output["details"] = f"MACD ({latest_macd:.2f}) < Signal ({latest_sig:.2f}) (Bearish Momentum)."
    return signal_output

def get_chart_overlay_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    # (Logic remains same, ensure it uses correct column names and returns ms timestamps)
    chart_data={};fast=params.get('macd_fast_period');slow=params.get('macd_slow_period');signal_p=params.get('macd_signal_period')
    macd_col=f'MACD_{fast}_{slow}_{signal_p}';sig_col=f'MACDs_{fast}_{slow}_{signal_p}';hist_col=f'MACDh_{fast}_{slow}_{signal_p}';df_chart=df.copy()
    if not isinstance(df_chart.index, pd.DatetimeIndex):
        if 'timestamp' in df_chart.columns: df_chart = df_chart.set_index(pd.to_datetime(df_chart['timestamp'], unit='ms'))
        else: return {}
    if macd_col in df_chart:chart_data['macd_line']=[{"time":int(i.timestamp()*1000),"value":r[macd_col]} for i,r in df_chart[[macd_col]].dropna().iterrows()]
    if sig_col in df_chart:chart_data['macd_signal_line']=[{"time":int(i.timestamp()*1000),"value":r[sig_col]} for i,r in df_chart[[sig_col]].dropna().iterrows()]
    if hist_col in df_chart:chart_data['macd_histogram']=[{"time":int(i.timestamp()*1000),"value":r[hist_col]} for i,r in df_chart[[hist_col]].dropna().iterrows()]
    return chart_data