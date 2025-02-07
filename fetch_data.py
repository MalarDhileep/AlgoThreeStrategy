import MetaTrader5 as mt5
import pandas as pd

# logging.basicConfig(filename='trading.log', level=logging.INFO)

def log_trade_action(action, symbol, price, lot):
    logging.info(f"{action} - Symbol: {symbol}, Price: {price}, Lot: {lot}, Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

def get_atr(symbol,timeframe,atr_period):
    rates = mt5.copy_rates_from_pos(symbol,timeframe,0,atr_period+1)
    df=pd.DataFrame(rates)
    df['high_low'] =df['high'] - df['low']
    atr = df['high_low'].mean()
    return atr
    
def fetch_live_data(symbol, timeframe, count=100):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    data = pd.DataFrame(rates)
    data['time'] = pd.to_datetime(data['time'], unit='s')
    return data
    
# Fetch the current data
def fetch_live_data_pivot(symbol, timeframe, bars_to_fetch, retry_interval=10):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars_to_fetch)
    if rates is None or len(rates) < bars_to_fetch:
        print("Failed to fetch data. Retrying...")
        time.sleep(60)
        return None

    # Convert rates to a DataFrame
    data = pd.DataFrame(rates)
    data['time'] = pd.to_datetime(data['time'], unit='s')  # Convert UNIX time to datetime
    data.rename(columns={'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close'}, inplace=True)
    return data