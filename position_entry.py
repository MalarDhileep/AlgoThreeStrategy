import MetaTrader5 as mt5

# Function to open a buy position
def open_buy_position(symbol, lot, magic_number):
    price = mt5.symbol_info_tick(symbol).ask
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY,
        "price": price,
        "deviation": 20,
        "magic": magic_number,
        "comment": "Python script buy",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
        # "type_filling": mt5.ORDER_FILLING_RETURN
    }
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Failed to open buy position: {result.retcode}")
    else:
        print(f"Buy position opened at {price}, Lot: {lot}")
    return result

# Function to open a sell position
def open_sell_position(symbol, lot, magic_number):
    price = mt5.symbol_info_tick(symbol).bid
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_SELL,
        "price": price,
        "deviation": 20,
        "magic": magic_number,
        "comment": "Python script sell",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Failed to open sell position: {result.retcode}")
    else:
        print(f"Sell position opened at {price}, Lot: {lot}")
    return result
