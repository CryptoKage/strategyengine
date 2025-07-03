# strategies/stochastic_oscillator_momentum.py
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional

STRATEGY_NAME = "Stochastic Oscillator Momentum"
STRATEGY_SLUG = "stochastic_momentum"
STRATEGY_DESCRIPTION = "Signals based on %K line crossing %D line in oversold/overbought territories."

STRATEGY_PARAMS_UI = {
    "stoch_k_period": { # Matches 'am_stoch_k'
        "label": "Stochastic %K Period", "default": 14, "type": "number", "min": 1, "max": 50
    },
    "stoch_d_period": { # Matches 'am_stoch_d'
        "label": "Stochastic %D Period (SMA of %K)", "default": 3, "type": "number", "min": 1, "max": 50
    },
    "stoch_smooth_k_period": { # Matches 'am_stoch_smooth_k'
        "label": "Stochastic Smooth %K Period", "default": 3, "type": "number", "min": 1, "max": 50
    },
    "stoch_oversold_level": { # Matches 'am_stoch_oversold'
        "label": "Stochastic Oversold Level", "default": 20, "type": "number", "min": 1, "max": 49
    },
    "stoch_overbought_level": { # Matches 'am_stoch_overbought'
        "label": "Stochastic Overbought Level", "default": 80, "type": "number", "min": 51, "max": 99
    }
}

