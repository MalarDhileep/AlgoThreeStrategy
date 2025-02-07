import MetaTrader5 as mt5
import time
import pandas as pd
def calculate_pivot_points(symbol):
    rate = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 1, 2)
    if len(rate) < 2:
        print("Not enough data to calculate pivot points.")
        return None
    
    prev_close = rate[1]['close']
    prev_high = rate[1]['high']
    prev_low = rate[1]['low']

    CP = (prev_close + prev_high + prev_low) / 3
    BC = (prev_high + prev_low) / 2
    TC = (CP - BC) + CP

    pivot_points = {
            'PivotT': TC,
            'PivotC': CP,
            'PivotB': BC,
            'R1': CP + (prev_high - prev_low) * 1.1 / 4,
            'R2': CP + (prev_high - prev_low) * 1.1 / 2,
            'R3': CP + (prev_high - prev_low) * 1.1,
            'S1': CP - (prev_high - prev_low) * 1.1 / 4,
            'S2': CP - (prev_high - prev_low) * 1.1 / 2,
            'S3': CP - (prev_high - prev_low) * 1.1,
            'PDH': prev_high,
            'PDL': prev_low,
    }

    # print(f"Today Day's Central Pivot (CP): {CP}, Bottom Central (BC): {BC}, Top Central (TC): {TC}")
    return pivot_points
    
def pivot_strategy(df, pivot_points):
    if not pivot_points:
        print("Pivot points not available.")
        return None
    prev_candle = df.iloc[-2]
    last_candle = df.iloc[-1]
    next_candle = df.iloc[-1]   
    close_price = last_candle['close']
    prev_close_price = prev_candle['close']
    signals = []
    # print(f"Prev Close: {prev_close_price}, Close: {close_price}")
    # print(f"Pivot Levels: S3={pivot_points['S3']}, S2={pivot_points['S2']}, S1={pivot_points['S1']},R1={pivot_points['R1']}, R2={pivot_points['R2']}, R3={pivot_points['R3']},")

    # Check for crossovers with pivot points
    if prev_close_price < pivot_points['S3'] and close_price > pivot_points['S3']:
        entry_price = next_candle['open'] 
        signals.append(('buy', 'Crossed above S3'))
    elif prev_close_price < pivot_points['S2'] and close_price > pivot_points['S2']:
        entry_price = next_candle['open'] 
        signals.append(('buy', 'Crossed above S2'))
    elif prev_close_price < pivot_points['S1'] and close_price > pivot_points['S1']:
        entry_price = next_candle['open'] 
        signals.append(('buy', 'Crossed above S1'))
    elif prev_close_price < pivot_points['PivotT'] and close_price > pivot_points['PivotT']:
        entry_price = next_candle['open'] 
        signals.append(('buy', 'Crossed above Pivot Top'))
    elif prev_close_price < pivot_points['PivotC'] and close_price > pivot_points['PivotC']:
        entry_price = next_candle['open'] 
        signals.append(('buy', 'Crossed above Pivot Central'))    
    elif prev_close_price < pivot_points['PivotB'] and close_price > pivot_points['PivotB']:
        entry_price = next_candle['open'] 
        signals.append(('buy', 'Crossed above Pivot Buttom'))
    elif prev_close_price < pivot_points['R1'] and close_price > pivot_points['R1']:
        entry_price = next_candle['open'] 
        signals.append(('buy', 'Crossed above R1'))
    elif prev_close_price < pivot_points['R2'] and close_price > pivot_points['R2']:
        entry_price = next_candle['open'] 
        signals.append(('buy', 'Crossed above R2'))
    elif prev_close_price < pivot_points['PDH'] and close_price > pivot_points['PDH']:
        entry_price = next_candle['open'] 
        signals.append(('buy', 'Crossed above Previous day high'))
    elif prev_close_price < pivot_points['PDL'] and close_price > pivot_points['PDL']:
        entry_price = next_candle['open'] 
        signals.append(('buy', 'Crossed above Previous day low'))

    #Sell Signal
    if prev_close_price > pivot_points['R3'] and close_price < pivot_points['R3']:
        entry_price = next_candle['open']
        signals.append(('sell', 'Crossed below R3'))
    elif prev_close_price > pivot_points['R2'] and close_price < pivot_points['R2']:
        entry_price = next_candle['open']
        signals.append(('sell', 'Crossed below R2'))
    elif prev_close_price > pivot_points['R1'] and close_price < pivot_points['R1']:
        entry_price = next_candle['open'] 
        signals.append(('sell', 'Crossed below R1'))
    elif prev_close_price > pivot_points['PivotT'] and close_price < pivot_points['PivotT']:
        entry_price = next_candle['open'] 
        signals.append(('sell', 'Crossed below Pivot Top'))
    elif prev_close_price > pivot_points['PivotC'] and close_price < pivot_points['PivotC']:
        entry_price = next_candle['open']
        signals.append(('sell', 'Crossed below Pivot Central'))
    elif prev_close_price > pivot_points['PivotB'] and close_price < pivot_points['PivotB']:
        entry_price = next_candle['open']
        signals.append(('sell', 'Crossed below Pivot Buttom'))
    elif prev_close_price > pivot_points['S1'] and close_price < pivot_points['S1']:
        entry_price = next_candle['open']
        signals.append(('sell', 'Crossed below S1'))
    elif prev_close_price > pivot_points['S2'] and close_price < pivot_points['S2']:
        entry_price = next_candle['open']
        signals.append(('sell', 'Crossed below S2'))
    elif prev_close_price > pivot_points['PDH'] and close_price < pivot_points['PDH']:
        entry_price = next_candle['open']
        signals.append(('sell', 'Crossed below Previous day high'))
    elif prev_close_price > pivot_points['PDL'] and close_price < pivot_points['PDL']:
        entry_price = next_candle['open']
        signals.append(('sell', 'Crossed below Previous day low'))
    return signals