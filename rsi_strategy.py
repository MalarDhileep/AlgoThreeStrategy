import pandas as pd
import ta

def calculate_rsi(df, window=14):
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=window).rsi()
    return df

# Function to generate trading signals based on RSI
def rsi_strategy(symbol,df):
    # timeframe = TIMEFRAME  # Use the defined global TIMEFRAME
    # count = 100  # Default count of data points to fetch
    # df = fetch_live_data(symbol, timeframe, count)
    # df = calculate_rsi(df)
    today_rsi = df["rsi"].iloc[-1]  # Latest RSI value
    
    overbuy = 70
    neutral = 50
    oversell = 30
    signals = []

    if today_rsi > neutral and today_rsi < overbuy:
        signals.append(('buy', 'RSI BUY'))
    elif today_rsi < neutral and today_rsi > oversell:
        signals.append(('sell', 'RSI SELL'))
    return signals
    # if today_rsi > overbuy:
    #     signals.append(('sell', 'RSI SELL'))
    # elif today_rsi < oversell:
    #     signals.append(('buy', 'RSI BUY'))
    # return signals