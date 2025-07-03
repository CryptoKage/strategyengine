# strategies/donchian_channels_strategy.py
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional
import traceback

STRATEGY_NAME = "Donchian Channel Breakout"
STRATEGY_SLUG = "donchian_breakout"
STRATEGY_DESCRIPTION = "Signals when price breaks above or below the Donchian Channels."

STRATEGY_PARAMS_UI = {
    "donchian_upper_length": {"label": "Donchian Upper Period", "default": 20, "type": "number", "min": 2, "max": 100},
    "donchian_lower_length": {"label": "Donchian Lower Period", "default": 20, "type": "number", "min": 2, "max": 100}
}

def calculate_strategy_indicators(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    upper_length = params.get('donchian_upper_length', STRATEGY_PARAMS_UI['donchian_upper_length']['default'])
    lower_length = params.get('donchian_lower_length', STRATEGY_PARAMS_UI['donchian_lower_length']['default'])

    if not all(c in df.columns for c in ['high', 'low']): return df

    try:
        # Let pandas-ta append its default column names
        df.ta.donchian(high=df['high'], low=df['low'], 
                      upper_length=upper_length, lower_length=lower_length, 
                      append=True)
        print(f"--- DEBUG: Columns after pandas-ta.donchian: {df.columns.tolist()} ---")
    except Exception as e:
        print(f"!!! {STRATEGY_NAME}: Error during donchian calc: {e}"); traceback.print_exc()
        # Ensure columns exist with NaNs if calc fails
        df[f'DCU_{upper_length}'] = pd.NA
        df[f'DCL_{lower_length}'] = pd.NA
        return df
    return df

def run_strategy(df: pd.DataFrame, params: Dict[str, Any], current_position_type: Optional[str] = None) -> Dict[str, Any]:
    upper_length = params.get('donchian_upper_length'); lower_length = params.get('donchian_lower_length')
    
    # --- Use the default names pandas-ta creates ---
    upper_col = f'DCU_{upper_length}'
    lower_col = f'DCL_{lower_length}'
    
    signal_output = {"signal": "HOLD", "details": "Conditions not met."}

    if not all(c in df.columns for c in [upper_col, lower_col, 'close']) or len(df)<1 or \
       pd.isna(df[upper_col].iloc[-1]) or pd.isna(df[lower_col].iloc[-1]) or pd.isna(df['close'].iloc[-1]):
        signal_output["details"] = "Donchian/close data incomplete or missing."; return signal_output
        
    lc=df['close'].iloc[-1]; lub=df[upper_col].iloc[-1]; llb=df[lower_col].iloc[-1]
    buy_breakout = lc > lub; sell_breakdown = lc < llb
    if buy_breakout: signal_output.update({"signal":"BUY", "details":f"Price ({lc:.2f}) broke ABOVE Upper Donchian ({lub:.2f})."})
    elif sell_breakdown: signal_output.update({"signal":"SELL", "details":f"Price ({lc:.2f}) broke BELOW Lower Donchian ({llb:.2f})."})
    else: signal_output["details"] = f"Price ({lc:.2f}) is within Donchian Channels ({llb:.2f} - {lub:.2f})."
    return signal_output

def get_chart_overlay_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    chart_data={}; upper_length=params.get('donchian_upper_length'); lower_length=params.get('donchian_lower_length')
    
    # Use the default names pandas-ta creates
    upper_col=f'DCU_{upper_length}'; lower_col=f'DCL_{lower_length}'
    middle_col=f'DCM_{lower_length}_{upper_length}' if lower_length != upper_length else f'DCM_{lower_length}'

    df_chart=df.copy()
    if not isinstance(df_chart.index, pd.DatetimeIndex):
        if 'timestamp' in df_chart.columns: df_chart = df_chart.set_index(pd.to_datetime(df_chart['timestamp'], unit='ms'))
        else: return {}
    
    for col_key, chart_key in [(upper_col,'donchian_upper'), (middle_col,'donchian_middle'), (lower_col,'donchian_lower')]:
        if col_key in df_chart.columns:
            series=df_chart[[col_key]].dropna()
            if not series.empty:
                chart_data[chart_key]=[{"time":int(i.timestamp()*1000),"value":r[col_key]} for i,r in series.iterrows()]
    return chart_data