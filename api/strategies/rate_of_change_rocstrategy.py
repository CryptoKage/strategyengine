# strategies/rate_of_change_threshold_strategy.py
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional

STRATEGY_NAME = "Rate of Change (ROC) Threshold Breakout"
STRATEGY_SLUG = "roc_threshold_breakout"
STRATEGY_DESCRIPTION = "Signals when ROC crosses above a positive threshold (BUY) or below a negative threshold (SELL)."

STRATEGY_PARAMS_UI = {
    "roc_length": { # Matches 'goblin_roc_length'
        "label": "ROC Period", "default": 12, "type": "number", "min": 1, "max": 100
    },
    "roc_threshold_percent": { # Matches 'goblin_roc_threshold'
        "label": "ROC Threshold (%)", "default": 0.5, "type": "number", "min": 0.01, "max": 10.0, "step": 0.01
    }
}

def calculate_strategy_indicators(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """Calculates Rate of Change (ROC) and adds it to the DataFrame."""
    length = params.get('roc_length', STRATEGY_PARAMS_UI['roc_length']['default'])

    if 'close' not in df.columns:
        print(f"!!! {STRATEGY_NAME}: 'close' column missing.")
        return df

    # pandas-ta roc appends ROC_length
    roc_series = df.ta.roc(length=length, close=df['close'], append=False)
    if roc_series is not None:
        df[f'ROC_{length}'] = roc_series
    else:
        df[f'ROC_{length}'] = pd.NA
    
    return df

def run_strategy(df: pd.DataFrame, params: Dict[str, Any], current_position_type: Optional[str] = None) -> Dict[str, Any]:
    """Calculates a trading signal for the ROC Threshold Breakout strategy."""
    length = params.get('roc_length', STRATEGY_PARAMS_UI['roc_length']['default'])
    threshold_percent = params.get('roc_threshold_percent', STRATEGY_PARAMS_UI['roc_threshold_percent']['default'])

    roc_col_name = f'ROC_{length}'
    signal_output = {"signal": "HOLD", "details": "Conditions not met or ROC neutral."}

    if roc_col_name not in df.columns:
        signal_output["details"] = "ROC column missing."
        return signal_output
    if len(df) < 1: # Only need latest ROC value
        signal_output["details"] = "Not enough data points."
        return signal_output
        
    # Check last value for NA. ROC can be NaN if length > available data.
    if pd.isna(df[roc_col_name].iloc[-1]):
        signal_output["details"] = "ROC data incomplete (NaNs) for latest period."
        return signal_output

    latest_roc = df[roc_col_name].iloc[-1]

    # Parameter validation (already in original, good to keep)
    if not (threshold_percent > 0):
        signal_output["details"] = "ROC threshold must be a positive percentage."
        return signal_output

    buy_condition_met = latest_roc > threshold_percent
    sell_condition_met = latest_roc < -threshold_percent # Note: uses negative of the threshold

    # Using logic from your provided file
    if current_position_type is None:
        if buy_condition_met:
            signal_output["signal"] = "BUY"
            signal_output["details"] = f"ROC ({latest_roc:.2f}%) broke ABOVE threshold ({threshold_percent:.2f}%)."
        elif sell_condition_met:
            signal_output["signal"] = "SELL"
            signal_output["details"] = f"ROC ({latest_roc:.2f}%) broke BELOW negative threshold (-{threshold_percent:.2f}%)."
    elif current_position_type == "LONG":
        if sell_condition_met:
            signal_output["signal"] = "CLOSE_LONG"
            signal_output["details"] = "ROC broke BELOW negative threshold (exit long)."
    elif current_position_type == "SHORT":
        if buy_condition_met:
            signal_output["signal"] = "CLOSE_SHORT"
            signal_output["details"] = "ROC broke ABOVE positive threshold (exit short)."
            
    if signal_output["signal"] == "HOLD": # Context
        if latest_roc > threshold_percent: signal_output["details"] = f"ROC ({latest_roc:.2f}%) is strong positive."
        elif latest_roc < -threshold_percent: signal_output["details"] = f"ROC ({latest_roc:.2f}%) is strong negative."
        else: signal_output["details"] = f"ROC ({latest_roc:.2f}%) is between +/-{threshold_percent:.2f}%."

    return signal_output

def get_chart_overlay_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Prepares ROC data for plotting. Often a separate pane."""
    chart_data = {}
    length = params.get('roc_length', STRATEGY_PARAMS_UI['roc_length']['default'])
    roc_col_name = f'ROC_{length}'
    
    df_for_chart = df.copy()
    if not isinstance(df_for_chart.index, pd.DatetimeIndex):
        if 'timestamp' in df_for_chart.columns: df_for_chart = df_for_chart.set_index(pd.to_datetime(df_for_chart['timestamp'], unit='ms'))
        else: return {}

    if roc_col_name in df_for_chart.columns:
        series = df_for_chart[[roc_col_name]].dropna()
        chart_data['roc_line'] = [{"time": int(idx.timestamp()*1000), "value": row[roc_col_name]} for idx,row in series.iterrows()]
        
    return chart_data