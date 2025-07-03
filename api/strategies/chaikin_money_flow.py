# strategies/chaikin_money_flow_threshold.py
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional

STRATEGY_NAME = "Chaikin Money Flow (CMF) Threshold"
STRATEGY_SLUG = "cmf_threshold"
STRATEGY_DESCRIPTION = "Signals when CMF crosses above a positive threshold (BUY) or below a negative threshold (SELL)."

STRATEGY_PARAMS_UI = {
    "cmf_length": { # Matches 'visor_cmf_length'
        "label": "CMF Period", "default": 20, "type": "number", "min": 2, "max": 100
    },
    "cmf_entry_threshold": { # Matches 'visor_cmf_entry_threshold'
        "label": "CMF Entry Threshold (Absolute)", "default": 0.05, "type": "number", "min": 0.01, "max": 0.5, "step": 0.01
    }
}

def calculate_strategy_indicators(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """Calculates Chaikin Money Flow and adds it to the DataFrame."""
    length = params.get('cmf_length', STRATEGY_PARAMS_UI['cmf_length']['default'])

    if not all(col in df.columns for col in ['high', 'low', 'close', 'volume']):
        print(f"!!! {STRATEGY_NAME}: Required HLCV columns missing.")
        return df

    # pandas-ta cmf appends CMF_length
    cmf_output = df.ta.cmf(
        high=df['high'], low=df['low'], close=df['close'], volume=df['volume'],
        length=length,
        append=False # Calculate separately
    )
    if cmf_output is not None and not cmf_output.empty:
        df[f'CMF_{length}'] = cmf_output # cmf_output is already the series for CMF
    
    return df

def run_strategy(df: pd.DataFrame, params: Dict[str, Any], current_position_type: Optional[str] = None) -> Dict[str, Any]:
    """Calculates a trading signal for the CMF Threshold strategy."""
    length = params.get('cmf_length', STRATEGY_PARAMS_UI['cmf_length']['default'])
    threshold = params.get('cmf_entry_threshold', STRATEGY_PARAMS_UI['cmf_entry_threshold']['default'])

    cmf_col_name = f'CMF_{length}'
    signal_output = {"signal": "HOLD", "details": "Conditions not met or CMF neutral."}

    if cmf_col_name not in df.columns:
        signal_output["details"] = "CMF column missing."
        return signal_output
    if len(df) < 2:
        signal_output["details"] = "Not enough data points."
        return signal_output
        
    if df[cmf_col_name].iloc[-2:].isna().any():
        signal_output["details"] = "CMF data incomplete (NaNs)."
        return signal_output

    latest_cmf = df[cmf_col_name].iloc[-1]
    previous_cmf = df[cmf_col_name].iloc[-2]

    # Parameter validation
    if not (threshold > 0):
        signal_output["details"] = "CMF threshold must be a positive value."
        return signal_output

    buy_threshold_cross_occurred = (previous_cmf <= threshold) and (latest_cmf > threshold)
    sell_threshold_cross_occurred = (previous_cmf >= -threshold) and (latest_cmf < -threshold)

    if current_position_type is None:
        if buy_threshold_cross_occurred:
            signal_output["signal"] = "BUY"
            signal_output["details"] = f"CMF ({latest_cmf:.4f}) crossed ABOVE threshold ({threshold:.2f})."
        elif sell_threshold_cross_occurred:
            signal_output["signal"] = "SELL"
            signal_output["details"] = f"CMF ({latest_cmf:.4f}) crossed BELOW negative threshold (-{threshold:.2f})."
    elif current_position_type == "LONG":
        if sell_threshold_cross_occurred:
            signal_output["signal"] = "CLOSE_LONG"
            signal_output["details"] = f"CMF crossed BELOW negative threshold (exit long)."
    elif current_position_type == "SHORT":
        if buy_threshold_cross_occurred:
            signal_output["signal"] = "CLOSE_SHORT"
            signal_output["details"] = f"CMF crossed ABOVE positive threshold (exit short)."
            
    if signal_output["signal"] == "HOLD":
        if latest_cmf > threshold: signal_output["details"] = f"CMF ({latest_cmf:.4f}) currently bullish (above {threshold:.2f})."
        elif latest_cmf < -threshold: signal_output["details"] = f"CMF ({latest_cmf:.4f}) currently bearish (below -{threshold:.2f})."
        else: signal_output["details"] = f"CMF ({latest_cmf:.4f}) is neutral (between +/-{threshold:.2f})."

    return signal_output

def get_chart_overlay_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Prepares CMF data for plotting."""
    chart_data = {}
    length = params.get('cmf_length', STRATEGY_PARAMS_UI['cmf_length']['default'])
    cmf_col_name = f'CMF_{length}'
    
    df_for_chart = df.copy()
    if not isinstance(df_for_chart.index, pd.DatetimeIndex): return {}

    if cmf_col_name in df_for_chart.columns:
        series = df_for_chart[[cmf_col_name]].dropna()
        chart_data['cmf_line'] = [{"time": int(idx.timestamp()*1000), "value": row[cmf_col_name]} for idx,row in series.iterrows()]
        
    return chart_data