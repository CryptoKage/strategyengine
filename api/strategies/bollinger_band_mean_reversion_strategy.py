# strategies/bollinger_band_mean_reversion_strategy.py
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional
import traceback

STRATEGY_NAME = "Bollinger Bands Mean Reversion"
STRATEGY_SLUG = "bbands_mean_reversion"
STRATEGY_DESCRIPTION = "Trades on price touching outer Bollinger Bands for entry and returning to the middle band for exit."

STRATEGY_PARAMS_UI = {
    "bbands_length": {"label": "BBands Length", "default": 20, "type": "number", "min": 2, "max": 100},
    "bbands_std_dev": {"label": "BBands Std Deviation", "default": 2.0, "type": "number", "min": 0.1, "max": 5.0, "step": 0.1}
}

def calculate_strategy_indicators(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    length = params.get('bbands_length', STRATEGY_PARAMS_UI['bbands_length']['default'])
    std_dev = params.get('bbands_std_dev', STRATEGY_PARAMS_UI['bbands_std_dev']['default'])
    if 'close' not in df.columns: print(f"!!! {STRATEGY_NAME}: 'close' column missing."); return df
    try:
        df.ta.bbands(close=df['close'], length=length, std=std_dev, append=True)
        print(f"--- DEBUG: Columns after pandas-ta.bbands: {df.columns.tolist()} ---")
    except Exception as e:
        print(f"!!! {STRATEGY_NAME}: Error during bbands calc: {e}"); traceback.print_exc()
    return df

# --- CORRECTED run_strategy and get_chart_overlay_data ---
def construct_bband_col_names(params: Dict[str, Any]) -> Dict[str, str]:
    """Helper function to consistently generate BBands column names."""
    length = params.get('bbands_length', STRATEGY_PARAMS_UI['bbands_length']['default'])
    std_dev = params.get('bbands_std_dev', STRATEGY_PARAMS_UI['bbands_std_dev']['default'])
    # pandas-ta uses float format "2.0" in name, even if input is int 2.
    std_dev_str = f"{float(std_dev):g}" # Use 'g' format to remove trailing .0 if possible, but be flexible
    
    # Based on logs, it seems to use the float representation.
    # The safest way is to find it, but let's try constructing the most likely name.
    # It appears pandas-ta standardizes to float for the name, e.g. "BBL_20_2.0"
    std_dev_name_str = str(float(std_dev))

    return {
        "lower": f'BBL_{length}_{std_dev_name_str}',
        "middle": f'BBM_{length}_{std_dev_name_str}',
        "upper": f'BBU_{length}_{std_dev_name_str}'
    }

def run_strategy(df: pd.DataFrame, params: Dict[str, Any], current_position_type: Optional[str] = None) -> Dict[str, Any]:
    col_names = construct_bband_col_names(params)
    lower_band_col, middle_band_col, upper_band_col = col_names['lower'], col_names['middle'], col_names['upper']
    
    signal_output = {"signal": "HOLD", "details": "Conditions not met."}

    if not all(col in df.columns for col in [lower_band_col, middle_band_col, upper_band_col, 'close']):
        signal_output["details"] = f"Required BBands columns missing. Looking for: {lower_band_col}, etc."
        return signal_output
    if len(df) < 2 or df[middle_band_col].iloc[-2:].isna().any() or pd.isna(df[lower_band_col].iloc[-1]) or pd.isna(df[upper_band_col].iloc[-1]):
        signal_output["details"] = "BBands data incomplete (NaNs)."; return signal_output

    latest_close=df['close'].iloc[-1]; prev_close=df['close'].iloc[-2]
    latest_lower=df[lower_band_col].iloc[-1]; latest_middle=df[middle_band_col].iloc[-1]
    prev_middle=df[middle_band_col].iloc[-2]; latest_upper=df[upper_band_col].iloc[-1]

    buy_entry = latest_close <= latest_lower; sell_entry = latest_close >= latest_upper
    close_long = (prev_close <= prev_middle) and (latest_close > latest_middle)
    close_short = (prev_close >= prev_middle) and (latest_close < latest_middle)
    
    if buy_entry: signal_output.update({"signal":"BUY", "details":f"Price <= Lower BB."})
    elif sell_entry: signal_output.update({"signal":"SELL", "details":f"Price >= Upper BB."})
    elif close_long: signal_output.update({"signal":"CLOSE_LONG", "details":"Price crossed above Middle BB."})
    elif close_short: signal_output.update({"signal":"CLOSE_SHORT", "details":"Price crossed below Middle BB."})
    elif latest_close > latest_middle: signal_output.update({"details":f"Price > Middle BB (Bullish Bias).", "bias":"bullish"})
    else: signal_output.update({"details":f"Price < Middle BB (Bearish Bias).", "bias":"bearish"})
    return signal_output

def get_chart_overlay_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    chart_data = {}
    col_names = construct_bband_col_names(params)
    lower_col, middle_col, upper_col = col_names['lower'], col_names['middle'], col_names['upper']
    
    df_chart=df.copy()
    if not isinstance(df_chart.index, pd.DatetimeIndex):
        if 'timestamp' in df_chart.columns: df_chart = df_chart.set_index(pd.to_datetime(df_chart['timestamp'], unit='ms'))
        else: return {}

    for col_key, chart_key in [(lower_col,'bband_lower'), (middle_col,'bband_middle'), (upper_col,'bband_upper')]:
        if col_key in df_chart.columns and not df_chart[col_key].dropna().empty:
            series=df_chart[[col_key]].dropna(); chart_data[chart_key]=[{"time":int(i.timestamp()*1000),"value":r[col_key]} for i,r in series.iterrows()]
    return chart_data