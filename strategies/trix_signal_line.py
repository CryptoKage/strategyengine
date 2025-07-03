# strategies/trix_signal_cross_strategy.py
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional

STRATEGY_NAME = "TRIX Signal Line Crossover"
STRATEGY_SLUG = "trix_signal_cross"
STRATEGY_DESCRIPTION = "Signals on TRIX line crossing above (BUY) or below (SELL) its signal line."

STRATEGY_PARAMS_UI = {
    "trix_length": { # Matches 'fox_trix_length'
        "label": "TRIX EMA Period", "default": 14, "type": "number", "min": 1, "max": 50
    },
    "trix_signal_length": { # Matches 'fox_trix_signal_length'
        "label": "TRIX Signal Line EMA", "default": 9, "type": "number", "min": 1, "max": 50
    }
}

def calculate_strategy_indicators(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """Calculates TRIX and its signal line and adds them to the DataFrame."""
    trix_length = params.get('trix_length', STRATEGY_PARAMS_UI['trix_length']['default'])
    signal_length = params.get('trix_signal_length', STRATEGY_PARAMS_UI['trix_signal_length']['default'])

    if 'close' not in df.columns:
        print(f"!!! {STRATEGY_NAME}: 'close' column missing.")
        return df

    # pandas-ta trix appends: TRIX_length_signal, TRIXs_length_signal, TRIXh_length_signal
    trix_output = df.ta.trix(
        close=df['close'],
        length=trix_length,
        signal=signal_length,
        append=False # Calculate separately
    )
    if trix_output is not None and not trix_output.empty:
        df[f'TRIX_{trix_length}_{signal_length}'] = trix_output[f'TRIX_{trix_length}_{signal_length}']
        df[f'TRIXs_{trix_length}_{signal_length}'] = trix_output[f'TRIXs_{trix_length}_{signal_length}'] # Signal Line
        # df[f'TRIXh_{trix_length}_{signal_length}'] = trix_output[f'TRIXh_{trix_length}_{signal_length}'] # Histogram (optional)
    
    return df

def run_strategy(df: pd.DataFrame, params: Dict[str, Any], current_position_type: Optional[str] = None) -> Dict[str, Any]:
    """Calculates a trading signal for the TRIX Signal Line Crossover strategy."""
    trix_length = params.get('trix_length', STRATEGY_PARAMS_UI['trix_length']['default'])
    signal_length = params.get('trix_signal_length', STRATEGY_PARAMS_UI['trix_signal_length']['default'])

    trix_line_col = f'TRIX_{trix_length}_{signal_length}'
    signal_line_col = f'TRIXs_{trix_length}_{signal_length}'
    
    signal_output = {"signal": "HOLD", "details": "Conditions not met or TRIX neutral."}

    if not all(col in df.columns for col in [trix_line_col, signal_line_col]):
        signal_output["details"] = "Required TRIX/Signal columns missing."
        return signal_output
    if len(df) < 2:
        signal_output["details"] = "Not enough data points."
        return signal_output
        
    if df[trix_line_col].iloc[-2:].isna().any() or df[signal_line_col].iloc[-2:].isna().any():
        signal_output["details"] = "TRIX/Signal data incomplete (NaNs)."
        return signal_output

    latest_trix_line = df[trix_line_col].iloc[-1]
    previous_trix_line = df[trix_line_col].iloc[-2]
    latest_signal_line = df[signal_line_col].iloc[-1]
    previous_signal_line = df[signal_line_col].iloc[-2]

    bullish_cross_occurred = (previous_trix_line <= previous_signal_line) and (latest_trix_line > latest_signal_line)
    bearish_cross_occurred = (previous_trix_line >= previous_signal_line) and (latest_trix_line < latest_signal_line)

    if current_position_type is None:
        if bullish_cross_occurred:
            signal_output["signal"] = "BUY"
            signal_output["details"] = f"TRIX ({latest_trix_line:.4f}) crossed ABOVE Signal ({latest_signal_line:.4f})."
        elif bearish_cross_occurred:
            signal_output["signal"] = "SELL"
            signal_output["details"] = f"TRIX ({latest_trix_line:.4f}) crossed BELOW Signal ({latest_signal_line:.4f})."
    elif current_position_type == "LONG":
        if bearish_cross_occurred:
            signal_output["signal"] = "CLOSE_LONG"
            signal_output["details"] = f"TRIX crossed BELOW Signal (exit long)."
    elif current_position_type == "SHORT":
        if bullish_cross_occurred:
            signal_output["signal"] = "CLOSE_SHORT"
            signal_output["details"] = f"TRIX crossed ABOVE Signal (exit short)."
            
    if signal_output["signal"] == "HOLD": # Context
        if latest_trix_line > latest_signal_line:
            signal_output["details"] = f"TRIX ({latest_trix_line:.4f}) currently ABOVE Signal ({latest_signal_line:.4f}) (Bullish momentum)."
        elif latest_trix_line < latest_signal_line:
            signal_output["details"] = f"TRIX ({latest_trix_line:.4f}) currently BELOW Signal ({latest_signal_line:.4f}) (Bearish momentum)."
        else:
            signal_output["details"] = f"TRIX ({latest_trix_line:.4f}) is EQUAL to Signal ({latest_signal_line:.4f})."

    return signal_output

def get_chart_overlay_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Prepares TRIX and Signal Line data for plotting."""
    chart_data = {}
    trix_length = params.get('trix_length', STRATEGY_PARAMS_UI['trix_length']['default'])
    signal_length = params.get('trix_signal_length', STRATEGY_PARAMS_UI['trix_signal_length']['default'])

    trix_line_col = f'TRIX_{trix_length}_{signal_length}'
    signal_line_col = f'TRIXs_{trix_length}_{signal_length}'
    # histogram_col = f'TRIXh_{trix_length}_{signal_length}' # Optional if you want to plot histogram too

    df_for_chart = df.copy()
    if not isinstance(df_for_chart.index, pd.DatetimeIndex): return {}

    if trix_line_col in df_for_chart.columns:
        series = df_for_chart[[trix_line_col]].dropna()
        chart_data['trix_line'] = [{"time": int(idx.timestamp()*1000), "value": row[trix_line_col]} for idx,row in series.iterrows()]
    if signal_line_col in df_for_chart.columns:
        series = df_for_chart[[signal_line_col]].dropna()
        chart_data['trix_signal_line'] = [{"time": int(idx.timestamp()*1000), "value": row[signal_line_col]} for idx,row in series.iterrows()]
        
    return chart_data