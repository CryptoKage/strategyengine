# strategies/vwap_cross_strategy.py
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional

STRATEGY_NAME = "VWAP Cross"
STRATEGY_SLUG = "vwap_cross"
STRATEGY_DESCRIPTION = "Signals when price crosses above (BUY) or below (SELL) the rolling VWAP."

STRATEGY_PARAMS_UI = {
    "vwap_length": { # Matches 'oracle_vwap_length'
        "label": "VWAP Period (Rolling)", "default": 20, "type": "number", "min": 1, "max": 200
    }
    # Note: True intraday VWAP often resets daily. pandas-ta's 'vwap' with a length
    # calculates a rolling VWAP. If a daily reset is needed, the logic becomes more complex
    # (e.g., grouping by day or using an anchor 'A' if pandas-ta supports it easily for rolling context).
    # For simplicity, this uses rolling VWAP.
}

def calculate_strategy_indicators(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """Calculates rolling VWAP and adds it to the DataFrame."""
    length = params.get('vwap_length', STRATEGY_PARAMS_UI['vwap_length']['default'])

    if not all(col in df.columns for col in ['high', 'low', 'close', 'volume']):
        print(f"!!! {STRATEGY_NAME}: HLCV columns missing.")
        return df

    # pandas-ta vwap appends VWAP_length
    vwap_output = df.ta.vwap(
        high=df['high'], low=df['low'], close=df['close'], volume=df['volume'],
        length=length, # For rolling VWAP
        append=False 
    )
    if vwap_output is not None and not vwap_output.empty:
        df[f'VWAP_{length}'] = vwap_output
    
    return df

def run_strategy(df: pd.DataFrame, params: Dict[str, Any], current_position_type: Optional[str] = None) -> Dict[str, Any]:
    """Calculates a trading signal based on price crossing a rolling VWAP."""
    length = params.get('vwap_length', STRATEGY_PARAMS_UI['vwap_length']['default'])
    vwap_col_name = f'VWAP_{length}'
    signal_output = {"signal": "HOLD", "details": "Conditions not met or price neutral vs VWAP."}

    if not all(col in df.columns for col in [vwap_col_name, 'close']):
        signal_output["details"] = "Required VWAP/close columns missing."
        return signal_output
    if len(df) < 2:
        signal_output["details"] = "Not enough data points."
        return signal_output
        
    if df[vwap_col_name].iloc[-2:].isna().any() or df['close'].iloc[-2:].isna().any():
        signal_output["details"] = "VWAP/close data incomplete (NaNs)."
        return signal_output

    latest_close = df['close'].iloc[-1]
    previous_close = df['close'].iloc[-2]
    latest_vwap = df[vwap_col_name].iloc[-1]
    previous_vwap = df[vwap_col_name].iloc[-2]

    bullish_cross_occurred = (previous_close <= previous_vwap) and (latest_close > latest_vwap)
    bearish_cross_occurred = (previous_close >= previous_vwap) and (latest_close < latest_vwap)

    if current_position_type is None:
        if bullish_cross_occurred:
            signal_output["signal"] = "BUY"
            signal_output["details"] = f"Price ({latest_close:.2f}) crossed ABOVE VWAP ({latest_vwap:.2f})."
        elif bearish_cross_occurred:
            signal_output["signal"] = "SELL"
            signal_output["details"] = f"Price ({latest_close:.2f}) crossed BELOW VWAP ({latest_vwap:.2f})."
    elif current_position_type == "LONG":
        if bearish_cross_occurred:
            signal_output["signal"] = "CLOSE_LONG"
            signal_output["details"] = f"Price crossed BELOW VWAP (exit long)."
    elif current_position_type == "SHORT":
        if bullish_cross_occurred:
            signal_output["signal"] = "CLOSE_SHORT"
            signal_output["details"] = f"Price crossed ABOVE VWAP (exit short)."
            
    if signal_output["signal"] == "HOLD": # Context
        if latest_close > latest_vwap: signal_output["details"] = f"Price ({latest_close:.2f}) currently ABOVE VWAP ({latest_vwap:.2f})."
        elif latest_close < latest_vwap: signal_output["details"] = f"Price ({latest_close:.2f}) currently BELOW VWAP ({latest_vwap:.2f})."
        else: signal_output["details"] = f"Price ({latest_close:.2f}) at VWAP ({latest_vwap:.2f})."

    return signal_output

def get_chart_overlay_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Prepares VWAP line data for plotting."""
    chart_data = {}
    length = params.get('vwap_length', STRATEGY_PARAMS_UI['vwap_length']['default'])
    vwap_col_name = f'VWAP_{length}'
    
    df_for_chart = df.copy()
    if not isinstance(df_for_chart.index, pd.DatetimeIndex): return {}

    if vwap_col_name in df_for_chart.columns:
        series = df_for_chart[[vwap_col_name]].dropna()
        chart_data['vwap_line'] = [{"time": int(idx.timestamp()*1000), "value": row[vwap_col_name]} for idx,row in series.iterrows()]
        
    return chart_data