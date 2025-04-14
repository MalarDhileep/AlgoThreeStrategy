import MetaTrader5 as mt5
import requests
import pandas as pd
# import ta
import time
import sys
import pytz
from datetime import datetime,timedelta

# login credentials
login = 204033390
password = "Arjun@21"
server = "Exness-MT5Trial7"
if not mt5.initialize(login=login, password=password, server=server):
    print("MetaTrader5 initialization failed.")
    mt5.shutdown()
    quit()
print("Connected to the account!")
# Variable
SYMBOL = "XAUUSDm"
LOT_SIZE = 0.01
base_lot = 0.01
MAGIC_NUMBER = 123456
TIMEFRAME = mt5.TIMEFRAME_M5
max_lots = 0.1
ATR_PERIOD = 14
LOT_INCREMENT = 0.01
CLOSE_CHECK_INTERVAL = 1
# base_lot = LOT_SIZE
current_lot_size = LOT_SIZE
buy_lot_size = 0.01
sell_lot_size = 0.01
BB_WINDOW = 20
BB_MULTIPLIER = 2
trade_log = []
previous_buy_lots = []
previous_sell_lots = []
BARS_TO_FETCH = 50
table1_profit = 20
table2_profit = 5
overall_target = 100
# second_table_base_lot=0.06
executed_conditions = set()
current_candle_time = None

TELEGRAM_BOT_TOKEN = "6959793717:AAHtVWXR6FoNOle6GtaQR17kyoU-slVQ-hI"
# TELEGRAM_CHAT_ID = "1639206560"
# GROUP_CHAT_ID = "-1002282694278"
SUBGROUP_CHAT_ID = "-1002646628247"

# Store trade details
def is_market_open():
    tick_info = mt5.symbol_info_tick(SYMBOL)
    if tick_info is None:
        print("Failed to get tick info!")
        return False

    server_timestamp = tick_info.time
    server_time = datetime.utcfromtimestamp(server_timestamp)  # Convert to UTC

    # Convert to Indian Standard Time (IST) - GMT+5:30
    ist_time = server_time + timedelta(hours=5, minutes=30)

    # Market Open: Monday 4:30 AM IST | Market Close: Saturday 3:30 AM IST
    market_open = ist_time.weekday() == 0 and ist_time.hour >= 2 and ist_time.minute >= 30
    market_close = ist_time.weekday() == 5 and ist_time.hour >= 3 and ist_time.minute >= 30

    return market_open or (0 <= ist_time.weekday() < 5 and not market_close)
