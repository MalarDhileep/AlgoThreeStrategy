import MetaTrader5 as mt5
from position_entry import open_buy_position, open_sell_position
import time
def apply_averaging(symbol, magic_number,base_lot,atr_value,last_entry_time, max_lots):
# def apply_averaging(symbol, magic_number,base_lot,atr_value):
   #  global last_entry_time
    positions = mt5.positions_get(symbol=symbol,magic=magic_number)
    total_volume = 0
    avg_price = 0
    position_type = None
    current_lot_size = base_lot 
    if symbol not in last_entry_time:
        last_entry_time[symbol] = 0
        
    # Calculate average price and total volume
    for position in positions:
        if position.magic == magic_number:
            position_type = position.type
            avg_price = (avg_price * total_volume + position.volume * position.price_open) / (total_volume + position.volume)
            total_volume += position.volume
            current_lot_size = position.volume  # Update current lot size based on the last position

      # Averaging logic: add a new position if price moves against us by 0.30 ATR
    if position_type is not None:
        current_price = mt5.symbol_info_tick(symbol).bid if position_type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(symbol).ask
        threshold_price = avg_price - 0.20 * atr_value if position_type == mt5.POSITION_TYPE_BUY else avg_price + 0.20 * atr_value
        # Check if 5 minutes have passed since the last entry
        current_time = time.time()
        time_since_last_entry = current_time - last_entry_time[symbol]

        if time_since_last_entry >= 300:
           if current_lot_size > max_lots:
              current_lot_size = max_lots
           # Open additional positions with increased lot size
           if position_type == mt5.POSITION_TYPE_BUY and current_price <= threshold_price:
              buy_lot_size =current_lot_size+ 0.01
              open_buy_position(symbol, buy_lot_size, magic_number)
              last_entry_time[symbol] = current_time
              print("Buy average")
           elif position_type == mt5.POSITION_TYPE_SELL and current_price >= threshold_price:
              sell_lot_size =current_lot_size+0.01
              open_sell_position(symbol, sell_lot_size, magic_number)
              last_entry_time[symbol] = current_time
              print("Sell average")



# import MetaTrader5 as mt5
# from position_entry import open_buy_position, open_sell_position
# import time
# def apply_averaging(symbol, magic_number,base_lot,atr_value,last_entry_time, max_lots):
#     if symbol not in last_entry_time or last_entry_time[symbol] is None:
#        last_entry_time[symbol] = 0 

#     positions = mt5.positions_get(symbol=symbol,magic=magic_number)

#     # Check if positions_get returned None (meaning no open positions)
#     if positions is None:
#         print(f"No open positions found for {symbol} with magic number {magic_number}")
#         return  # Exit function if no positions exist
    
#     total_volume = 0
#     avg_price = 0
#     position_type = None
#     current_lot_size = base_lot 
#    #  if symbol not in last_entry_time:
#    #      last_entry_time[symbol] = 0
        
#     # Calculate average price and total volume
#     for position in positions:
#       #   if position.magic == magic_number:
#          position_type = position.type
#          avg_price = (avg_price * total_volume + position.volume * position.price_open) / (total_volume + position.volume)
#          total_volume += position.volume
#          current_lot_size = position.volume  # Update current lot size based on the last position

#       # Averaging logic: add a new position if price moves against us by 0.30 ATR
#     if position_type is not None:
#         current_price = mt5.symbol_info_tick(symbol).bid if position_type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(symbol).ask
#         threshold_price = avg_price - 0.20 * atr_value if position_type == mt5.POSITION_TYPE_BUY else avg_price + 0.20 * atr_value
       
#         current_time = time.time()
#         time_since_last_entry = current_time - last_entry_time[symbol]

#         if time_since_last_entry >= 300:
#            if current_lot_size > max_lots:
#               current_lot_size = max_lots

#            if position_type == mt5.POSITION_TYPE_BUY and current_price <= threshold_price:
#               buy_lot_size =current_lot_size+ 0.01
#               open_buy_position(symbol, buy_lot_size, magic_number)
#               last_entry_time[symbol] = current_time
#               print("Buy average")
#            elif position_type == mt5.POSITION_TYPE_SELL and current_price >= threshold_price:
#               sell_lot_size =current_lot_size+0.01
#               open_sell_position(symbol, sell_lot_size, magic_number)
#               last_entry_time[symbol] = current_time
#               print("Sell average")