# strategies/candlestick_trend_filter_strategy.py
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional
import traceback # Good to have for debugging errors within strategy

STRATEGY_NAME = "Candlestick Pattern + EMA Trend Filter"
STRATEGY_SLUG = "candle_ema_filter"
STRATEGY_DESCRIPTION = "Looks for specific candlestick patterns (e.g., Engulfing, Hammer) and confirms with an EMA trend filter."

STRATEGY_PARAMS_UI = {
    "trend_ema_length": { "label": "Trend EMA Period", "default": 20, "type": "number", "min": 5, "max": 200 },
    "candlestick_pattern": { 
        "label": "Candlestick Pattern", 
        "default": "ENGULFING", 
        "type": "select", # This will tell the UI to make a dropdown
        "options": ["ENGULFING", "HAMMER", "SHOOTINGSTAR", "MORNINGSTAR", "EVENINGSTAR", "DOJI"] 
    }
}

def calculate_strategy_indicators(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    trend_ema_length = params.get('trend_ema_length', STRATEGY_PARAMS_UI['trend_ema_length']['default'])
    pattern_code = params.get('candlestick_pattern', STRATEGY_PARAMS_UI['candlestick_pattern']['default'])

    if not all(c in df.columns for c in ['open','high','low','close']):
        print(f"!!! {STRATEGY_NAME}: OHLC columns missing for candlestick or EMA calculation.")
        # Return df as is, run_strategy will handle missing columns
        return df

    # Calculate Trend EMA
    try:
        # --- CORRECTED: Call ta on DataFrame ---
        ema_series = df.ta.ema(close=df['close'], length=trend_ema_length, append=False)
        if ema_series is not None:
            df[f'EMA_{trend_ema_length}'] = ema_series
        else:
            print(f"!!! {STRATEGY_NAME}: EMA calculation returned None for length {trend_ema_length}.")
            df[f'EMA_{trend_ema_length}'] = pd.NA # Ensure column exists even if calculation fails
    except Exception as e_ema:
        print(f"!!! {STRATEGY_NAME}: Error calculating EMA_{trend_ema_length}: {e_ema}")
        df[f'EMA_{trend_ema_length}'] = pd.NA


    pattern_col_name = f"pattern_{pattern_code.lower()}"
    pattern_series = None # Initialize
    try:
        # Call candlestick functions directly via df.ta
        cdl_function_name = f"cdl_{pattern_code.lower()}"
        
        if hasattr(df.ta, cdl_function_name):
            # Most cdl functions in pandas_ta take open, high, low, close as keyword arguments
            # if not specified, they default to the df's columns named 'open', 'high', 'low', 'close'
            pattern_series = getattr(df.ta, cdl_function_name)(
                open=df['open'], 
                high=df['high'], 
                low=df['low'], 
                close=df['close'], 
                append=False
            )
        else:
            print(f"!!! {STRATEGY_NAME}: Candlestick function 'ta.{cdl_function_name}()' not found in pandas-ta.")
            # Create a series of 0s with the same index as df if pattern not found
            pattern_series = pd.Series(0, index=df.index, name=pattern_col_name) 
            
        df[pattern_col_name] = pattern_series if pattern_series is not None else 0
    except Exception as e:
        print(f"!!! {STRATEGY_NAME}: Error calculating candlestick pattern '{pattern_code}': {e}")
        traceback.print_exc() 
        df[pattern_col_name] = 0 # Default to 0 on error
    
    return df

def run_strategy(df: pd.DataFrame, params: Dict[str, Any], current_position_type: Optional[str] = None) -> Dict[str, Any]:
    trend_ema_length = params.get('trend_ema_length', STRATEGY_PARAMS_UI['trend_ema_length']['default'])
    pattern_code = params.get('candlestick_pattern', STRATEGY_PARAMS_UI['candlestick_pattern']['default'])
    
    ema_col_name = f'EMA_{trend_ema_length}'
    pattern_col_name = f"pattern_{pattern_code.lower()}"
    signal_output = {"signal": "HOLD", "details": f"No valid {pattern_code} pattern or trend confirmation."}

    if not all(col in df.columns for col in [ema_col_name, pattern_col_name, 'close']):
        signal_output["details"] = "Required EMA, pattern, or close columns missing."
        return signal_output
    if len(df) < 1: # Need at least the last candle for pattern and close
        signal_output["details"] = "Not enough data points for candlestick signal."
        return signal_output
        
    # Check for NaNs in the specific columns and the last row we will use
    if pd.isna(df[ema_col_name].iloc[-1]) or \
       pd.isna(df[pattern_col_name].iloc[-1]) or \
       pd.isna(df['close'].iloc[-1]):
        signal_output["details"] = "EMA/Pattern/Close data incomplete (NaNs) for latest period."
        return signal_output

    latest_close = df['close'].iloc[-1]
    latest_ema = df[ema_col_name].iloc[-1]
    # Candlestick patterns usually return 100 for bullish, -100 for bearish, 0 for none.
    latest_pattern_signal_value = df[pattern_col_name].iloc[-1] 

    is_bullish_pattern = latest_pattern_signal_value > 0 
    is_bearish_pattern = latest_pattern_signal_value < 0
    pattern_name_for_details = pattern_code.replace("_", " ").title()

    buy_condition_met = False
    sell_condition_met = False

    if is_bullish_pattern and latest_close > latest_ema: # Bullish pattern in an uptrend
        buy_condition_met = True
        signal_output["details"] = f"Bullish {pattern_name_for_details} detected with Price ({latest_close:.2f}) > EMA({trend_ema_length}) ({latest_ema:.2f})."
    
    if is_bearish_pattern and latest_close < latest_ema: # Bearish pattern in a downtrend
        sell_condition_met = True
        signal_output["details"] = f"Bearish {pattern_name_for_details} detected with Price ({latest_close:.2f}) < EMA({trend_ema_length}) ({latest_ema:.2f})."

    # Generate signal based on current position (simplified for UI)
    if current_position_type is None: # No current position, looking for entry
        if buy_condition_met:
            signal_output["signal"] = "BUY"
        elif sell_condition_met:
            signal_output["signal"] = "SELL"
    elif current_position_type == "LONG":
        if sell_condition_met: # An opposite (bearish confirmed) pattern is an exit signal
            signal_output["signal"] = "CLOSE_LONG"
    elif current_position_type == "SHORT":
        if buy_condition_met: # An opposite (bullish confirmed) pattern is an exit signal
            signal_output["signal"] = "CLOSE_SHORT"
            
    # Further context if holding, even if pattern didn't align with trend
    if signal_output["signal"] == "HOLD":
        if latest_pattern_signal_value != 0: # If a pattern was detected
            pattern_type_detected = "Bullish" if is_bullish_pattern else "Bearish"
            trend_status = "uptrend (Price > EMA)" if latest_close > latest_ema else "downtrend (Price < EMA)" if latest_close < latest_ema else "price at EMA"
            signal_output["details"] = f"{pattern_type_detected} {pattern_name_for_details} pattern detected. Price is in {trend_status}."
        else: # No pattern detected on latest candle
            signal_output["details"] = f"No significant {pattern_name_for_details} pattern on latest candle."

    return signal_output

def get_chart_overlay_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    chart_data = {}; 
    trend_ema_length = params.get('trend_ema_length', STRATEGY_PARAMS_UI['trend_ema_length']['default'])
    ema_col_name = f'EMA_{trend_ema_length}'
    
    df_for_chart = df.copy()
    # Ensure index is DatetimeIndex for timestamp conversion
    if not isinstance(df_for_chart.index, pd.DatetimeIndex):
        if 'timestamp' in df_for_chart.columns: # Assuming 'timestamp' column exists from get_historical_data
            df_for_chart = df_for_chart.set_index(pd.to_datetime(df_for_chart['timestamp'], unit='ms'))
        else:
            return {} # Cannot proceed without a time reference

    if ema_col_name in df_for_chart.columns and not df_for_chart[ema_col_name].dropna().empty:
        series = df_for_chart[[ema_col_name]].dropna()
        chart_data['trend_ema_line'] = [{"time":int(idx.timestamp()*1000),"value":row[ema_col_name]} for idx,row in series.iterrows()]
    
    # Candlestick patterns are identified on the main chart (OHLC data).
    # For visualization, we could return the TIMESTAMPS where patterns occurred.
    # The JS could then draw markers. For now, just returning the EMA line.
    # Example for returning pattern occurrences:
    # pattern_code = params.get('candlestick_pattern', STRATEGY_PARAMS_UI['candlestick_pattern']['default'])
    # pattern_col_name = f"pattern_{pattern_code.lower()}"
    # if pattern_col_name in df_for_chart.columns:
    #     pattern_occurrences = df_for_chart[df_for_chart[pattern_col_name] != 0] # Filter rows where pattern exists
    #     if not pattern_occurrences.empty:
    #         chart_data[f'{pattern_code.lower()}_markers'] = [
    #             {"time": int(idx.timestamp()*1000), "value": row['close'], "signal_value": row[pattern_col_name]} # Value could be close price for positioning marker
    #             for idx, row in pattern_occurrences.iterrows()
    #         ]
            
    return chart_data