# Telegram message created
def send_telegram_message(message):
    """Send trade alerts to Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": SUBGROUP_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"Telegram Error: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Telegram Message Error: {e}")


def get_atr(symbol, timeframe, atr_period):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, atr_period + 1)
    df = pd.DataFrame(rates)
    df['high_low'] = df['high'] - df['low']
    atr = df['high_low'].mean()
    return atr


def fetch_live_data(symbol, timeframe, bars_to_fetch):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars_to_fetch)
    if rates is None or len(rates) < bars_to_fetch:
        print("Failed to fetch data. Retrying...")
        # time.sleep(10)
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    latest_candle_time = df['time'].iloc[-1]
    current_time = datetime.now()
    return df


def fetch_live_data_pivot(symbol, timeframe, bars_to_fetch, retry_interval=10):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars_to_fetch)
    if rates is None or len(rates) < bars_to_fetch:
        print("Failed to fetch data. Retrying...")
        # time.sleep(60)
        return None
    data = pd.DataFrame(rates)
    data['time'] = pd.to_datetime(data['time'], unit='s')  # Convert UNIX time to datetime
    data.rename(columns={'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close'}, inplace=True)
    return data


def get_last_candle_time(symbol, timeframe):
    """Fetch the last closed candle time."""
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 1, 1)  # Get the last closed candle
    if rates is None or len(rates) == 0:
        return None
    return rates[0]['time']


def calculate_bollinger_bands(data, TIMEFRAM, window=20, std_dev=2):
    data['middle_band'] = data['close'].rolling(window=TIMEFRAM).mean()
    data['upper_band'] = data['middle_band'] + (data['close'].rolling(window=TIMEFRAM).std() * std_dev)
    data['lower_band'] = data['middle_band'] - (data['close'].rolling(window=TIMEFRAM).std() * std_dev)
    return data


def bb_strategy(df):
    if len(df) < 3:
        return []

    prev, breakout, current = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    signals = []

    if prev['close'] < prev['upper_band'] and breakout['close'] > breakout['upper_band']:
        signals.append(('buy', 'UB CrossAbove'))
    elif prev['close'] < prev['middle_band'] and breakout['close'] > breakout['middle_band']:
        signals.append(('buy', 'MB CrossAbove'))
    elif prev['close'] < prev['lower_band'] and breakout['close'] > breakout['lower_band']:
        signals.append(('buy', 'LB CrossAbove'))

    # Sell signals
    if prev['close'] > prev['upper_band'] and breakout['close'] < breakout['upper_band']:
        signals.append(('sell', 'UB CrossBelow'))
    elif prev['close'] > prev['middle_band'] and breakout['close'] < breakout['middle_band']:
        signals.append(('sell', 'MB CrossBelow'))
    elif prev['close'] > prev['lower_band'] and breakout['close'] < breakout['lower_band']:
        signals.append(('sell', 'LB CrossBelow'))
    return signals

def bb_reversal_strategy(data):
    if len(data) < 3:
        return []

    signals = []
    prev = data.iloc[-2]      # Previous candle
    current = data.iloc[-1]   # Current candle

    # ✅ Buy Conditions
    # Previous candle crosses & closes above UB/MB/LB + Current candle closes above previous high
    if (prev['close'] > prev['upper_band'] and prev['open'] <= prev['upper_band']
            and current['close'] > prev['high']):
        signals.append(('buy', 'UB HH breakout'))

    elif (prev['close'] > prev['middle_band'] and prev['open'] <= prev['middle_band']
          and current['close'] > prev['high']):
        signals.append(('buy', 'MB HH breakout'))

    elif (prev['close'] > prev['lower_band'] and prev['open'] <= prev['lower_band'] and current['close'] > prev['high']):
        signals.append(('buy', 'LB HH breakout'))

    # ✅ Sell Conditions
    # Previous candle crosses & closes below UB/MB/LB + Current candle closes below previous low
    if (prev['close'] < prev['upper_band'] and prev['open'] >= prev['upper_band'] and current['close'] < prev['low']):
        signals.append(('sell', 'UB LL breakdown'))

    elif (prev['close'] < prev['middle_band'] and prev['open'] >= prev['middle_band'] and current['close'] < prev['low']):
        signals.append(('sell', 'MB LL breakdown'))

    elif (prev['close'] < prev['lower_band'] and prev['open'] >= prev['lower_band'] and current['close'] < prev['low']):
        signals.append(('sell', 'LB LL breakdown'))

    return signals


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
        'TCPR': TC,
        'CCPR': CP,
        'BCPR': BC,
        'R1': CP + (prev_high - prev_low) * 1.1 / 4,
        'R2': CP + (prev_high - prev_low) * 1.1 / 2,
        'R3': CP + (prev_high - prev_low) * 1.1,
        'S1': CP - (prev_high - prev_low) * 1.1 / 4,
        'S2': CP - (prev_high - prev_low) * 1.1 / 2,
        'S3': CP - (prev_high - prev_low) * 1.1,
        'PDH': prev_high,
        'PDL': prev_low,
    }

    # print(f"Today Day's TC: {TC},CP: {CP}, BC: {BC}, PDH:{prev_high},PDL:{prev_low}")
    return pivot_points


def pivot_strategy(df, pivot_points):
    if not pivot_points or len(df) < 3:
        return []

    # prev, current = df.iloc[-2], df.iloc[-1]
    prev, breakout, current = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    signals = []

    # Buy signals
    for level in ['S3', 'S2', 'S1', 'TCPR','BCPR','R3', 'R2', 'R1','PDH','PDL']:
        if prev['close'] < pivot_points[level] and breakout['close'] > pivot_points[level] and current['open'] < breakout['close']:
            signals.append(('buy', f"Crossabove {level}"))

    # Sell signals
    for level in ['R3', 'R2', 'R1', 'TCPR','BCPR','S3', 'S2', 'S1','PDH','PDL']:
        if prev['close'] > pivot_points[level] and breakout['close'] < pivot_points[level] and current['open'] < breakout['close']:
            signals.append(('sell', f"Crossbelow {level}"))
    return signals

def bb_inner_reversal(df):
    if len(df) < 2:
        return []

    signals = []
    prev,current = df.iloc[-2], df.iloc[-1]
    #Buys
    if (prev['low'] < prev['lower_band'] and prev['open'] > prev['lower_band'] and prev['close'] > prev['lower_band'] and current['high'] >= prev['high']):
        signals.append(('buy', 'LB Rejection'))

    elif (prev['low'] < prev['middle_band'] and prev['open'] > prev['middle_band'] and prev['close'] > prev['middle_band'] and current['high'] >= prev['high']):
        signals.append(('buy', 'MBBuyRejection'))
    #Sell
    if (prev['high'] >prev['upper_band']  and prev['open'] < prev['upper_band'] and prev['close'] < prev['upper_band'] and current['low'] <=  prev['low']):
        signals.append(('sell', 'UB Rejection'))

    elif (prev['high'] > prev['middle_band'] and prev['open'] < prev['middle_band'] and prev['close'] < prev['middle_band'] and current['low'] <= prev['low']):
        signals.append(('sell', 'MBSellRejection'))
    return signals

def open_buy_position(symbol, magic_number, lot, comment):
    global buy_lot_size, base_lot, previous_buy_lots
    # lot = round(lot, 2)
    lot = round(float(lot), 2)
    # Add small delay
    time.sleep(1)
    price = mt5.symbol_info_tick(symbol).ask
    if price is None:
        print(f"ERROR: Failed to get price for {symbol}.")
        return None
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY,
        "price": price,
        "deviation": 50,
        "magic": magic_number,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result is None:
        print("❌ ERROR: Failed to send order. MT5 returned None.")
        print(f"Request: {request}")
        return None
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Failed to open buy position: {result.retcode}")
    else:
        entry_price = result.price
        trade_log.append({
            "Time": datetime.now(),
            "Symbol": symbol,
            "Type": mt5.ORDER_TYPE_BUY,
            "Lot": lot,
            "Entry Price": entry_price,
            "Exit Price": None,
            "Profit": None
        })
        previous_buy_lots.append(lot)
        # server_time = mt5.time()
        # server_time = result.time
        # print(f"🟢 Buy position opened | Lot: {lot} | Previous Buy Lots: {previous_buy_lots}")
        # entry_time  = datetime.fromtimestamp(result.time, pytz.timezone("Etc/UTC")).strftime('%Y-%m-%d %H:%M:%S')
        entry_time = datetime.now(pytz.timezone("Etc/UTC")).strftime('%Y-%m-%d %H:%M:%S')
        # entry_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get formatted time
        ticket_number = result.order  # Get the position ticket number
        message = (
            # f"📌 *New Trade Opened Buy*\n\n" \
            f"🟢 *Trade Alert! BUY* " \
            # f"📉 *Symbol:* {symbol}\n" \
            f"🕒 *Entry Time:* {entry_time}\n"
            f"📉 *Type: Buy *\n" \
            f"📊 *Lot Size:* {lot}\n" \
            f"🎯 *Entry Price:* {entry_price}\n" \
            # f"🔴 *Stop Loss:* {sl}\n" \
            # f"🟢 *Take Profit:* {tp}"
        )
        send_telegram_message(message)
        print(f"Buy position opened | Time: {entry_time} | Ticket ID: {ticket_number}|Price : {price},Lot: {lot}")
        previous_buy_lots.append(lot)
    return result


# Function to open a sell position
def open_sell_position(symbol, magic_number, lot, comment):
    global sell_lot_size, base_lot, previous_sell_lots
    # lot = round(lot, 2)
    lot = round(float(lot), 2)
    price = mt5.symbol_info_tick(symbol).bid
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_SELL,
        "price": price,
        "deviation": 50,
        "magic": magic_number,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result is None:
        print("❌ ERROR: Failed to send order. MT5 returned None.")
        print(f"Request: {request}")
        return None
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Failed to open sell position: {result.retcode}")
    else:
        entry_price = result.price
        trade_log.append({
            "Time": datetime.now(),
            "Symbol": symbol,
            "Type": mt5.ORDER_TYPE_SELL,
            "Lot": lot,
            "Entry Price": entry_price,
            "Exit Price": None,
            "Profit": None
        })
        previous_sell_lots.append(lot)
        entry_time = datetime.now(pytz.timezone("Etc/UTC")).strftime('%Y-%m-%d %H:%M:%S')
        ticket_number = result.order  # Get the position ticket number
        message = (
            # f"📌 *New Trade Opened Sell*\n\n" \
            f"🔴 *Trade Alert! Sell*" \
                # f"📉 *Symbol:* {symbol}\n" \
            f"🕒 *Entry Time:* {entry_time}\n"
            f"📉 *Type: Sell*\n" \
            f"📊 *Lot Size:* {lot}\n" \
            f"🎯 *Entry Price:* {entry_price}\n" \
            # f"🔴 *Stop Loss:* {sl}\n" \
            # f"🟢 *Take Profit:* {tp}"
        )
        send_telegram_message(message)
        # print(f"Sell position opened at {price}, Position {position.ticket},Lot: {lot}")
        print(f"Sell position opened | Time: {entry_time} | Ticket ID: {ticket_number}|Price : {price},Lot: {lot}")
        previous_sell_lots.append(lot)
    return result


def apply_averaging(symbol, magic_number, reason, buy_lot_size, sell_lot_size, atr_value, last_entry_time, max_lots,previous_buy_lots, previous_sell_lots):
    positions = mt5.positions_get(symbol=symbol, magic=magic_number)
    if not positions:
        return
    total_volume = 0
    avg_price = 0
    position_type = None
    last_buy_lot = base_lot
    last_sell_lot = base_lot
    current_time = time.time()
    averaging_count = 0

    if symbol not in last_entry_time:
        last_entry_time[symbol] = 0

    if current_time - last_entry_time[symbol] < 300:  # 300 seconds = 5 minutes
        return buy_lot_size, sell_lot_size

    for position in positions:
        if position.magic == magic_number:
            if position.type == mt5.POSITION_TYPE_BUY:
                last_buy_lot = max(last_buy_lot, position.volume)
                averaging_count += 1
            elif position.type == mt5.POSITION_TYPE_SELL:
                last_sell_lot = max(last_sell_lot, position.volume)
                averaging_count += 1
            avg_price = (avg_price * total_volume + position.volume * position.price_open) / (
                        total_volume + position.volume)
            total_volume += position.volume
            position_type = position.type
    current_candle_time = get_last_candle_time(symbol, mt5.TIMEFRAME_M5)
    current_price = mt5.symbol_info_tick(
        symbol).ask if position_type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(symbol).bid
    if averaging_count < 3:
        threshold_price = avg_price - (0.30 * atr_value) if position_type == mt5.POSITION_TYPE_BUY else avg_price + (
                    0.30 * atr_value)
    else:
        threshold_price = avg_price - (0.50 * atr_value) if position_type == mt5.POSITION_TYPE_BUY else avg_price + (
                    0.50 * atr_value)
    if position_type == mt5.POSITION_TYPE_BUY and current_price <= threshold_price:
        # buy_lot_size = min(max(previous_buy_lots, default=last_buy_lot) + 0.01, max_lots)
        # next_lot  = 0.1 if buy_lot_size >= max_lots else min(max(previous_buy_lots, default=last_buy_lot) + 0.01, max_lots)
        # if buy_lot_size not in previous_buy_lots:
        next_lot = 0.1 if buy_lot_size >= max_lots else min(max(previous_buy_lots or [last_buy_lot]) + 0.01, max_lots)
        if next_lot not in previous_buy_lots or next_lot == 0.1:
            open_buy_position(symbol, magic_number, next_lot, "Buy average")
            previous_buy_lots.append(next_lot)
            last_entry_time[symbol] = current_time
            print("Buy average")
        buy_lot_size = next_lot

    elif position_type == mt5.POSITION_TYPE_SELL and current_price >= threshold_price:
        # sell_lot_size = min(max(previous_sell_lots, default=last_sell_lot) + 0.01, max_lots)
        # next_lot = 0.1 if sell_lot_size >= max_lots else min(max(previous_sell_lots, default=last_sell_lot) + 0.01, max_lots)
        # if sell_lot_size not in previous_sell_lots:
        next_lot = 0.1 if sell_lot_size >= max_lots else min(max(previous_sell_lots or [last_sell_lot]) + 0.01,
                                                             max_lots)
        if next_lot not in previous_sell_lots or next_lot == 0.1:
            open_sell_position(symbol, magic_number, next_lot, "Sell average")
            previous_sell_lots.append(next_lot)
            last_entry_time[symbol] = current_time
            print("Sell average")
        sell_lot_size = next_lot
    return buy_lot_size, sell_lot_size


def close_all_positions(symbol, magic_number, overall_target, averaging_active):
    global buy_lot_size, sell_lot_size
    positions = mt5.positions_get(symbol=symbol)
    if positions is None or len(positions) == 0:
        return False
    total_profit = sum(position.profit for position in positions if position.magic == magic_number)
    closed_positions = []
    total_lot = 0

    target_profit = overall_target

    if total_profit >= overall_target:
        print(f"Target profit reached: {total_profit}. Closing all positions.")
        for position in positions:
            if position.magic == magic_number:
                action = (mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY)
                price = (mt5.symbol_info_tick(
                    symbol).bid if position.type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(symbol).ask)
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
                    trade_type = "Buy" if position.type == mt5.POSITION_TYPE_BUY else "Sell"
                    close_time = datetime.now(pytz.timezone("Etc/UTC")).strftime('%Y-%m-%d %H:%M:%S')
                    entry_price = position.price_open
                    entry_time = datetime.fromtimestamp(position.time, pytz.timezone("Etc/UTC")).strftime('%Y-%m-%d %H:%M:%S')
                    closed_positions.append(f"| {trade_type:<4} | {entry_price:<8.2f}| {position.volume:<4.2f}  | {position.profit:<8.2f} | {entry_time} |")
                    # closed_positions.append(f"| {trade_type:<4} | {position.volume:<4.2f} | {position.profit:<8.2f} | {entry_time} |")
                    total_lot += position.volume
                    # trade_type = "Buy" if position.type == mt5.POSITION_TYPE_BUY else "Sell"
                    # closed_positions.append(f"| {trade_type:<4} | {position.volume:<4.2f} | {position.profit:<8.2f} | {entry_time} |")
                    # total_lot += position.volume
        # Send Telegram alert
        if closed_positions:
            close_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S') 
            message = (
                    f"✅🚀  *Target Profit Reached: {total_profit:.2f} USD* 🚀 \n"
                    f"📉 *Symbol:* {symbol}\n\n"
                    f"🕒 *Close Time:* {close_time}\n\n"
                    f"```"  # Start of code block for monospaced formatting
                    # f"|------|----------|------|-------|-----------\n"
                    f"| Type |Entry_price| Lot  | Profit| Entry time|\n"
                    f"|------|-----------|------|-------|-----------\n"
                    + "\n".join(closed_positions) + "\n"
                    f"|-------|----------|-----|------------|\n"
                    f"| Total |           | {total_lot:.2f} | {total_profit:.2f} |              |\n"
                    f"|-------|----------|------|---------|-----------\n"
                    f"```"  # End of code block
            )
            send_telegram_message(message)
        return True
    return False


def get_first_table_positions():
    positions = mt5.positions_get(symbol=SYMBOL)
    first_table = []

    if positions:
        for pos in positions:
            lot_size = round_lot_size(pos.volume)
            if lot_size <= 0.05:  # First Table Condition
                first_table.append(pos)
    return first_table


def get_second_table_positions():
    positions = mt5.positions_get(symbol=SYMBOL)
    second_table = []
    min_entry_price_0_05 = None
    has_0_05_lot = False
    second_table_active = False
    max_lot_reached = False

    if positions:
        for pos in positions:
            lot_size = round_lot_size(pos.volume)
            if lot_size >= max_lots:
                max_lot_reached = True
            if lot_size > 0.05:
                second_table.append(pos)
                second_table_active = True
            if lot_size == 0.05:
                has_0_05_lot = True
                if min_entry_price_0_05 is None:
                    min_entry_price_0_05 = pos.price_open
                else:
                    min_entry_price_0_05 = min(min_entry_price_0_05, pos.price_open)

    entry_price_0_05 = min_entry_price_0_05 if has_0_05_lot else None
    return second_table, has_0_05_lot, entry_price_0_05, second_table_active, max_lot_reached


def get_current_running_lots(symbol, magic_number):
    positions = mt5.positions_get(symbol=symbol, magic=magic_number)
    buy_lots = []
    sell_lots = []

    if positions:
        for pos in positions:
            if pos.type == mt5.POSITION_TYPE_BUY:
                buy_lots.append(round(pos.volume, 2))
            elif pos.type == mt5.POSITION_TYPE_SELL:
                sell_lots.append(round(pos.volume, 2))
    return buy_lots, sell_lots


def round_lot_size(volume):
    return round(volume, 2)


def get_next_lot_size(current_lots, max_lots,base_lot):
    if not current_lots:
        return base_lot

    max_current_lot = max(current_lots)
    # next_lot = round_lot_size(max_current_lot + LOT_INCREMENT,2)
    next_lot = round(max_current_lot + LOT_INCREMENT, 2)
    return min(next_lot, max_lots)


def check_and_close_trades(SYMBOL, table1_profit, table2_profit):
    global second_table_closed, buy_lot_size, sell_lot_size

    first_table = get_first_table_positions()
    second_table, has_0_05_lot, entry_price_0_05, second_table_active, max_lot_reached = get_second_table_positions()

    first_table_profit = sum(pos.profit for pos in first_table)
    second_table_profit = sum(pos.profit for pos in second_table)
    current_price = mt5.symbol_info_tick(SYMBOL).ask

    closed_positions = []
    total_profit, total_lot = 0, 0
    table_name = None
    #Condition 1: Close Second Table with single 0.05 lot and profit ≥ $5
    if second_table and has_0_05_lot and round(current_price, 0) == round(entry_price_0_05, 0) and second_table_profit >= table2_profit:
        close_time = datetime.now(pytz.timezone("Etc/UTC")).strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n🚀 Closing Second Table -Profit: {second_table_profit:.2f} | 0.05 Entry price:{entry_price_0_05}| Time: {close_time}")
        close_positions(second_table, "Second Table")
        table_name = "Second Table"

        for pos in second_table:
            # trade_type = "BUY" if pos.type == 0 else "SELL"
            # entry_time = datetime.fromtimestamp(pos.time).strftime('%Y-%m-%d %H:%M:%S')
            # closed_positions.append(f"| {trade_type:<5} | {pos.volume:.2f} | {pos.profit:.2f} | {entry_time} |")
            total_profit += pos.profit
            total_lot += round_lot_size(pos.volume)
            trade_type = "Buy" if pos.type == mt5.POSITION_TYPE_BUY else "Sell"
            close_time = datetime.now(pytz.timezone("Etc/UTC")).strftime('%Y-%m-%d %H:%M:%S')
            entry_price = pos.price_open
            entry_time = datetime.fromtimestamp(pos.time, pytz.timezone("Etc/UTC")).strftime('%Y-%m-%d %H:%M:%S')
            closed_positions.append(f"| {trade_type:<4} | {entry_price:<8.2f}| {pos.volume:<4.2f}  | {pos.profit:<8.2f} | {entry_time} |")
            # closed_positions.append(f"| {trade_type:<4} | {position.volume:<4.2f} | {position.profit:<8.2f} | {entry_time} |")
            # total_lot += position.volume

        second_table_closed = True
        time.sleep(2)

        # ✅ Update lot sizes after closing Second Table
        buy_lots, sell_lots = get_current_running_lots(SYMBOL, MAGIC_NUMBER)
        previous_buy_lots.clear()
        previous_sell_lots.clear()
        previous_buy_lots.extend(buy_lots)
        previous_sell_lots.extend(sell_lots)

        # Calculate next lot sizes
        buy_lot_size = get_next_lot_size(buy_lots, max_lots, base_lot)
        sell_lot_size = get_next_lot_size(sell_lots, max_lots, base_lot)

        # ✅ Refresh First Table positions
        first_table = get_first_table_positions()
        first_table_profit = sum(pos.profit for pos in first_table)

        # ✅ Close First Table if profit ≥ $1
        if first_table_profit >= table1_profit:
            close_time = datetime.now(pytz.timezone("Etc/UTC")).strftime('%Y-%m-%d %H:%M:%S')
            print(
                f"\n🚀 Closing First Table - Profit: {first_table_profit:.2f} | Time: {close_time}")
            close_positions(first_table, "First Table")
            table_name = "First Table"

            for pos in first_table:
                # trade_type = "BUY" if pos.type == 0 else "SELL"
                # entry_time = datetime.now(pytz.timezone("Etc/UTC")).strftime('%Y-%m-%d %H:%M:%S')
                # closed_positions.append(f"| {trade_type:<5} | {pos.volume:.2f} | {pos.profit:.2f} | {entry_time} |")
                total_profit += pos.profit
                total_lot += round_lot_size(pos.volume)
                trade_type = "Buy" if pos.type == mt5.POSITION_TYPE_BUY else "Sell"
                close_time = datetime.now(pytz.timezone("Etc/UTC")).strftime('%Y-%m-%d %H:%M:%S')
                entry_price = pos.price_open
                entry_time = datetime.fromtimestamp(pos.time, pytz.timezone("Etc/UTC")).strftime('%Y-%m-%d %H:%M:%S')
                closed_positions.append(f"| {trade_type:<4} | {entry_price:<8.2f}| {pos.volume:<4.2f}  | {pos.profit:<8.2f} | {entry_time} |")
            reset_lot_size()

    #Condition 2: Close First Table if Second Table is empty and profit ≥ $1
    elif not second_table and first_table_profit >= table1_profit:
        close_time = datetime.now(pytz.timezone("Etc/UTC")).strftime('%Y-%m-%d %H:%M:%S')
        print(
            f"\n🚀 Closing First Table - Profit: {first_table_profit:.2f} | Time: {close_time}")
        close_positions(first_table, "First Table")
        table_name = "First Table"

        for pos in first_table:
            # trade_type = "BUY" if pos.type == 0 else "SELL"
            # entry_time = datetime.now(pytz.timezone("Etc/UTC")).strftime('%Y-%m-%d %H:%M:%S')
            # # entry_time = datetime.fromtimestamp(pos.time).strftime('%Y-%m-%d %H:%M:%S')
            # closed_positions.append(f"| {trade_type:<5} | {pos.volume:.2f} | {pos.profit:.2f} | {entry_time} |")
            total_profit += pos.profit
            total_lot += round_lot_size(pos.volume)
            trade_type = "Buy" if pos.type == mt5.POSITION_TYPE_BUY else "Sell"
            close_time = datetime.now(pytz.timezone("Etc/UTC")).strftime('%Y-%m-%d %H:%M:%S')
            entry_price = pos.price_open
            entry_time = datetime.fromtimestamp(pos.time, pytz.timezone("Etc/UTC")).strftime('%Y-%m-%d %H:%M:%S')
            closed_positions.append(f"| {trade_type:<4} | {entry_price:<8.2f}| {pos.volume:<4.2f}  | {pos.profit:<8.2f} | {entry_time} |")
        reset_lot_size()
        # print("All trades closed. Restarting the program.")
        # python = sys.executable
        # subprocess.run([python, sys.argv[0]])

    # ✅ Send Telegram message with the closed positions
    if closed_positions:
        message = (
                f"✅🚀  *{table_name} Closed - Target Profit Reached! {total_profit:.2f}* 🚀\n"
                f"📉 *Symbol:* {SYMBOL}\n\n"
                f"🕒 *Close Time:* {close_time}\n\n"
                f"```"
                f"|------|-----------|------|------|-----------|\n"
                f"| Type |Entry_price| Lot  |Profit| Entry time|\n"
                f"|------|-----------|------|------|-----------|\n"
                + "\n".join(closed_positions) + "\n"
                f"|------|-----------|------|------|-----------|\n"
                f"| Total|           | {total_lot:.2f} | {total_profit:.2f} |          |\n"
                f"|------|-----------|------|------|-----------|\n"
                f"```"
        )
        send_telegram_message(message)


def close_positions(trades, table_name):
    closed_positions = []
    total_profit, total_lot = 0, 0

    for pos in trades:
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
            "position": pos.ticket,
            "volume": pos.volume,
            "type": mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY,  # Close opposite
            "price": mt5.symbol_info_tick(pos.symbol).bid if pos.type == 0 else mt5.symbol_info_tick(pos.symbol).ask,
            "deviation": 10,
            "magic": pos.magic,
            "comment": "Auto close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Failed to close position {pos.ticket}, Error Code: {result.retcode}, Message: {result.comment}")
            continue  # Move to next trade instead of stopping

        trade_type = "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL"
        closed_positions.append(f"| {trade_type:<5} | {pos.volume:.2f} | {pos.profit:.2f} |")
        total_profit += pos.profit
        total_lot += round_lot_size(pos.volume)
        print(f"{table_name} closed: Ticket {pos.ticket}, Volume {pos.volume}, Profit {pos.profit}")
    return closed_positions, total_profit, total_lot


def reset_lot_size():
    global buy_lot_size, sell_lot_size, previous_buy_lots, previous_sell_lots, base_lot
    buy_lot_size = base_lot
    sell_lot_size = base_lot
    previous_buy_lots.clear()
    previous_sell_lots.clear()
    print("Lot sizes reset to base:", base_lot)


# next_lot_size = get_next_second_table_lot()
# print(f"Next Second Table Lot Size: {next_lot_size}")

def get_lot_size(order_type):
    global buy_lot_size, sell_lot_size
    if order_type.lower() == 'buy':
        return round(buy_lot_size, 2)
    elif order_type.lower() == 'sell':
        return round(sell_lot_size, 2)
    else:
        reset_lot_size()
        return 0.01


def process_signals(symbol, timeframe, signals, buy_lot_size, sell_lot_size):
    global executed_conditions, current_candle_time

    # Get current candle time and check if new candle
    # new_candle_time = get_last_candle_time(symbol, timeframe)
    # if new_candle_time != current_candle_time:
    #     executed_conditions.clear()
    #     current_candle_time = new_candle_time
    #     print(f"🕒 New candle detected at {datetime.fromtimestamp(current_candle_time)}")

    # Process all signals
    for direction, reason in signals:
        if reason not in executed_conditions:
           lot_size = get_lot_size(direction)
           if direction == 'buy' and buy_lot_size <= max_lots:
              if open_buy_position(SYMBOL, MAGIC_NUMBER, buy_lot_size, reason):
                 previous_buy_lots.append(buy_lot_size)
                 print(f"Buy entry opened: Lot size = {buy_lot_size}, Reason: {reason}")
                 executed_conditions.add(reason)
              else:
                 print(f"❌ Buy entry FAILED - Lot: {lot_size}, Reason: {reason}")

           if direction == 'sell' and sell_lot_size <= max_lots:
              if open_sell_position(SYMBOL, MAGIC_NUMBER, sell_lot_size, reason):
                 previous_sell_lots.append(sell_lot_size)
                 print(f"Sell entry opened: Lot size = {sell_lot_size}, Reason: {reason}")
                 executed_conditions.add(reason)
              else:
                 print(f"❌ Sll entry FAILED - Lot: {lot_size}, Reason: {reason}")
           # executed_conditions.clear()
           # executed_conditions.add(reason)
           time.sleep(1)

def main():
    global buy_lot_size, sell_lot_size, current_candle_time, executed_conditions
    reason = "Start reason"
    buy_lot_size = base_lot
    sell_lot_size = base_lot
    symbol = SYMBOL
    last_checked_time = datetime.now()

    executed_conditions = set()
    current_candle_time = None
    atr_value = get_atr(SYMBOL, TIMEFRAME, ATR_PERIOD)

    averaging_active = False
    last_entry_time = {}
    previous_buy_lots = []
    previous_sell_lots = []
    last_candle_time = None
    signals = []
    last_bb_candle_time = None
    last_checked_time = datetime.now()
    while True:
        if not is_market_open():
            time.sleep(60)
            continue

        # 4. Fetch Data
        data = fetch_live_data(SYMBOL, TIMEFRAME, BARS_TO_FETCH)
        data_pivot = fetch_live_data_pivot(SYMBOL, TIMEFRAME, BARS_TO_FETCH)
        data_bb = fetch_live_data(SYMBOL, TIMEFRAME, BB_WINDOW + 3)
        if data_bb is None or data_pivot is None:
            time.sleep(1)
            continue

        # 5. Calculate Indicators
        data_bb = calculate_bollinger_bands(data_bb, BB_WINDOW, BB_MULTIPLIER)
        pivot_points = calculate_pivot_points(SYMBOL)

        candle_time = get_last_candle_time(SYMBOL, TIMEFRAME)

        new_candle_time = get_last_candle_time(SYMBOL, TIMEFRAME)

        if new_candle_time != current_candle_time:
           current_candle_time = new_candle_time
           check_time = datetime.now(pytz.timezone("Etc/UTC")).strftime('%Y-%m-%d %H:%M:%S')
           print(f"🕒 New candle detected at {check_time}")
        #    print(f"🕒 New candle detected at {datetime.fromtimestamp(current_candle_time)}")
           process_signals(SYMBOL, TIMEFRAME, signals, buy_lot_size, sell_lot_size)
           executed_conditions.clear()

        # if candle_time != last_candle_time:
        #     print(f"New Candle: {candle_time}")
        #     last_candle_time = candle_time

        current_time = datetime.now()
        if (current_time - last_checked_time).seconds >= 60:
            # print("60-second continuous signal check at{current_time}")
            signals = []
            # last_checked_time = current_time
            signals.extend(bb_strategy(data_bb))
            signals.extend(pivot_strategy(data_pivot, pivot_points))
            signals.extend(bb_reversal_strategy(data_bb))
            signals.extend(bb_inner_reversal(data_bb))

            process_signals(SYMBOL, TIMEFRAME, signals, buy_lot_size, sell_lot_size)

            buy_lots, sell_lots = get_current_running_lots(SYMBOL, MAGIC_NUMBER)
            # Calculate next lot sizes
            buy_lot_size = get_next_lot_size(buy_lots, max_lots,base_lot)
            sell_lot_size = get_next_lot_size(sell_lots, max_lots,base_lot)
            previous_buy_lots = buy_lots
            previous_sell_lots = sell_lots

            positions = mt5.positions_get(symbol=SYMBOL, magic=MAGIC_NUMBER)
            if positions is None or len(positions) == 0:
                buy_lot_size = base_lot
                sell_lot_size = base_lot
                previous_buy_lots.clear()
                previous_sell_lots.clear()
            #Signal base entry

        apply_averaging(SYMBOL, MAGIC_NUMBER, reason, buy_lot_size, sell_lot_size, atr_value, last_entry_time, max_lots,
                        previous_buy_lots, previous_sell_lots)
        if not averaging_active:
            averaging_active = True
        check_and_close_trades(SYMBOL, table1_profit, table2_profit)
        if close_all_positions(SYMBOL, MAGIC_NUMBER, overall_target, averaging_active):
            averaging_active = False
            buy_lot_size = base_lot
            sell_lot_size = base_lot
            print("Resetting lot sizes")
            # print("All trades closed. Restarting the program.")
            # python = sys.executable
            # subprocess.run([python, sys.argv[0]])
        time.sleep(1)


# Run the main function
main()
# Shutdown MetaTrader 5 after finishing
mt5.shutdown()