def calculate_strategy_indicators(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """Calculates Stochastic Oscillator components and adds them to the DataFrame."""
    k_period = params.get('stoch_k_period', STRATEGY_PARAMS_UI['stoch_k_period']['default'])
    d_period = params.get('stoch_d_period', STRATEGY_PARAMS_UI['stoch_d_period']['default'])
    smooth_k = params.get('stoch_smooth_k_period', STRATEGY_PARAMS_UI['stoch_smooth_k_period']['default'])

    if not all(col in df.columns for col in ['high', 'low', 'close']):
        print(f"!!! {STRATEGY_NAME}: 'high', 'low', or 'close' columns missing.")
        return df

    stoch_output = df.ta.stoch(
        high=df['high'], low=df['low'], close=df['close'],
        k=k_period, d=d_period, smooth_k=smooth_k,
        append=False # Calculate separately
    )
    if stoch_output is not None and not stoch_output.empty:
        # pandas-ta names them STOCHk_k_d_smooth and STOCHd_k_d_smooth
        df[f'STOCHk_{k_period}_{d_period}_{smooth_k}'] = stoch_output[f'STOCHk_{k_period}_{d_period}_{smooth_k}']
        df[f'STOCHd_{k_period}_{d_period}_{smooth_k}'] = stoch_output[f'STOCHd_{k_period}_{d_period}_{smooth_k}']
    
    return df

def run_strategy(df: pd.DataFrame, params: Dict[str, Any], current_position_type: Optional[str] = None) -> Dict[str, Any]:
    """Calculates a trading signal for the Stochastic Oscillator Momentum strategy."""
    k_period = params.get('stoch_k_period', STRATEGY_PARAMS_UI['stoch_k_period']['default'])
    d_period = params.get('stoch_d_period', STRATEGY_PARAMS_UI['stoch_d_period']['default'])
    smooth_k = params.get('stoch_smooth_k_period', STRATEGY_PARAMS_UI['stoch_smooth_k_period']['default'])
    oversold_level = params.get('stoch_oversold_level', STRATEGY_PARAMS_UI['stoch_oversold_level']['default'])
    overbought_level = params.get('stoch_overbought_level', STRATEGY_PARAMS_UI['stoch_overbought_level']['default'])

    stoch_k_col = f'STOCHk_{k_period}_{d_period}_{smooth_k}'
    stoch_d_col = f'STOCHd_{k_period}_{d_period}_{smooth_k}'
    
    signal_output = {"signal": "HOLD", "details": "Conditions not met or Stochastic neutral."}

    if not all(col in df.columns for col in [stoch_k_col, stoch_d_col]):
        signal_output["details"] = "Required Stochastic columns missing."
        return signal_output
    if len(df) < 2:
        signal_output["details"] = "Not enough data points for signal."
        return signal_output
        
    if df[stoch_k_col].iloc[-2:].isna().any() or df[stoch_d_col].iloc[-2:].isna().any():
        signal_output["details"] = "Stochastic data incomplete (NaNs)."
        return signal_output

    latest_k = df[stoch_k_col].iloc[-1]
    previous_k = df[stoch_k_col].iloc[-2]
    latest_d = df[stoch_d_col].iloc[-1]
    previous_d = df[stoch_d_col].iloc[-2]

    # Refined Buy Condition: %K crosses above %D, and on the previous bar, both were in oversold territory.
    buy_condition_met = (previous_k <= previous_d and latest_k > latest_d) and \
                        (previous_k < oversold_level and previous_d < oversold_level)

    # Refined Sell Condition: %K crosses below %D, and on the previous bar, both were in overbought territory.
    sell_condition_met = (previous_k >= previous_d and latest_k < latest_d) and \
                         (previous_k > overbought_level and previous_d > overbought_level)

    if current_position_type is None:
        if buy_condition_met:
            signal_output["signal"] = "BUY"
            signal_output["details"] = f"%K ({latest_k:.2f}) crossed ABOVE %D ({latest_d:.2f}) from oversold zone."
        elif sell_condition_met:
            signal_output["signal"] = "SELL"
            signal_output["details"] = f"%K ({latest_k:.2f}) crossed BELOW %D ({latest_d:.2f}) from overbought zone."
    elif current_position_type == "LONG":
        if sell_condition_met:
            signal_output["signal"] = "CLOSE_LONG"
            signal_output["details"] = f"%K crossed BELOW %D from overbought (exit long)."
    elif current_position_type == "SHORT":
        if buy_condition_met:
            signal_output["signal"] = "CLOSE_SHORT"
            signal_output["details"] = f"%K crossed ABOVE %D from oversold (exit short)."
            
    if signal_output["signal"] == "HOLD": # Context
        if latest_k < oversold_level: signal_output["details"] = f"Stochastic %K ({latest_k:.2f}) in OVERSOLD zone."
        elif latest_k > overbought_level: signal_output["details"] = f"Stochastic %K ({latest_k:.2f}) in OVERBOUGHT zone."
        elif latest_k > latest_d : signal_output["details"] = f"Stochastic %K ({latest_k:.2f}) > %D ({latest_d:.2f}) (Bullish momentum)."
        else: signal_output["details"] = f"Stochastic %K ({latest_k:.2f}) < %D ({latest_d:.2f}) (Bearish momentum)."

    return signal_output

def get_chart_overlay_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Prepares Stochastic %K and %D lines for plotting."""
    chart_data = {}
    k_period = params.get('stoch_k_period', STRATEGY_PARAMS_UI['stoch_k_period']['default'])
    d_period = params.get('stoch_d_period', STRATEGY_PARAMS_UI['stoch_d_period']['default'])
    smooth_k = params.get('stoch_smooth_k_period', STRATEGY_PARAMS_UI['stoch_smooth_k_period']['default'])

    stoch_k_col = f'STOCHk_{k_period}_{d_period}_{smooth_k}'
    stoch_d_col = f'STOCHd_{k_period}_{d_period}_{smooth_k}'
    
    df_for_chart = df.copy()
    if not isinstance(df_for_chart.index, pd.DatetimeIndex): return {}

    if stoch_k_col in df_for_chart.columns:
        series = df_for_chart[[stoch_k_col]].dropna()
        chart_data['stoch_k_line'] = [{"time": int(idx.timestamp()*1000), "value": row[stoch_k_col]} for idx,row in series.iterrows()]
    if stoch_d_col in df_for_chart.columns:
        series = df_for_chart[[stoch_d_col]].dropna()
        chart_data['stoch_d_line'] = [{"time": int(idx.timestamp()*1000), "value": row[stoch_d_col]} for idx,row in series.iterrows()]
        
    return chart_data