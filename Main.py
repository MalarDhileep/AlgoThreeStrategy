import MetaTrader5 as mt5
import time
import sys
print('Adding path:', 'D:\Jupyter\Algo PY')
sys.path.append('D:\Jupyter\Algo PY') 

# from initialization import initialize_mt5,setup_logging, log_trade_action
from fetch_data import get_atr,fetch_live_data,fetch_live_data_pivot
from bolliger_bands import calculate_bollinger_bands,bb_strategy
from rsi_strategy import calculate_rsi,rsi_strategy
from pivot import calculate_pivot_points,pivot_strategy
from position_entry import open_buy_position, open_sell_position
from new_averaging import apply_averaging
from closure import close_all_positions

# Account credentials
login = 189667611
password = "Malar@96"
server = "Exness-MT5Trial14"

# initialize_mt5(login, password, server)
# setup_logging()

# # Initialize connection
if not mt5.initialize(login=login, password=password, server=server):
    print("MetaTrader5 initialization failed.")
    mt5.shutdown()
    quit()
print("Connected to the account!")

SYMBOL = "XAUUSDm"
LOT_SIZE = 0.01
MAGIC_NUMBER = 123
TIMEFRAME = mt5.TIMEFRAME_M5
TAKE_PROFIT_AMOUNT = 1 
max_lots = 0.1 
ATR_PERIOD=14
CLOSE_CHECK_INTERVAL = 1 
base_lot = LOT_SIZE
current_lot_size = LOT_SIZE
buy_lot_size = LOT_SIZE
sell_lot_size = LOT_SIZE
BB_WINDOW = 20  
BB_MULTIPLIER = 2
# last_entry_time = {}
TIMEFRAME_BB = mt5.TIMEFRAME_M5
TIMEFRAME_RSI = mt5.TIMEFRAME_H1
ORDER_INTERVAL = 300  #5 min once take entry
RSI_INTERVAL = 3600   #15 min once take entry

def main():
    global buy_lot_size, sell_lot_size
    # initialize_mt5(login, password, server)
    base_lot = LOT_SIZE
    last_entry_time = {}
    atr_value=get_atr(SYMBOL,TIMEFRAME_BB,ATR_PERIOD)
    # last_order_time = time.time()
    averaging_active = False  
    initial_target = 5  
    overall_target = 1 
    last_bb_time = 0
    last_rsi_time = 0
    while True:
        current_time = time.time()
        positions = mt5.positions_get(symbol=SYMBOL, magic=MAGIC_NUMBER)
        if positions is None or len(positions) == 0:
                buy_lot_size = base_lot
                sell_lot_size = base_lot
                # averaging_active = False
        if current_time - last_bb_time >= ORDER_INTERVAL:
            data_bb = fetch_live_data(SYMBOL, TIMEFRAME_BB, count=BB_WINDOW + 2)
            data_bb = calculate_bollinger_bands(data_bb, BB_WINDOW, BB_MULTIPLIER)
            bb_signals = bb_strategy(data_bb)
            #pivot 
            pivot_points = calculate_pivot_points(SYMBOL)
            data = fetch_live_data_pivot(SYMBOL, TIMEFRAME_BB , 15)
            if data is None:
                continue
            pivot_signals = pivot_strategy(data, pivot_points)
            combined_signals = bb_signals + pivot_signals
            #BB entry   
            for direction, reason in combined_signals:
                if direction == 'buy' and buy_lot_size <= max_lots:
                    if open_buy_position(SYMBOL, buy_lot_size, MAGIC_NUMBER):
                       print(f"Buy entry opened: Lot size = {buy_lot_size}, Reason: {reason}")
                       buy_lot_size += base_lot
                elif direction == 'sell' and sell_lot_size <= max_lots:
                    if open_sell_position(SYMBOL, sell_lot_size, MAGIC_NUMBER):
                       print(f"Sell entry opened: Lot size = {sell_lot_size}, Reason: {reason}")
                       sell_lot_size += base_lot
            last_bb_time = current_time         
        #rsi
        if current_time - last_rsi_time >= RSI_INTERVAL:
            data_rsi = fetch_live_data(SYMBOL, TIMEFRAME_RSI, count=100)
            data_rsi = calculate_rsi(data_rsi)
            rsi_signals = rsi_strategy(SYMBOL, data_rsi)
            #RSI Entry
            for direction, reason in rsi_signals:
                if direction == 'buy' and buy_lot_size <= max_lots:
                    if open_buy_position(SYMBOL, buy_lot_size, MAGIC_NUMBER):
                       print(f"Buy entry opened: Lot size = {buy_lot_size}, Reason: {reason}")
                       buy_lot_size += base_lot
                elif direction == 'sell' and sell_lot_size <= max_lots:
                    if open_sell_position(SYMBOL, sell_lot_size, MAGIC_NUMBER):
                       print(f"Sell entry opened: Lot size = {sell_lot_size}, Reason: {reason}")
                       sell_lot_size += base_lot
            last_rsi_time = current_time     
        
        # Apply averaging strategy
        apply_averaging(SYMBOL, MAGIC_NUMBER, base_lot, atr_value, last_entry_time, max_lots)
        if not averaging_active:
           averaging_active = True
        
        # profit_target = overall_target if averaging_active else initial_target
        if close_all_positions(SYMBOL, MAGIC_NUMBER, initial_target, overall_target,  averaging_active):
            averaging_active = False
            buy_lot_size  = base_lot    
            sell_lot_size = base_lot
            print("Resetting lot sizes")
        time.sleep(CLOSE_CHECK_INTERVAL) 

# Run the main function
main()
# Shutdown MetaTrader 5 after finishing
mt5.shutdown() 
