import MetaTrader5 as mt5
import logging
import time

def initialize_mt5(login, password, server):
    if not mt5.initialize(login=login, password=password, server=server):
        raise Exception(f"MetaTrader5 initialization failed. Error: {mt5.last_error()}")
        # print("MetaTrader5 initialization failed.")
        mt5.shutdown()
        quit()
    print("Connected to MetaTrader 5")

# def setup_logging():
#     logging.basicConfig(filename='trading.log', level=logging.INFO)

# def log_trade_action(action, symbol, price, lot):
#     logging.info(f"{action} - Symbol: {symbol}, Price: {price}, Lot: {lot}, Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

