# strategies/supertrend_following.py
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional

STRATEGY_NAME = "Supertrend Following"
STRATEGY_SLUG = "supertrend_following"
STRATEGY_DESCRIPTION = "Signals based on Supertrend direction flips. BUY when trend flips to bullish, SELL when it flips to bearish."

STRATEGY_PARAMS_UI = {
    "supertrend_atr_length": { # Matches 'invo_supertrend_atr_length'
        "label": "Supertrend ATR Period", "default": 10, "type": "number", "min": 1, "max": 50
    },
    "supertrend_multiplier": { # Matches 'invo_supertrend_multiplier'
        "label": "Supertrend ATR Multiplier", "default": 3.0, "type": "number", "min": 0.1, "max": 10.0, "step": 0.1
    }
}

def calculate_strategy_indicators(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """Calculates Supertrend and adds its components to the DataFrame."""
    atr_length = params.get('supertrend_atr_length', STRATEGY_PARAMS_UI['supertrend_atr_length']['default'])
    multiplier = params.get('supertrend_multiplier', STRATEGY_PARAMS_UI['supertrend_multiplier']['default'])

    if not all(col in df.columns for col in ['high', 'low', 'close']):
        print(f"!!! {STRATEGY_NAME}: 'high', 'low', or 'close' columns missing.")
        return df

    # pandas-ta supertrend appends: SUPERT_length_multiplier, SUPERTd_length_multiplier (direction), SUPERTl, SUPERTs
    supertrend_output = df.ta.supertrend(
        high=df['high'], low=df['low'], close=df['close'],
        length=atr_length,
        multiplier=multiplier,
        append=False # Calculate separately to control names if needed
    )
    if supertrend_output is not None and not supertrend_output.empty:
        # Main line and direction are most important
        df[f'SUPERT_{atr_length}_{multiplier}'] = supertrend_output[f'SUPERT_{atr_length}_{multiplier}']
        df[f'SUPERTd_{atr_length}_{multiplier}'] = supertrend_output[f'SUPERTd_{atr_length}_{multiplier}'] # Direction: 1 for uptrend, -1 for downtrend
        # Optional: Long/Short stop lines if you want to plot them
        # df[f'SUPERTl_{atr_length}_{multiplier}'] = supertrend_output[f'SUPERTl_{atr_length}_{multiplier}'] # Long stop
        # df[f'SUPERTs_{atr_length}_{multiplier}'] = supertrend_output[f'SUPERTs_{atr_length}_{multiplier}'] # Short stop
    
    return df

def run_strategy(df: pd.DataFrame, params: Dict[str, Any], current_position_type: Optional[str] = None) -> Dict[str, Any]:
    """Calculates a trading signal for the Supertrend Following strategy."""
    atr_length = params.get('supertrend_atr_length', STRATEGY_PARAMS_UI['supertrend_atr_length']['default'])
    multiplier = params.get('supertrend_multiplier', STRATEGY_PARAMS_UI['supertrend_multiplier']['default'])

    # Construct column names based on how pandas_ta names them
    supertrend_val_col = f'SUPERT_{atr_length}_{multiplier}' # The actual Supertrend line value
    supertrend_dir_col = f'SUPERTd_{atr_length}_{multiplier}' # The direction (-1 or 1)
    
    signal_output = {"signal": "HOLD", "details": "Conditions not met or Supertrend neutral."}

    if not all(col in df.columns for col in [supertrend_dir_col, 'close']): # Value col not strictly needed for flip logic
        signal_output["details"] = "Required Supertrend direction or close columns missing."
        return signal_output
    if len(df) < 2: # Need at least current and previous direction
        signal_output["details"] = "Not enough data points for signal."
        return signal_output
        
    if df[supertrend_dir_col].iloc[-2:].isna().any(): # Check last two direction values
        signal_output["details"] = "Supertrend direction data incomplete (NaNs)."
        return signal_output

    latest_direction = df[supertrend_dir_col].iloc[-1]
    previous_direction = df[supertrend_dir_col].iloc[-2]
    latest_close = df['close'].iloc[-1] # For context in details

    buy_condition_met = (previous_direction == -1) and (latest_direction == 1) # Flipped from down to up
    sell_condition_met = (previous_direction == 1) and (latest_direction == -1) # Flipped from up to down

    if current_position_type is None:
        if buy_condition_met:
            signal_output["signal"] = "BUY"
            signal_output["details"] = f"Supertrend flipped to BULLISH (direction: {latest_direction:.0f})."
        elif sell_condition_met:
            signal_output["signal"] = "SELL"
            signal_output["details"] = f"Supertrend flipped to BEARISH (direction: {latest_direction:.0f})."
    elif current_position_type == "LONG":
        if sell_condition_met:
            signal_output["signal"] = "CLOSE_LONG"
            signal_output["details"] = f"Supertrend flipped to BEARISH (exit long)."
    elif current_position_type == "SHORT":
        if buy_condition_met:
            signal_output["signal"] = "CLOSE_SHORT"
            signal_output["details"] = f"Supertrend flipped to BULLISH (exit short)."
            
    if signal_output["signal"] == "HOLD": # Context
        if latest_direction == 1: signal_output["details"] = f"Supertrend currently BULLISH (direction {latest_direction:.0f}). Price: {latest_close:.2f}."
        elif latest_direction == -1: signal_output["details"] = f"Supertrend currently BEARISH (direction {latest_direction:.0f}). Price: {latest_close:.2f}."
        else: signal_output["details"] = "Supertrend direction unclear."


    return signal_output

def get_chart_overlay_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Prepares Supertrend line data for plotting."""
    chart_data = {}
    atr_length = params.get('supertrend_atr_length', STRATEGY_PARAMS_UI['supertrend_atr_length']['default'])
    multiplier = params.get('supertrend_multiplier', STRATEGY_PARAMS_UI['supertrend_multiplier']['default'])

    supertrend_val_col = f'SUPERT_{atr_length}_{multiplier}' # The main Supertrend line
    
    df_for_chart = df.copy()
    if not isinstance(df_for_chart.index, pd.DatetimeIndex): return {}

    if supertrend_val_col in df_for_chart.columns:
        series = df_for_chart[[supertrend_val_col]].dropna()
        chart_data['supertrend_line'] = [{"time": int(idx.timestamp()*1000), "value": row[supertrend_val_col]} for idx,row in series.iterrows()]
        
    return chart_data