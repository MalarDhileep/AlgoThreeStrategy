import MetaTrader5 as mt5

# Modify close_all_positions to reset the lot size
def close_all_positions(symbol, magic_number, initial_target, overall_target, averaging_active):
    global buy_lot_size, sell_lot_size 
    positions = mt5.positions_get(symbol=symbol)
    if positions is None or len(positions) == 0:
        return False
    total_profit = sum(position.profit for position in positions if position.magic == magic_number)
    
    # Set the appropriate target based on the averaging status
    target_profit = overall_target if initial_target else averaging_active 

    if total_profit >=  overall_target:
       print(f"Target profit reached: {total_profit}. Closing all positions.")
       for position in positions:
           if position.magic == magic_number:
              action = (mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY)
              price = (mt5.symbol_info_tick(symbol).bid if position.type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(symbol).ask)
              close_request = {
                 "action": mt5.TRADE_ACTION_DEAL,
                 "position": position.ticket,
                 "symbol": symbol,
                 "volume": position.volume,
                 "type": action,
                 "price": price,
                 "deviation": 20,
                 "magic": magic_number,
                 "comment": "Closing position",
                 "type_time": mt5.ORDER_TIME_GTC,
                 "type_filling": mt5.ORDER_FILLING_IOC,
              }
              # Send the close order
              result = mt5.order_send(close_request)
              if result.retcode != mt5.TRADE_RETCODE_DONE:
                 print(f"Failed to close position {position.ticket}, retcode: {result.retcode}")
              else:
                 print(f"Position {position.ticket} closed successfully.")
       return True
    return False