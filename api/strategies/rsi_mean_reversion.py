# strategies/rsi_mean_reversion_strategy.py
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional

STRATEGY_NAME = "RSI Mean Reversion"
STRATEGY_SLUG = "rsi_mean_reversion"
STRATEGY_DESCRIPTION = "Buys when RSI crosses up from oversold, sells when RSI crosses down from overbought."
STRATEGY_PARAMS_UI = {
    "rsi_length": {"label": "RSI Period", "default": 14, "type": "number", "min": 2, "max": 50},
    "rsi_oversold_level": {"label": "RSI Oversold", "default": 30, "type": "number", "min": 1, "max": 49},
    "rsi_overbought_level": {"label": "RSI Overbought", "default": 70, "type": "number", "min": 51, "max": 99}
}

def calculate_strategy_indicators(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    length = params.get('rsi_length', STRATEGY_PARAMS_UI['rsi_length']['default'])
    if 'close' not in df.columns: return df
    # Corrected: Call ta on DataFrame
    rsi_series = df.ta.rsi(close=df['close'], length=length, append=False)
    if rsi_series is not None: df[f'RSI_{length}'] = rsi_series
    return df

def run_strategy(df: pd.DataFrame, params: Dict[str, Any], current_position_type: Optional[str] = None) -> Dict[str, Any]:
    # (Logic remains same, ensure it uses correct rsi_col_name)
    length=params.get('rsi_length');oversold=params.get('rsi_oversold_level');overbought=params.get('rsi_overbought_level')
    rsi_col=f'RSI_{length}'; signal_output={"signal":"HOLD", "details":"RSI neutral."}
    if rsi_col not in df.columns or len(df)<2 or df[rsi_col].iloc[-2:].isna().any(): return {"signal":"HOLD", "details":"RSI data missing/incomplete."}
    latest_rsi=df[rsi_col].iloc[-1];previous_rsi=df[rsi_col].iloc[-2]
    buy_met=(previous_rsi<=oversold)and(latest_rsi>oversold);sell_met=(previous_rsi>=overbought)and(latest_rsi<overbought)
    if buy_met: signal_output={"signal":"BUY","details":f"RSI ({latest_rsi:.2f}) crossed ABOVE oversold ({oversold})."}
    elif sell_met: signal_output={"signal":"SELL","details":f"RSI ({latest_rsi:.2f}) crossed BELOW overbought ({overbought})."}
    # ... (add CLOSE_LONG/SHORT logic if needed based on current_position_type) ...
    elif latest_rsi < oversold: signal_output["details"] = f"RSI OVERSOLD ({latest_rsi:.2f} < {oversold})."
    elif latest_rsi > overbought: signal_output["details"] = f"RSI OVERBOUGHT ({latest_rsi:.2f} > {overbought})."
    return signal_output

def get_chart_overlay_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    # (Logic remains same, ensure it returns ms timestamps)
    chart_data={};length=params.get('rsi_length');rsi_col=f'RSI_{length}';df_chart=df.copy()
    if not isinstance(df_chart.index, pd.DatetimeIndex):
        if 'timestamp' in df_chart.columns: df_chart = df_chart.set_index(pd.to_datetime(df_chart['timestamp'], unit='ms'))
        else: return {}
    if rsi_col in df_chart:chart_data['rsi_line']=[{"time":int(i.timestamp()*1000),"value":r[rsi_col]} for i,r in df_chart[[rsi_col]].dropna().iterrows()]
    return chart_data