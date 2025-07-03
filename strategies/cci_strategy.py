# strategies/cci_cyclical_strategy.py
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional

STRATEGY_NAME = "CCI Cyclical Trade"
STRATEGY_SLUG = "cci_cyclical"
STRATEGY_DESCRIPTION = "Signals when CCI crosses above a lower threshold (BUY) or below an upper threshold (SELL)."

# Parameters for the UI and for the strategy logic
STRATEGY_PARAMS_UI = {
    "cci_length": { # Matches 'sssr_cci_length'
        "label": "CCI Period", "default": 20, "type": "number", "min": 2, "max": 100
    },
    "cci_lower_threshold": { # Matches 'sssr_cci_lower_threshold'
        "label": "CCI Lower Threshold (e.g., -100)", "default": -100, "type": "number", "min": -300, "max": -1
    },
    "cci_upper_threshold": { # Matches 'sssr_cci_upper_threshold'
        "label": "CCI Upper Threshold (e.g., 100)", "default": 100, "type": "number", "min": 1, "max": 300
    }
}

def calculate_strategy_indicators(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """Calculates CCI and adds it to the DataFrame."""
    length = params.get('cci_length', STRATEGY_PARAMS_UI['cci_length']['default'])
    # The default constant pandas-ta.cci uses is 0.015
    fixed_constant_str = "0.015"
    cci_col_name_expected = f'CCI_{length}_{fixed_constant_str}'

    if not all(col in df.columns for col in ['high', 'low', 'close']):
        print(f"!!! {STRATEGY_NAME}: 'high', 'low', or 'close' columns missing.")
        # Return original df, run_strategy will then see missing column
        return df

    # Calculate CCI using pandas-ta
    # It's better to let pandas-ta name the column and then retrieve it if using append=True,
    # or if append=False, assign its result.
    try:
        # Calculate without appending first to get the Series
        cci_series = df.ta.cci(high=df['high'], low=df['low'], close=df['close'], length=length, append=False)
        if cci_series is not None and not cci_series.empty:
            # pandas-ta for CCI with default constant usually names it like CCI_Length_0.015
            # If it's just a series, its .name attribute might be this.
            # Forcing our expected name for consistency.
            df[cci_col_name_expected] = cci_series
        else:
            print(f"!!! {STRATEGY_NAME}: CCI calculation returned None or empty.")
    except Exception as e:
        print(f"!!! {STRATEGY_NAME}: Error during CCI calculation: {e}")
        # Ensure column doesn't exist or is all NaN if calc fails
        df[cci_col_name_expected] = pd.NA 
    
    return df

def run_strategy(df: pd.DataFrame, params: Dict[str, Any], current_position_type: Optional[str] = None) -> Dict[str, Any]:
    """Calculates a trading signal for the CCI Cyclical Trading strategy."""
    length = params.get('cci_length', STRATEGY_PARAMS_UI['cci_length']['default'])
    lower_threshold = params.get('cci_lower_threshold', STRATEGY_PARAMS_UI['cci_lower_threshold']['default'])
    upper_threshold = params.get('cci_upper_threshold', STRATEGY_PARAMS_UI['cci_upper_threshold']['default'])

    # Construct the expected CCI column name (pandas-ta default constant is 0.015)
    fixed_constant_str = "0.015" 
    cci_col_name = f'CCI_{length}_{fixed_constant_str}'
    
    signal_output = {"signal": "HOLD", "details": "Conditions not met or CCI neutral."}

    if cci_col_name not in df.columns:
        signal_output["details"] = f"CCI column '{cci_col_name}' missing."
        return signal_output
    if len(df) < 2:
        signal_output["details"] = "Not enough data points."
        return signal_output
        
    if df[cci_col_name].iloc[-2:].isna().any():
        signal_output["details"] = "CCI data incomplete (NaNs)."
        return signal_output

    latest_cci = df[cci_col_name].iloc[-1]
    previous_cci = df[cci_col_name].iloc[-2]

    # Parameter validation (already in original, good to keep)
    if not (lower_threshold < 0 < upper_threshold and lower_threshold < upper_threshold) :
        signal_output["details"] = "Invalid CCI thresholds configuration."
        return signal_output

    buy_condition_met = (previous_cci <= lower_threshold) and (latest_cci > lower_threshold)
    sell_condition_met = (previous_cci >= upper_threshold) and (latest_cci < upper_threshold)

    if current_position_type is None:
        if buy_condition_met:
            signal_output["signal"] = "BUY"
            signal_output["details"] = f"CCI ({latest_cci:.2f}) crossed ABOVE lower threshold ({lower_threshold})."
        elif sell_condition_met:
            signal_output["signal"] = "SELL"
            signal_output["details"] = f"CCI ({latest_cci:.2f}) crossed BELOW upper threshold ({upper_threshold})."
    elif current_position_type == "LONG":
        if sell_condition_met:
            signal_output["signal"] = "CLOSE_LONG"
            signal_output["details"] = f"CCI crossed BELOW upper threshold (exit long)."
    elif current_position_type == "SHORT":
        if buy_condition_met:
            signal_output["signal"] = "CLOSE_SHORT"
            signal_output["details"] = f"CCI crossed ABOVE lower threshold (exit short)."
            
    if signal_output["signal"] == "HOLD": # Context for hold
        if latest_cci < lower_threshold:
             signal_output["details"] = f"CCI ({latest_cci:.2f}) currently BELOW lower threshold ({lower_threshold})."
        elif latest_cci > upper_threshold:
             signal_output["details"] = f"CCI ({latest_cci:.2f}) currently ABOVE upper threshold ({upper_threshold})."
        else:
             signal_output["details"] = f"CCI ({latest_cci:.2f}) is between thresholds ({lower_threshold} and {upper_threshold})."

    return signal_output

def get_chart_overlay_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepares CCI data for plotting. CCI is typically a separate pane.
    For simplicity, we'll return it for the main chart as a line.
    """
    chart_data = {}
    length = params.get('cci_length', STRATEGY_PARAMS_UI['cci_length']['default'])
    fixed_constant_str = "0.015" # pandas-ta default constant for cci
    cci_col_name = f'CCI_{length}_{fixed_constant_str}'
    
    df_for_chart = df.copy()
    if not isinstance(df_for_chart.index, pd.DatetimeIndex): return {}

    if cci_col_name in df_for_chart.columns:
        series = df_for_chart[[cci_col_name]].dropna()
        chart_data['cci_line'] = [{"time": int(idx.timestamp()*1000), "value": row[cci_col_name]} for idx,row in series.iterrows()]
        
        # Optionally, add horizontal lines for thresholds if JS can handle it
        # lower_thresh_val = params.get('cci_lower_threshold')
        # upper_thresh_val = params.get('cci_upper_threshold')
        # if lower_thresh_val is not None:
        #     chart_data['cci_lower_thresh_line'] = [{"time": int(idx.timestamp()*1000), "value": lower_thresh_val} for idx,row in series.iterrows()]
        # if upper_thresh_val is not None:
        #     chart_data['cci_upper_thresh_line'] = [{"time": int(idx.timestamp()*1000), "value": upper_thresh_val} for idx,row in series.iterrows()]

    return chart_data