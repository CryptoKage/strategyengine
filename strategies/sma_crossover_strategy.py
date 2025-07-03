# strategies/sma_crossover_strategy.py
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional

STRATEGY_NAME = "SMA Crossover"
STRATEGY_SLUG = "sma_crossover"
STRATEGY_DESCRIPTION = "Simple Moving Average (SMA) crossover strategy. BUY on short SMA crossing above long SMA, SELL on cross below."

STRATEGY_PARAMS_UI = {
    "short_sma_period": {
        "label": "Short SMA Period", "default": 10, "type": "number", "min": 1, "max": 100
    },
    "long_sma_period": {
        "label": "Long SMA Period", "default": 20, "type": "number", "min": 2, "max": 200
    }
}

def calculate_strategy_indicators(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """Calculates SMAs and adds them to the DataFrame."""
    short_period = params.get('short_sma_period', STRATEGY_PARAMS_UI['short_sma_period']['default'])
    long_period = params.get('long_sma_period', STRATEGY_PARAMS_UI['long_sma_period']['default'])

    if 'close' not in df.columns:
        print(f"!!! {STRATEGY_NAME}: 'close' column missing.")
        return df

    # Calculate SMAs using pandas_ta on the DataFrame
    sma_short_series = df.ta.sma(length=short_period, close=df['close'], append=False)
    sma_long_series = df.ta.sma(length=long_period, close=df['close'], append=False)

    if sma_short_series is not None:
        df[f'SMA_{short_period}'] = sma_short_series
    else: # Ensure column exists even if calc fails
        df[f'SMA_{short_period}'] = pd.NA


    if sma_long_series is not None:
        df[f'SMA_{long_period}'] = sma_long_series
    else: # Ensure column exists
        df[f'SMA_{long_period}'] = pd.NA
    
    return df

def run_strategy(df: pd.DataFrame, params: Dict[str, Any], current_position_type: Optional[str] = None) -> Dict[str, Any]:
    """Calculates a trading signal for the SMA Crossover strategy."""
    short_period = params.get('short_sma_period', STRATEGY_PARAMS_UI['short_sma_period']['default'])
    long_period = params.get('long_sma_period', STRATEGY_PARAMS_UI['long_sma_period']['default'])

    sma_short_col = f"SMA_{short_period}"
    sma_long_col = f"SMA_{long_period}"
    signal_output = {"signal": "HOLD", "details": "Conditions not met or SMAs neutral."}

    if not all(col in df.columns for col in [sma_short_col, sma_long_col]):
        signal_output["details"] = "Required SMA columns missing."
        return signal_output
    if len(df) < 2: # Need current and previous for crossover
        signal_output["details"] = "Not enough data points for crossover."
        return signal_output
        
    if df[sma_short_col].iloc[-2:].isna().any() or df[sma_long_col].iloc[-2:].isna().any():
        signal_output["details"] = "SMA data incomplete (NaNs) for recent periods."
        return signal_output

    last_short_sma = df[sma_short_col].iloc[-1]
    prev_short_sma = df[sma_short_col].iloc[-2]
    last_long_sma = df[sma_long_col].iloc[-1]
    prev_long_sma = df[sma_long_col].iloc[-2]

    # Logic from your provided file
    if current_position_type is None:
        if prev_short_sma <= prev_long_sma and last_short_sma > last_long_sma:
            signal_output["signal"] = "BUY"
            signal_output["details"] = f"SMA({short_period}) crossed ABOVE SMA({long_period})."
        elif prev_short_sma >= prev_long_sma and last_short_sma < last_long_sma:
            signal_output["signal"] = "SELL"
            signal_output["details"] = f"SMA({short_period}) crossed BELOW SMA({long_period})."
    elif current_position_type == "LONG":
        if prev_short_sma >= prev_long_sma and last_short_sma < last_long_sma:
            signal_output["signal"] = "CLOSE_LONG"
            signal_output["details"] = "SMA short crossed below long (exit long)."
    elif current_position_type == "SHORT":
        if prev_short_sma <= prev_long_sma and last_short_sma > last_long_sma:
            signal_output["signal"] = "CLOSE_SHORT"
            signal_output["details"] = "SMA short crossed above long (exit short)."
            
    if signal_output["signal"] == "HOLD": # Context
        if last_short_sma > last_long_sma: signal_output["details"] = f"SMA({short_period}) > SMA({long_period}) (Long Bias)."
        elif last_short_sma < last_long_sma: signal_output["details"] = f"SMA({short_period}) < SMA({long_period}) (Short Bias)."
        else: signal_output["details"] = "SMAs are equal or no crossover."

    return signal_output

def get_chart_overlay_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Prepares SMA lines data for plotting."""
    chart_data = {}
    short_period = params.get('short_sma_period', STRATEGY_PARAMS_UI['short_sma_period']['default'])
    long_period = params.get('long_sma_period', STRATEGY_PARAMS_UI['long_sma_period']['default'])

    sma_short_col = f'SMA_{short_period}'
    sma_long_col = f'SMA_{long_period}'
    
    df_for_chart = df.copy()
    # Ensure index is DatetimeIndex for timestamp conversion
    if not isinstance(df_for_chart.index, pd.DatetimeIndex):
        if 'timestamp' in df_for_chart.columns: # Assuming 'timestamp' column exists from get_historical_data
            df_for_chart = df_for_chart.set_index(pd.to_datetime(df_for_chart['timestamp'], unit='ms'))
        else:
            return {} # Cannot proceed without a time reference

    if sma_short_col in df_for_chart.columns:
        series = df_for_chart[[sma_short_col]].dropna()
        chart_data['sma_short'] = [{"time": int(idx.timestamp()*1000), "value": row[sma_short_col]} for idx,row in series.iterrows()]
    if sma_long_col in df_for_chart.columns:
        series = df_for_chart[[sma_long_col]].dropna()
        chart_data['sma_long'] = [{"time": int(idx.timestamp()*1000), "value": row[sma_long_col]} for idx,row in series.iterrows()]
        
    return chart_data