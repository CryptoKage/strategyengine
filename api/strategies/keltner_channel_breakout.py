# strategies/keltner_channel_breakout_strategy.py  needs fixing
import pandas as pd
import pandas_ta as ta
import traceback
from typing import Dict, Any, Optional

STRATEGY_NAME = "Keltner Channel Breakout"
STRATEGY_SLUG = "keltner_breakout"
STRATEGY_DESCRIPTION = "Signals when price breaks above the Upper Keltner Channel (BUY) or below the Lower Keltner Channel (SELL)."

STRATEGY_PARAMS_UI = {
    "kc_ema_length": { "label": "KC EMA Period", "default": 20, "type": "number", "min": 2, "max": 100 },
    "kc_atr_length": { "label": "KC ATR Period", "default": 10, "type": "number", "min": 1, "max": 50 },
    "kc_atr_multiplier": { "label": "KC ATR Multiplier", "default": 2.0, "type": "number", "min": 0.1, "max": 5.0, "step": 0.1 }
}

def calculate_strategy_indicators(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """Calculates Keltner Channels and renames columns to a consistent internal format."""
    ema_len = params.get('kc_ema_length', STRATEGY_PARAMS_UI['kc_ema_length']['default'])
    atr_len = params.get('kc_atr_length', STRATEGY_PARAMS_UI['kc_atr_length']['default']) # Used for our desired col name
    atr_mult = params.get('kc_atr_multiplier', STRATEGY_PARAMS_UI['kc_atr_multiplier']['default'])

    if not all(col in df.columns for col in ['high', 'low', 'close']):
        print(f"!!! {STRATEGY_NAME}: HLC columns missing for Keltner calculation."); return df

    # Let pandas-ta append its default names first
    try:
        # Crucial: pandas-ta 'kc' uses 'length' for EMA, 'atr_length' for ATR, 'scalar' for multiplier
        df.ta.kc(
            high=df['high'], low=df['low'], close=df['close'],
            length=ema_len,      # This is the EMA period for KC
            atr_length=atr_len,  # This is the ATR period for KC internal calc
            scalar=atr_mult,     # This is the ATR multiplier for KC
            append=True          # Let pandas-ta add its default column names
        )
        print(f"--- DEBUG: Columns after pandas-ta.kc (params: EMA_L={ema_len}, ATR_L={atr_len}, Scalar={atr_mult}): {df.columns.tolist()} ---")
    except Exception as e:
        print(f"!!! {STRATEGY_NAME}: Error during pandas-ta.kc calculation: {e}")
        traceback.print_exc()
        # Ensure our desired columns exist with NaNs if calculation failed
        df[f'KCLe_{ema_len}_{atr_len}_{atr_mult}'] = pd.NA
        df[f'KCBe_{ema_len}_{atr_len}_{atr_mult}'] = pd.NA
        df[f'KCUe_{ema_len}_{atr_len}_{atr_mult}'] = pd.NA
        return df

    # --- Identify the columns pandas-ta created and RENAME them to our desired format ---
    # pandas-ta for Keltner Channels with EMA: KCLe_EMA_SCALAR, KCBe_EMA_SCALAR, KCUe_EMA_SCALAR
    # The scalar (atr_mult) might be int (e.g., "2") or float ("2.0", "2.1") in the name.

    # Construct the multiplier string part as pandas-ta likely creates it
    mult_str_pta = str(float(atr_mult)) # e.g., "2.0", "2.1"
    if mult_str_pta.endswith(".0"):
        mult_str_pta = str(int(float(atr_mult))) # "2"
    # For floats like 2.1, pandas-ta might use "2.1" or sometimes "2_1". Let's check both.
    
    pta_generated_lower_options = [f'KCLe_{ema_len}_{mult_str_pta}', f'KCLe_{ema_len}_{str(atr_mult).replace(".","_")}']
    pta_generated_basis_options = [f'KCBe_{ema_len}_{mult_str_pta}', f'KCBe_{ema_len}_{str(atr_mult).replace(".","_")}']
    pta_generated_upper_options = [f'KCUe_{ema_len}_{mult_str_pta}', f'KCUe_{ema_len}_{str(atr_mult).replace(".","_")}']

    actual_pta_lower_col = next((col for col in pta_generated_lower_options if col in df.columns), None)
    actual_pta_basis_col = next((col for col in pta_generated_basis_options if col in df.columns), None)
    actual_pta_upper_col = next((col for col in pta_generated_upper_options if col in df.columns), None)
    
    # Our desired consistent column names (which include atr_len for our internal clarity)
    desired_lower_col = f'KCLe_{ema_len}_{atr_len}_{atr_mult}'
    desired_basis_col = f'KCBe_{ema_len}_{atr_len}_{atr_mult}'
    desired_upper_col = f'KCUe_{ema_len}_{atr_len}_{atr_mult}'

    # Rename if found and different, otherwise ensure the desired column exists (even if with NaNs)
    if actual_pta_lower_col:
        if actual_pta_lower_col != desired_lower_col: df.rename(columns={actual_pta_lower_col: desired_lower_col}, inplace=True)
    elif desired_lower_col not in df.columns: df[desired_lower_col] = pd.NA

    if actual_pta_basis_col:
        if actual_pta_basis_col != desired_basis_col: df.rename(columns={actual_pta_basis_col: desired_basis_col}, inplace=True)
    elif desired_basis_col not in df.columns: df[desired_basis_col] = pd.NA
        
    if actual_pta_upper_col:
        if actual_pta_upper_col != desired_upper_col: df.rename(columns={actual_pta_upper_col: desired_upper_col}, inplace=True)
    elif desired_upper_col not in df.columns: df[desired_upper_col] = pd.NA
    
    if desired_lower_col not in df.columns or desired_basis_col not in df.columns or desired_upper_col not in df.columns:
        print(f"!!! {STRATEGY_NAME}: Failed to map all Keltner columns to desired names. Current df columns: {df.columns.tolist()}")
        # This indicates an issue with matching pandas-ta's output naming convention.
    else:
        print(f"Successfully mapped Keltner columns: L->{desired_lower_col}, B->{desired_basis_col}, U->{desired_upper_col}")

    return df

def run_strategy(df: pd.DataFrame, params: Dict[str, Any], current_position_type: Optional[str] = None) -> Dict[str, Any]:
    ema_len = params.get('kc_ema_length', STRATEGY_PARAMS_UI['kc_ema_length']['default'])
    atr_len = params.get('kc_atr_length', STRATEGY_PARAMS_UI['kc_atr_length']['default'])
    atr_mult = params.get('kc_atr_multiplier', STRATEGY_PARAMS_UI['kc_atr_multiplier']['default'])

    # Use our consistent "desired" column names
    lower_band_col = f'KCLe_{ema_len}_{atr_len}_{atr_mult}'
    upper_band_col = f'KCUe_{ema_len}_{atr_len}_{atr_mult}'
    middle_band_col = f'KCBe_{ema_len}_{atr_len}_{atr_mult}' # If you use middle band in logic
    
    signal_output = {"signal": "HOLD", "details": "Conditions not met or price within Keltner Channels."}

    if not all(col in df.columns for col in [lower_band_col, upper_band_col, 'close']):
        signal_output["details"] = "Required Keltner/close columns missing for signal generation."
        return signal_output
    if len(df) < 1: # Need at least the latest candle for breakout check
        signal_output["details"] = "Not enough data points for Keltner signal."
        return signal_output
        
    # Check for NaNs in the specific columns we will use
    if pd.isna(df[upper_band_col].iloc[-1]) or \
       pd.isna(df[lower_band_col].iloc[-1]) or \
       pd.isna(df['close'].iloc[-1]):
        signal_output["details"] = "Keltner/close data incomplete (NaNs) for latest period."
        return signal_output

    latest_close = df['close'].iloc[-1]
    latest_upper_band = df[upper_band_col].iloc[-1]
    latest_lower_band = df[lower_band_col].iloc[-1]

    buy_breakout_occurred = latest_close > latest_upper_band
    sell_breakdown_occurred = latest_close < latest_lower_band

    # Your existing signal logic from the file:
    if current_position_type is None:
        if buy_breakout_occurred: signal_output.update({"signal":"BUY", "details":f"Price ({latest_close:.2f}) > Upper KC ({latest_upper_band:.2f})."})
        elif sell_breakdown_occurred: signal_output.update({"signal":"SELL", "details":f"Price ({latest_close:.2f}) < Lower KC ({latest_lower_band:.2f})."})
    elif current_position_type == "LONG":
        if sell_breakdown_occurred: signal_output.update({"signal":"CLOSE_LONG", "details":"Price broke below Lower KC."})
    elif current_position_type == "SHORT":
        if buy_breakout_occurred: signal_output.update({"signal":"CLOSE_SHORT", "details":"Price broke above Upper KC."})
            
    if signal_output["signal"] == "HOLD": # Context for HOLD
        signal_output["details"] = f"Price ({latest_close:.2f}) within KC ({latest_lower_band:.2f} - {latest_upper_band:.2f})."

    return signal_output

def get_chart_overlay_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    chart_data = {}
    ema_len = params.get('kc_ema_length', STRATEGY_PARAMS_UI['kc_ema_length']['default'])
    atr_len = params.get('kc_atr_length', STRATEGY_PARAMS_UI['kc_atr_length']['default'])
    atr_mult = params.get('kc_atr_multiplier', STRATEGY_PARAMS_UI['kc_atr_multiplier']['default'])
    
    # Use our consistent "desired" column names
    lower_col = f'KCLe_{ema_len}_{atr_len}_{atr_mult}'
    middle_col = f'KCBe_{ema_len}_{atr_len}_{atr_mult}'
    upper_col = f'KCUe_{ema_len}_{atr_len}_{atr_mult}'
    
    df_for_chart = df.copy()
    # Ensure index is DatetimeIndex for timestamp conversion
    if not isinstance(df_for_chart.index, pd.DatetimeIndex):
        if 'timestamp' in df_for_chart.columns: # Assuming 'timestamp' column exists from get_historical_data
            df_for_chart = df_for_chart.set_index(pd.to_datetime(df_for_chart['timestamp'], unit='ms'))
        else:
            return {} # Cannot proceed without a time reference

    for col_key, chart_key in [(upper_col, 'keltner_upper'), (middle_col, 'keltner_middle'), (lower_col, 'keltner_lower')]:
        if col_key in df_for_chart.columns and not df_for_chart[col_key].dropna().empty:
            series = df_for_chart[[col_key]].dropna()
            chart_data[chart_key] = [{"time":int(idx.timestamp()*1000),"value":row[col_key]} for idx,row in series.iterrows()]
        else:
            print(f"Chart overlay data: Column {col_key} not found or all NaN in Keltner df.")
            
    return chart_data