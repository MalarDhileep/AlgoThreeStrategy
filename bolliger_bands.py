import MetaTrader5 as mt5
import time
import pandas as pd

def calculate_bollinger_bands(data,TIMEFRAM, window=20, std_dev=2):    
    data['middle_band'] = data['close'].rolling(window=TIMEFRAM).mean()
    data['upper_band'] = data['middle_band'] + (data['close'].rolling(window=TIMEFRAM).std() * std_dev)
    data['lower_band'] = data['middle_band'] - (data['close'].rolling(window=TIMEFRAM).std() * std_dev)
    return data

# Generate trading signal
def bb_strategy(data):
    if len(data) < 3:
        return [] 
    previous_row = data.iloc[-3]
    last_row = data.iloc[-2]
    next_row = data.iloc[-1] 
    prev = data.iloc[-3]      # Before breakout
    breakout = data.iloc[-2]  # Breakout candle
    current = data.iloc[-1]

    
    signals = []
    
    # Buy signal
    if previous_row['close'] < previous_row['upper_band'] and last_row['close'] > last_row['upper_band']:
        entry_price = next_row['open'] 
        signals.append(('buy', 'Crossed above upper_band'))
  
    elif previous_row['close'] < previous_row['lower_band'] and last_row['close'] > last_row['lower_band']:
        entry_price = next_row['open'] 
        signals.append(('buy', 'Crossed above lower_band'))

    elif previous_row['close'] < previous_row['middle_band'] and last_row['close'] > last_row['middle_band']:
        entry_price = next_row['open'] 
        signals.append(('buy', 'Crossed above middle_band'))
        
    # Sell signal
    elif previous_row['close'] > previous_row['middle_band'] and last_row['close'] < last_row['middle_band']:
        entry_price = next_row['open'] 
        signals.append(('sell', 'Crossed below middle_band'))

    elif previous_row['close'] > previous_row['lower_band'] and last_row['close'] < last_row['lower_band']:
        entry_price = next_row['open'] 
        signals.append(('sell', 'Crossed below lower_band'))

    elif previous_row['close'] > previous_row['upper_band'] and last_row['close'] < last_row['upper_band']:
        entry_price = next_row['open'] 
        signals.append(('sell', 'Crossed below upper_band'))

    #Reversal Strategy
    elif breakout['close'] > breakout['upper_band'] and prev['close'] < prev['upper_band'] and current['high'] > breakout['high']:
        signals.append(('buy', "Reversal Entry from High break out Upper Band"))

    elif breakout['close'] > breakout['middle_band'] and prev['close'] < prev['middle_band'] and current['high'] > breakout['high']:
        signals.append(('buy', "Reversal Entry from High break out middle_band"))

    elif breakout['close'] < breakout['lower_band'] and prev['close'] < prev['lower_band'] and current['high'] > breakout['high']:
        signals.append(('buy', "Reversal Entry from High break out Lower Band"))

    # Sell on **Reversal Entry**
    elif breakout['close'] < breakout['lower_band'] and prev['close'] > prev['lower_band'] and current['low'] < breakout['low']:
        signals.append(('sell', "Reversal Entry from Low break out Lower Band"))

    elif breakout['close'] < breakout['middle_band'] and prev['close'] > prev['middle_band'] and current['low'] < breakout['low']:
        signals.append(('sell', "Reversal Entry from Low break out middle_band"))

    elif breakout['close'] > breakout['upper_band'] and prev['close'] > prev['upper_band'] and current['low'] < breakout['low']:
        signals.append(('sell', "Reversal Entry from Low break out Upper Band"))
    return signals
