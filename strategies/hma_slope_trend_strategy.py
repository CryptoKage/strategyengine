# strategies/hma_slope_trend_strategy.py
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional

STRATEGY_NAME = "HMA Slope Trend"
STRATEGY_SLUG = "hma_slope_trend"
STRATEGY_DESCRIPTION = "Signals based on the slope of the Hull Moving Average (HMA). BUY on positive slope, SELL on negative slope."

STRATEGY_PARAMS_UI = {
    "hma_length": { # Matches 'phantom_hma_length'
        "label": "HMA Period", "default": 20, "type": "number", "min": 2, "max": 200
    }
}

def calculate_strategy_indicators(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """Calculates Hull Moving Average (HMA) and adds it to the DataFrame."""
    length = params.get('hma_length', STRATEGY_PARAMS_UI['hma_length']['default'])

    if 'close' not in df.columns:
        print(f"!!! {STRATEGY_NAME}: 'close' column missing.")
        return df

    # pandas-ta hma appends HMA_length
    hma_output = df.ta.hma(length=length, close=df['close'], append=False)
    if hma_output is not None and not hma_output.empty:
        df[f'HMA_{length}'] = hma_output # hma_output is the series
    
    return df

def run_strategy(df: pd.DataFrame, params: Dict[str, Any], current_position_type: Optional[str] = None) -> Dict[str, Any]:
    """Calculates a trading signal based on the slope of the HMA."""
    length = params.get('hma_length', STRATEGY_PARAMS_UI['hma_length']['default'])
    hma_col_name = f'HMA_{length}'
    signal_output = {"signal": "HOLD", "details": "Conditions not met or HMA slope neutral."}

    if hma_col_name not in df.columns:
        signal_output["details"] = "HMA column missing."
        return signal_output
    if len(df) < 2: # Need current and previous HMA for slope
        signal_output["details"] = "Not enough data points for HMA slope."
        return signal_output
        
    if df[hma_col_name].iloc[-2:].isna().any():
        signal_output["details"] = "HMA data incomplete (NaNs)."
        return signal_output

    latest_hma = df[hma_col_name].iloc[-1]
    previous_hma = df[hma_col_name].iloc[-2]

    hma_slope_positive = latest_hma > previous_hma
    hma_slope_negative = latest_hma < previous_hma
    
    buy_condition_met = False
    sell_condition_met = False

    if hma_slope_positive:
        buy_condition_met = True
    elif hma_slope_negative:
        sell_condition_met = True
        
    if current_position_type is None:
        if buy_condition_met:
            signal_output["signal"] = "BUY"
            signal_output["details"] = f"HMA({length}) slope turned POSITIVE (HMA: {latest_hma:.2f})."
        elif sell_condition_met:
            signal_output["signal"] = "SELL"
            signal_output["details"] = f"HMA({length}) slope turned NEGATIVE (HMA: {latest_hma:.2f})."
    elif current_position_type == "LONG":
        if sell_condition_met:
            signal_output["signal"] = "CLOSE_LONG"
            signal_output["details"] = f"HMA slope turned NEGATIVE (exit long)."
    elif current_position_type == "SHORT":
        if buy_condition_met:
            signal_output["signal"] = "CLOSE_SHORT"
            signal_output["details"] = f"HMA slope turned POSITIVE (exit short)."
            
    if signal_output["signal"] == "HOLD":
        if hma_slope_positive: signal_output["details"] = f"HMA({length}) currently RISING (HMA: {latest_hma:.2f})."
        elif hma_slope_negative: signal_output["details"] = f"HMA({length}) currently FALLING (HMA: {latest_hma:.2f})."
        else: signal_output["details"] = f"HMA({length}) slope is FLAT (HMA: {latest_hma:.2f})."


    return signal_output

def get_chart_overlay_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Prepares HMA line data for plotting."""
    chart_data = {}
    length = params.get('hma_length', STRATEGY_PARAMS_UI['hma_length']['default'])
    hma_col_name = f'HMA_{length}'
    
    df_for_chart = df.copy()
    if not isinstance(df_for_chart.index, pd.DatetimeIndex): return {}

    if hma_col_name in df_for_chart.columns:
        series = df_for_chart[[hma_col_name]].dropna()
        chart_data['hma_line'] = [{"time": int(idx.timestamp()*1000), "value": row[hma_col_name]} for idx,row in series.iterrows()]
        
    return chart_data