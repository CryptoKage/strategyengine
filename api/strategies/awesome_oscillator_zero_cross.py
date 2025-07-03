# strategies/awesome_oscillator_zero_cross_strategy.py
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional

STRATEGY_NAME = "Awesome Oscillator Zero Cross"
STRATEGY_SLUG = "ao_zero_cross"
STRATEGY_DESCRIPTION = "Generates signals when the Awesome Oscillator (AO) crosses the zero line."

STRATEGY_PARAMS_UI = {
    "ao_fast_length": { # Original: tg_ao_fast_length
        "label": "AO Fast Length", "default": 5, "type": "number", "min": 1, "max": 50
    },
    "ao_slow_length": { # Original: tg_ao_slow_length
        "label": "AO Slow Length", "default": 34, "type": "number", "min": 2, "max": 100
    }
}

def calculate_strategy_indicators(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """Calculates Awesome Oscillator and adds it to the DataFrame."""
    fast_length = params.get('ao_fast_length', STRATEGY_PARAMS_UI['ao_fast_length']['default'])
    slow_length = params.get('ao_slow_length', STRATEGY_PARAMS_UI['ao_slow_length']['default'])

    if not all(col in df.columns for col in ['high', 'low']):
        print(f"!!! {STRATEGY_NAME}: 'high' or 'low' columns missing.")
        return df # Return original df if essential columns are missing

    # pandas-ta ao appends AO_fast_slow
    ao_output = df.ta.ao(
        high=df['high'], low=df['low'],
        fast=fast_length, slow=slow_length,
        append=False # Calculate separately
    )
    if ao_output is not None and not ao_output.empty:
         # The series returned by ta.ao() is the AO itself. pandas-ta might name it AO_fast_slow by default.
         # For consistency if ta.ao changes its default name for a Series, we explicitly name it.
         df[f'AO_{fast_length}_{slow_length}'] = ao_output
    else:
        print(f"!!! {STRATEGY_NAME}: AO calculation failed or returned empty.")
        # Ensure column exists with NaNs if calculation failed to prevent KeyErrors later
        df[f'AO_{fast_length}_{slow_length}'] = pd.NA
    
    return df

def run_strategy(df: pd.DataFrame, params: Dict[str, Any], current_position_type: Optional[str] = None) -> Dict[str, Any]:
    """Calculates a trading signal for the AO Zero-Line Cross strategy."""
    fast_length = params.get('ao_fast_length', STRATEGY_PARAMS_UI['ao_fast_length']['default'])
    slow_length = params.get('ao_slow_length', STRATEGY_PARAMS_UI['ao_slow_length']['default'])
    
    ao_col_name = f'AO_{fast_length}_{slow_length}'
    signal_output = {"signal": "HOLD", "details": "Conditions not met or AO indicates hold."}

    if ao_col_name not in df.columns:
        signal_output["details"] = "AO column missing (calculation might have failed)."
        return signal_output
    if len(df) < 2: # Need current and previous for crossover
        signal_output["details"] = "Not enough data points for signal."
        return signal_output
        
    if df[ao_col_name].iloc[-2:].isna().any():
        signal_output["details"] = "AO data incomplete (NaNs) for recent periods."
        return signal_output

    latest_ao = df[ao_col_name].iloc[-1]
    previous_ao = df[ao_col_name].iloc[-2]

    buy_zero_cross_occurred = (previous_ao <= 0) and (latest_ao > 0)
    sell_zero_cross_occurred = (previous_ao >= 0) and (latest_ao < 0)

    # Using logic from your provided file
    if current_position_type is None:
        if buy_zero_cross_occurred:
            signal_output["signal"] = "BUY"
            signal_output["details"] = f"AO ({latest_ao:.2f}) crossed ABOVE zero."
        elif sell_zero_cross_occurred:
            signal_output["signal"] = "SELL"
            signal_output["details"] = f"AO ({latest_ao:.2f}) crossed BELOW zero."
    elif current_position_type == "LONG":
        if sell_zero_cross_occurred:
            signal_output["signal"] = "CLOSE_LONG"
            signal_output["details"] = f"AO ({latest_ao:.2f}) crossed BELOW zero (exit long)."
    elif current_position_type == "SHORT":
        if buy_zero_cross_occurred:
            signal_output["signal"] = "CLOSE_SHORT"
            signal_output["details"] = f"AO ({latest_ao:.2f}) crossed ABOVE zero (exit short)."
            
    if signal_output["signal"] == "HOLD": # Provide context if holding
        if latest_ao > 0 :
            signal_output["details"] = f"AO ({latest_ao:.2f}) is currently POSITIVE (Bullish momentum)."
        elif latest_ao < 0:
             signal_output["details"] = f"AO ({latest_ao:.2f}) is currently NEGATIVE (Bearish momentum)."
        else:
            signal_output["details"] = f"AO ({latest_ao:.2f}) is at ZERO."

    return signal_output

def get_chart_overlay_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Prepares AO data for plotting."""
    chart_data = {}
    fast_length = params.get('ao_fast_length', STRATEGY_PARAMS_UI['ao_fast_length']['default'])
    slow_length = params.get('ao_slow_length', STRATEGY_PARAMS_UI['ao_slow_length']['default'])
    ao_col_name = f'AO_{fast_length}_{slow_length}'
    
    df_for_chart = df.copy()
    # Ensure index is DatetimeIndex (should be set by main API before calling this)
    if not isinstance(df_for_chart.index, pd.DatetimeIndex): 
        if 'timestamp' in df_for_chart.columns: # Try to set it if 'timestamp' (ms) exists
            df_for_chart = df_for_chart.set_index(pd.to_datetime(df_for_chart['timestamp'], unit='ms'))
        else: return {} # Cannot create chart data without proper time index

    if ao_col_name in df_for_chart.columns:
        series = df_for_chart[[ao_col_name]].dropna()
        # AO is often a histogram, but we'll send line data. JS can style it.
        chart_data['ao_line'] = [{"time": int(idx.timestamp()*1000), "value": row[ao_col_name]} for idx,row in series.iterrows()]
        
    return chart_data