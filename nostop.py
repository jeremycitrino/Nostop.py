#!/usr/bin/env python
# nostop.py – Optimised REST Polling + Foreground Service
# Uses yfinance with caching, reduced frequency, and Android keep‑alive.

import os, sys, json, time, threading, random, webbrowser, signal, shutil, traceback, socket, subprocess, urllib.request, gc
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import atexit

try:
    import yfinance as yf
except ImportError:
    os.system('pip install yfinance')
    import yfinance as yf

# ===============================
#  CONFIGURATION
# ===============================

WR_FILE = "wr_cache.json"
HISTORY_FILE = "trade_history.json"
POSITIONS_FILE = "positions_cache.json"
CASH_FILE = "cash_cache.json"
METRICS_FILE = "metrics_history.json"
SESSION_FILE = "session_state.json"
CONFIG_FILE = "config.json"
WATCHLIST_FILE = "watchlist.json"
PID_FILE = "bot.pid"
LOG_FILE = "bot.log"

cfg = {
    'base_size': 0.08,
    'reserve': 0.10,
    'base_tp': 0.0888,
    'base_sl': 0.03,
    'max_pos': 50,
    'max_buys': 10,
    'min_trade': 2.0,
    'min_hold_hours': 8,
    'trailing_stop_pct': 0.0666,
    'heartbeat_interval': 30,
    'auto_restart': True,
    'build': True,
    'build_factor': 0.5,
    'pyramid_threshold': 5.0,
    'pyramid_size': 0.30,
    'max_pyramids': 999,
    'max_builds': 999,
    'build_trigger_pct': 2.5,
    'wr_extreme': 0.85,
    'wr_very_high': 0.75,
    'wr_high': 0.65,
    'wr_low': 0.45,
    'tp_extreme': 1.30,
    'tp_very_high': 1.20,
    'tp_high': 1.15,
    'tp_low': 0.90,
    'size_extreme': 1.25,
    'size_very_high': 1.20,
    'size_high': 1.15,
    'size_low': 0.90,
    'vix_high_tp': 1.10,
    'vix_elevated_tp': 1.05,
    'sl_low': 1.10,
    'vix_high_sl': 1.20,
    'vix_elevated_sl': 1.05,
    'vix_high_size': 1.20,
    'vix_elevated_size': 1.05,
    'vix_low_size': 0.95,
    'vix_high': 25,
    'vix_elevated': 18,
    'max_consecutive_losses': 3,
    'loss_streak_cooldown': 8,
    'circuit_breaker_enabled': False,
    'scan_size': 60,
    'extreme_dip': 8.0,
    'normal_dip': 3.0,
    'high_vix_reduction': 0.5,
    'dip_vix_critical': 8.0,
    'dip_vix_high': 6.0,
    'dip_vix_elevated': 5.0,
    'dip_vix_moderate': 4.0,
    'dip_vix_low': 3.0,
    'static_stop_loss_enabled': False,
    'trailing_only_after_pyramid': True,
}

# ===============================
#  DEFAULT WATCHLIST
# ===============================

DEFAULT_WATCHLIST = [
    'AAPL','MSFT','GOOGL','AMZN','NVDA','META','TSLA','NFLX','ADBE','CRM',
    'ORCL','IBM','CSCO','INTC','AMD','QCOM','TXN','AVGO','MU','PYPL',
    'PANW','CRWD','SNOW','PLTR','ADSK','ANET','CDNS','SNPS','NXPI','MCHP',
    'WDAY','VEEV','CTSH','INFY','DELL','HPQ','HPE','NTAP','STX','WDC',
    'SMCI','MRVL','ON','ADI','LRCX','KLAC','MDB','TEAM','NET','ZS',
    'JPM','BAC','WFC','C','GS','MS','AXP','V','MA','COF',
    'DFS','SCHW','BLK','BK','STT','TROW','AMP','RF','HBAN','KEY',
    'FITB','MTB','PNC','USB','ALLY','SOFI','AFRM','UPST','LC','LNC',
    'MET','PRU','AIG','ALL','TRV','PGR','CB','ZION','CFG','EWBC',
    'JNJ','UNH','PFE','MRK','ABBV','ABT','TMO','DHR','LLY','BMY',
    'GILD','AMGN','CVS','CI','HUM','MDT','ISRG','SYK','BSX','ZTS',
    'REGN','VRTX','BIIB','ILMN','IQV','WST','COO','HCA','UHS','BDX',
    'RMD','IDXX','MTD','WAT','BAX','STE','HOLX','ALGN','DGX','DVA',
    'BIO','TECH','XRAY','INCY','EXEL','HALO','IONS','ARWR','QDEL','MYGN',
    'WMT','COST','HD','MCD','NKE','SBUX','TGT','LOW','TJX','ROST',
    'DG','DLTR','KR','EL','PG','KO','PEP','GIS','KHC','MDLZ',
    'CL','CLX','KMB','CHD','TAP','STZ','MNST','PM','MO','BTI',
    'UL','NVS','SNY','GSK','AZN','DEO','KDP','SYY','MCK','ADM',
    'CAT','GE','BA','MMM','HON','LMT','RTX','NOC','GD','DE',
    'PCAR','CMI','ITW','EMR','ETN','ROK','DOV','PH','IR','JCI',
    'TT','OTIS','CARR','WAB','UNP','CSX','NSC','FDX','UPS','ODFL',
    'LSTR','EXPD','CHRW','JBHT','GWW','FAST','MSM','TXT','HII','CW',
    'XOM','CVX','COP','EOG','OXY','SLB','HAL','BKR','VLO','MPC',
    'PSX','KMI','WMB','OKE','LNG','DVN','HES','MRO','APA','FANG',
    'CTRA','EQT','RRC','CHK','SWN','AR','CRK','MUR','SM','MTDR',
    'SPY','QQQ','IWM','DIA','VT','VTI','VOO','IVV','BND','AGG',
    'TLT','LQD','GLD','SLV','USO','XLK','XLF','XLE','XLV','XLI',
    'PLD','AMT','CCI','EQIX','PSA','WELL','SPG','O','DLR','AVB',
    'T','VZ','TMUS','CHTR','CMCSA','DIS','WBD','PARA','FOXA','LYV',
    'NEE','DUK','SO','D','AEP','EXC','SRE','XEL','WEC','PPL'
]

WATCHLIST = DEFAULT_WATCHLIST.copy()

# ===============================
#  LOGGING SYSTEM
# ===============================

class Logger:
    def __init__(self, log_file=LOG_FILE):
        self.log_file = log_file
        self.console_output = True
    def log(self, message, level="INFO"):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"[{ts}] [{level}] {message}\n")
        except: pass
        if self.console_output: print(f"[{ts}] [{level}] {message}")
    def info(self, msg): self.log(msg, "INFO")
    def error(self, msg): self.log(msg, "ERROR")
    def warning(self, msg): self.log(msg, "WARNING")

logger = Logger()

# ===============================
#  GLOBAL STATE
# ===============================

running = True
trading = True
cash = 1000.0
positions = {}
buy_time = {}
trailing_state = {}
wins = 0
losses = 0
trade_history = []
session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
start_time = datetime.now().isoformat()
start_timestamp = time.time()
cur_size = cfg['base_size']
buy_list = []
scan_num = 0
metrics_history = []
loss_streak = 0
trading_paused = False
pause_end_time = 0
price_data = {}
vix_value = 15.0
vix_timestamp = 0
scan_index = 0

# ===============================
#  WATCHLIST PERSISTENCE
# ===============================

def save_watchlist():
    global WATCHLIST
    try:
        with open(WATCHLIST_FILE, 'w') as f:
            json.dump(WATCHLIST, f, indent=2)
        logger.info(f"Watchlist saved: {len(WATCHLIST)} symbols")
    except Exception as e:
        logger.error(f"Error saving watchlist: {e}")

def load_watchlist():
    global WATCHLIST
    try:
        with open(WATCHLIST_FILE, 'r') as f:
            loaded = json.load(f)
            if isinstance(loaded, list) and len(loaded) > 0:
                WATCHLIST = loaded
                logger.info(f"Watchlist loaded: {len(WATCHLIST)} symbols")
            else:
                WATCHLIST = DEFAULT_WATCHLIST.copy()
                logger.info("Using default watchlist")
    except FileNotFoundError:
        WATCHLIST = DEFAULT_WATCHLIST.copy()
        save_watchlist()
        logger.info("Created default watchlist")
    except Exception as e:
        logger.error(f"Error loading watchlist: {e}")
        WATCHLIST = DEFAULT_WATCHLIST.copy()

def reset_watchlist():
    global WATCHLIST, scan_index
    WATCHLIST = DEFAULT_WATCHLIST.copy()
    scan_index = scan_index % len(WATCHLIST)
    save_watchlist()
    logger.info(f"Watchlist reset to default ({len(WATCHLIST)} symbols)")
    return WATCHLIST

def add_to_watchlist(symbol):
    global WATCHLIST, scan_index
    symbol = symbol.upper().strip()
    if symbol not in WATCHLIST:
        WATCHLIST.append(symbol)
        scan_index = scan_index % len(WATCHLIST)
        save_watchlist()
        logger.info(f"Added {symbol} to watchlist")
        return True
    return False

def remove_from_watchlist(symbol):
    global WATCHLIST, scan_index
    symbol = symbol.upper().strip()
    if symbol in WATCHLIST:
        WATCHLIST.remove(symbol)
        if len(WATCHLIST) > 0:
            scan_index = scan_index % len(WATCHLIST)
        else:
            scan_index = 0
        save_watchlist()
        logger.info(f"Removed {symbol} from watchlist")
        return True
    return False

# ===============================
#  PERSISTENCE & UTILITIES
# ===============================

def load_config():
    global cfg
    try:
        with open(CONFIG_FILE, 'r') as f:
            loaded = json.load(f)
            cfg.update(loaded)
            logger.info(f"Loaded user config")
    except FileNotFoundError:
        logger.info("No user config file, using defaults")
    except Exception as e:
        logger.error(f"Error loading config: {e}")

def save_config():
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)
        logger.info("Config saved")
    except Exception as e:
        logger.error(f"Error saving config: {e}")

def save_pid():
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"PID saved: {os.getpid()}")
    except Exception as e:
        logger.error(f"Failed to save PID: {e}")

def save_all_state():
    global cash, positions, wins, losses, trade_history, metrics_history, session_id, loss_streak, trading_paused, trailing_state
    try:
        with open(WR_FILE, 'w') as f:
            json.dump({'wins': wins, 'losses': losses, 'last_updated': datetime.now().isoformat()}, f, indent=2)
        recent_history = trade_history[-1000:] if len(trade_history) > 1000 else trade_history
        with open(HISTORY_FILE, 'w') as f:
            json.dump(recent_history, f, indent=2)
        positions_data = {}
        for sym, lots in positions.items():
            positions_data[sym] = {'lots': lots, 'buy_time': buy_time.get(sym, 0), 'created_at': datetime.now().isoformat()}
        with open(POSITIONS_FILE, 'w') as f:
            json.dump(positions_data, f, indent=2)
        with open(CASH_FILE, 'w') as f:
            json.dump({'cash': cash, 'initial_cash': 1000.0, 'last_updated': datetime.now().isoformat()}, f, indent=2)
        recent_metrics = metrics_history[-1000:] if len(metrics_history) > 1000 else metrics_history
        with open(METRICS_FILE, 'w') as f:
            json.dump(recent_metrics, f, indent=2)
        with open(SESSION_FILE, 'w') as f:
            json.dump({
                'session_id': session_id, 'start_time': start_time, 'total_trades': len(trade_history),
                'total_wins': wins, 'total_losses': losses, 'current_cash': cash,
                'positions_count': len(positions), 'last_save': datetime.now().isoformat(),
                'pid': os.getpid(), 'uptime': time.time() - start_timestamp,
                'loss_streak': loss_streak, 'trading_paused': trading_paused,
                'trailing_state': trailing_state
            }, f, indent=2)
        logger.info(f"State saved: ${cash:.2f} | {len(positions)} pos | {wins}W/{losses}L | Streak:{loss_streak}")
    except Exception as e:
        logger.error(f"Save error: {e}")

def load_all_state():
    global cash, positions, wins, losses, trade_history, metrics_history, buy_time, session_id, start_time, loss_streak, trading_paused, trailing_state
    try:
        with open(SESSION_FILE, 'r') as f:
            data = json.load(f)
            session_id = data.get('session_id', datetime.now().strftime('%Y%m%d_%H%M%S'))
            start_time = data.get('start_time', datetime.now().isoformat())
            loss_streak = data.get('loss_streak', 0)
            trading_paused = data.get('trading_paused', False)
            trailing_state = data.get('trailing_state', {})
            logger.info(f"Session loaded: {session_id}, streak={loss_streak}, paused={trading_paused}")
    except: pass
    try:
        with open(WR_FILE, 'r') as f:
            data = json.load(f)
            wins, losses = data.get('wins',0), data.get('losses',0)
            logger.info(f"Loaded win/loss: {wins}W/{losses}L")
    except: wins, losses = 0,0
    try:
        with open(HISTORY_FILE, 'r') as f:
            trade_history = json.load(f)
            logger.info(f"Loaded {len(trade_history)} trades")
    except: trade_history = []
    try:
        with open(POSITIONS_FILE, 'r') as f:
            positions_data = json.load(f)
            positions, buy_time = {}, {}
            for sym, data in positions_data.items():
                positions[sym] = data['lots']
                buy_time[sym] = data.get('buy_time',0)
            logger.info(f"Loaded {len(positions)} positions")
    except: positions, buy_time = {}, {}
    try:
        with open(CASH_FILE, 'r') as f:
            cash = json.load(f).get('cash',1000.0)
            logger.info(f"Loaded cash: ${cash:.2f}")
    except: cash = 1000.0
    try:
        with open(METRICS_FILE, 'r') as f:
            metrics_history = json.load(f)
            logger.info(f"Loaded {len(metrics_history)} metric snapshots")
    except: metrics_history = []

def clear_all_history():
    global cash, positions, wins, losses, trade_history, metrics_history, buy_time, session_id, start_time, loss_streak, trading_paused, trailing_state
    backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    for f in [WR_FILE, HISTORY_FILE, POSITIONS_FILE, CASH_FILE, METRICS_FILE, SESSION_FILE]:
        if os.path.exists(f): shutil.copy(f, os.path.join(backup_dir, f))
    logger.info(f"Backup created in {backup_dir}/")
    cash, positions, buy_time = 1000.0, {}, {}
    wins = losses = loss_streak = 0
    trading_paused = False
    trailing_state = {}
    trade_history, metrics_history = [], []
    session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    start_time = datetime.now().isoformat()
    save_all_state()
    add_to_history({'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'type': 'RESET',
                    'message': 'All history cleared, bot reset to initial state', 'backup': backup_dir})
    logger.info("All history cleared and reset!")
    return backup_dir

def add_to_history(entry):
    global trade_history
    entry['timestamp'] = time.time()
    entry['session_id'] = session_id
    if 'value' not in entry:
        if entry['type'] == 'BUY' and 'position_size' in entry:
            entry['value'] = entry['position_size']
        elif entry['type'] in ('TP', 'SL', 'MANUAL') and 'pnl' in entry:
            entry['value'] = abs(entry['pnl'])
        else:
            entry['value'] = 0
    trade_history.append(entry)
    save_all_state()

def record_metrics():
    global metrics_history
    total = wins + losses
    wr = (wins/total*100) if total>0 else 0
    holdings_value = sum((sum(l['shares'] for l in lots) * (get_price_cached(sym) or 0)) for sym, lots in positions.items())
    metric = {
        'timestamp': time.time(), 'datetime': datetime.now().isoformat(),
        'cash': cash, 'holdings': holdings_value, 'net': cash+holdings_value,
        'positions': len(positions), 'wins': wins, 'losses': losses, 'win_rate': wr,
        'loss_streak': loss_streak, 'trading_paused': trading_paused, 'vix': get_vix(),
        'session_id': session_id, 'uptime': time.time()-start_timestamp
    }
    metrics_history.append(metric)
    if len(metrics_history)%10==0: save_all_state()

def heartbeat_loop():
    while running:
        time.sleep(cfg['heartbeat_interval'])
        if running:
            uptime = time.time()-start_timestamp
            holdings_value = sum((sum(l['shares'] for l in lots) * (get_price_cached(sym) or 0)) for sym, lots in positions.items())
            logger.info(f"❤️ Heartbeat - Uptime: {uptime/3600:.1f}h | Cash: ${cash:.0f} | Holdings: ${holdings_value:.0f} | Positions: {len(positions)}")

def auto_save_loop():
    while running:
        time.sleep(60)
        if running:
            save_all_state()
            record_metrics()

def prevent_sleep():
    def keep_alive():
        while running:
            time.sleep(15)
            _ = datetime.now()
    threading.Thread(target=keep_alive, daemon=True).start()
    threading.Thread(target=auto_save_loop, daemon=True).start()
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    logger.info("Background services: ACTIVE")

# ===============================
#  PRICE & INDICATORS (REST polling with memory cleanup)
# ===============================

def fetch_prices_bulk(symbols):
    global price_data
    if not symbols: return {}
    result = {}
    chunk_size = 20
    for i in range(0, len(symbols), chunk_size):
        chunk = symbols[i:i+chunk_size]
        try:
            data = yf.download(tickers=chunk, period="1y", interval="1d", group_by='ticker', threads=False, progress=False, timeout=15)
            for sym in chunk:
                try:
                    if sym in data and data[sym] is not None and not data[sym].empty:
                        df = data[sym]
                        if len(df) > 0:
                            price = float(df['Close'].iloc[-1])
                            sma20 = float(df['Close'].rolling(20).mean().iloc[-1]) if len(df) >= 20 else price
                            sma200 = float(df['Close'].rolling(200).mean().iloc[-1]) if len(df) >= 200 else None
                            if sma200 is None:
                                sma200 = float(df['Close'].rolling(50).mean().iloc[-1]) if len(df) >= 50 else price * 0.9
                            result[sym] = {'price': price, 'sma20': sma20, 'sma200': sma200, 'time': time.time()}
                except: continue
            time.sleep(0.3)
            gc.collect()
        except Exception as e:
            logger.error(f"Fetch error: {e}")
    price_data.update(result)
    # Keep only recent data to avoid memory bloat
    if len(price_data) > 1000:
        price_data = dict(list(price_data.items())[-800:])
    return result

def get_price_cached(sym):
    if sym in price_data and time.time() - price_data[sym]['time'] < 60:
        return price_data[sym]['price']
    try:
        d = yf.Ticker(sym).history(period="2d")
        if not d.empty:
            price = float(d['Close'].iloc[-1])
            price_data[sym] = price_data.get(sym, {})
            price_data[sym]['price'] = price
            price_data[sym]['time'] = time.time()
            return price
    except: pass
    return None

def get_sma20_cached(sym): return price_data[sym].get('sma20') if sym in price_data else None
def get_sma200_cached(sym): return price_data[sym].get('sma200') if sym in price_data else None

def get_vix():
    global vix_value, vix_timestamp
    if time.time() - vix_timestamp < 300: return vix_value
    try:
        d = yf.Ticker("^VIX").history(period="5d", timeout=10)
        vix_value = float(d['Close'].iloc[-1]) if not d.empty else 15.0
        vix_timestamp = time.time()
    except: vix_value = 15.0
    return vix_value

def get_vix_parameters():
    v = get_vix()
    if v > 30: return 8.0, 0.40, 1.30, "CRITICAL"
    elif v > 25: return 6.0, 0.50, 1.20, "HIGH"
    elif v > 20: return 5.0, 0.70, 1.10, "ELEVATED"
    elif v > 18: return 4.0, 0.85, 1.05, "MODERATE"
    else: return 3.0, 1.00, 1.00, "LOW"

def get_required_dip():
    v = get_vix()
    if v > 30: return cfg.get('dip_vix_critical', 8.0)
    elif v > 25: return cfg.get('dip_vix_high', 6.0)
    elif v > 20: return cfg.get('dip_vix_elevated', 5.0)
    elif v > 18: return cfg.get('dip_vix_moderate', 4.0)
    else: return cfg.get('dip_vix_low', 3.0)

def update_params():
    global cur_size, loss_streak
    total = wins+losses
    wr = wins/total if total>0 else 0.5
    v = get_vix()
    _, _, sl_mult, _ = get_vix_parameters()
    if wr > cfg['wr_extreme']:
        tp_w, sz_w = cfg['tp_extreme'], cfg['size_extreme']
        wr_effect = "AGGRESSIVE"
    elif wr > cfg['wr_very_high']:
        tp_w, sz_w = cfg['tp_very_high'], cfg['size_very_high']
        wr_effect = "BULLISH"
    elif wr > cfg['wr_high']:
        tp_w, sz_w = cfg['tp_high'], cfg['size_high']
        wr_effect = "CONFIDENT"
    elif wr < cfg['wr_low']:
        tp_w, sz_w = cfg['tp_low'], cfg['size_low']
        wr_effect = "DEFENSIVE"
    else:
        tp_w = sz_w = 1.0
        wr_effect = "NEUTRAL"
    if v > cfg['vix_high']:
        tp_v, sl_v, size_v = cfg['vix_high_tp'], cfg['vix_high_sl'], cfg['vix_high_size']
    elif v > cfg['vix_elevated']:
        tp_v, sl_v, size_v = cfg['vix_elevated_tp'], cfg['vix_elevated_sl'], cfg['vix_elevated_size']
    else:
        tp_v = sl_v = 1.0
        size_v = cfg['vix_low_size']
    tp = cfg['base_tp'] * tp_w * tp_v
    sl = cfg['base_sl'] * (cfg['sl_low'] if wr < cfg['wr_low'] else 1.0) * sl_v
    cur_size = cfg['base_size'] * sz_w * size_v
    if loss_streak > 0:
        cur_size *= (1 - (loss_streak * 0.15))
        cur_size = max(cur_size, cfg['base_size'] * 0.3)
    return tp, sl, wr, wr_effect, v

def available_cash(): return cash - cash * cfg['reserve']

def can_buy(sym, price):
    s20, s200 = get_sma20_cached(sym), get_sma200_cached(sym)
    if not s20 or not s200 or price <= s200: return False
    return ((s20 - price) / s20 * 100) >= get_required_dip()

def can_sell(sym):
    if sym not in buy_time: return True
    return (time.time() - buy_time[sym]) / 3600 >= cfg['min_hold_hours']

def update_trailing_stop(sym, current_price, entry_avg):
    if sym not in trailing_state:
        trailing_state[sym] = {'highest': entry_avg, 'trailing': entry_avg * (1 - cfg['trailing_stop_pct']), 'has_pyramid': False}
    if current_price > trailing_state[sym]['highest']:
        trailing_state[sym]['highest'] = current_price
        trailing_state[sym]['trailing'] = current_price * (1 - cfg['trailing_stop_pct'])
    return trailing_state[sym]['trailing']

def check_exits():
    global cash, wins, losses, loss_streak, trading_paused, pause_end_time
    to_remove = []
    tp, sl, _, _, _ = update_params()
    for sym, lots in list(positions.items()):
        price = get_price_cached(sym)
        if not price: continue
        shares = sum(l['shares'] for l in lots)
        avg = sum(l['shares'] * l['price'] for l in lots) / shares
        tp_price = avg * (1 + tp)
        sl_price = avg * (1 - sl)
        if not can_sell(sym):
            continue
        if price >= tp_price:
            pnl = shares * (price - avg)
            cash += shares * price
            wins += 1
            to_remove.append(sym)
            if loss_streak > 0:
                loss_streak = 0
                trading_paused = False
            add_to_history({'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'symbol': sym, 'type': 'TP',
                'entry': round(avg,2), 'exit': round(price,2), 'pnl': round(pnl,2), 'shares': round(shares,2),
                'hold_time': round((time.time() - buy_time.get(sym, time.time()))/3600,1)})
            logger.info(f"💰 TP {sym}: +${pnl:.2f}")
        else:
            trail_triggered = False
            if cfg['trailing_stop_pct'] > 0:
                if not cfg['trailing_only_after_pyramid'] or (sym in trailing_state and trailing_state[sym].get('has_pyramid', False)):
                    trail_sl = update_trailing_stop(sym, price, avg)
                    if price <= trail_sl:
                        trail_triggered = True
                        pnl = shares * (price - avg)
                        cash += shares * price
                        losses += 1
                        to_remove.append(sym)
                        loss_streak += 1
                        if cfg.get('circuit_breaker_enabled', True):
                            if loss_streak >= cfg['max_consecutive_losses']:
                                trading_paused = True
                                pause_end_time = time.time() + cfg['loss_streak_cooldown'] * 3600
                                logger.warning(f"🔴 {loss_streak} consecutive losses! Trading paused for {cfg['loss_streak_cooldown']} hours")
                        add_to_history({'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'symbol': sym, 'type': 'SL',
                            'entry': round(avg,2), 'exit': round(price,2), 'pnl': round(pnl,2), 'shares': round(shares,2),
                            'hold_time': round((time.time() - buy_time.get(sym, time.time()))/3600,1)})
                        logger.info(f"📉 Trailing SL {sym}: ${pnl:.2f} (Loss streak: {loss_streak})")
            if not trail_triggered and cfg['static_stop_loss_enabled'] and price <= sl_price:
                pnl = shares * (price - avg)
                cash += shares * price
                losses += 1
                to_remove.append(sym)
                loss_streak += 1
                if cfg.get('circuit_breaker_enabled', True):
                    if loss_streak >= cfg['max_consecutive_losses']:
                        trading_paused = True
                        pause_end_time = time.time() + cfg['loss_streak_cooldown'] * 3600
                        logger.warning(f"🔴 {loss_streak} consecutive losses! Trading paused for {cfg['loss_streak_cooldown']} hours")
                add_to_history({'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'symbol': sym, 'type': 'SL',
                    'entry': round(avg,2), 'exit': round(price,2), 'pnl': round(pnl,2), 'shares': round(shares,2),
                    'hold_time': round((time.time() - buy_time.get(sym, time.time()))/3600,1)})
                logger.info(f"📉 Static SL {sym}: ${pnl:.2f} (Loss streak: {loss_streak})")
    for sym in to_remove:
        del positions[sym]
        if sym in buy_time: del buy_time[sym]
        if sym in trailing_state: del trailing_state[sym]
    if to_remove: save_all_state()

def check_entries():
    global cash, trading_paused, loss_streak
    if trading_paused:
        if time.time() < pause_end_time: return
        trading_paused = False
        loss_streak = 0
        logger.info("✅ Cooldown period ended - resuming trading")
    if not trading or len(positions) >= cfg['max_pos']: return
    avail = available_cash()
    if avail < cfg['min_trade']: return
    tp, sl, _, _, _ = update_params()
    dip_req = get_required_dip()
    trade_val = avail * cur_size
    if trade_val < cfg['min_trade']: return
    candidates = buy_list[:cfg['max_buys']] if buy_list else []
    if not candidates:
        return
    bought = 0
    for dip_info in candidates:
        if bought >= cfg['max_buys'] or len(positions) >= cfg['max_pos']:
            break
        sym = dip_info['sym']
        price = dip_info['price']
        price = get_price_cached(sym) or price
        if not price:
            continue
        existing = positions.get(sym)
        add_type = None
        add_size_mult = 1.0
        if existing and cfg['build']:
            total_shares = sum(l['shares'] for l in existing)
            avg = sum(l['shares'] * l['price'] for l in existing) / total_shares
            pnl_pct = (price - avg) / avg * 100
            build_count = sum(1 for l in existing if l.get('is_build', False))
            if pnl_pct <= -cfg.get('build_trigger_pct', 2.5) and build_count < cfg.get('max_builds', 3):
                add_type = "AVG_DOWN"
                add_size_mult = cfg['build_factor']
            elif pnl_pct >= cfg['pyramid_threshold']:
                s20 = get_sma20_cached(sym)
                if s20 and price < s20:
                    pyramid_count = sum(1 for l in existing if l.get('is_pyramid', False))
                    if pyramid_count < cfg['max_pyramids']:
                        add_type = "PYRAMID"
                        add_size_mult = cfg['pyramid_size']
        if add_type or (sym not in positions and can_buy(sym, price)):
            s20 = get_sma20_cached(sym)
            dip = ((s20 - price) / s20 * 100) if s20 else 0
            size = trade_val * add_size_mult
            size = max(size, cfg['min_trade'])
            if size > avail: size = avail
            if size < cfg['min_trade']: continue
            shares = size / price
            lot = {'shares': shares, 'price': price}
            if add_type == "PYRAMID":
                lot['is_pyramid'] = True
                if sym not in trailing_state:
                    trailing_state[sym] = {'highest': price, 'trailing': price * (1 - cfg['trailing_stop_pct']), 'has_pyramid': False}
                trailing_state[sym]['has_pyramid'] = True
            if add_type == "AVG_DOWN": lot['is_build'] = True
            if sym in positions:
                positions[sym].append(lot)
            else:
                positions[sym] = [lot]
            buy_time[sym] = time.time()
            if sym not in trailing_state:
                trailing_state[sym] = {'highest': price, 'trailing': price * (1 - cfg['trailing_stop_pct']), 'has_pyramid': False}
            cash -= size
            bought += 1
            avail = available_cash()
            trade_val = avail * cur_size
            if trade_val < cfg['min_trade']: break
            if add_type is None:
                add_to_history({'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'symbol': sym, 'type': 'BUY',
                    'entry': round(price,2), 'shares': round(shares,2), 'dip': round(dip,1),
                    'required_dip': dip_req, 'position_size': round(size,2)})
            else:
                add_to_history({'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'symbol': sym, 'type': add_type,
                    'entry': round(price,2), 'shares': round(shares,2), 'dip': round(dip,1),
                    'position_size': round(size,2)})
            action = add_type if add_type else "NEW"
            logger.info(f"{action} BUY {sym} @ {price:.2f} (Dip:{dip:.1f}%, Req:{dip_req}%, Size:${size:.2f})")
    if bought: save_all_state()

def scan():
    global buy_list, scan_num, scan_index
    scan_num += 1
    min_dip = get_required_dip()
    if scan_num == 1:
        candidates = WATCHLIST.copy()
        logger.info(f"📡 Full initial scan #{scan_num}: all {len(candidates)} symbols")
    else:
        chunk_size = cfg['scan_size']
        start = scan_index
        end = start + chunk_size
        if end >= len(WATCHLIST):
            candidates = WATCHLIST[start:] + WATCHLIST[:end - len(WATCHLIST)]
        else:
            candidates = WATCHLIST[start:end]
        scan_index = (scan_index + chunk_size) % len(WATCHLIST)
        logger.info(f"📡 Round‑robin scan #{scan_num}: symbols {start}–{end} (chunk {chunk_size})")
    fetch_prices_bulk(candidates)
    dips = []
    for sym in candidates:
        price = get_price_cached(sym)
        s20, s200 = get_sma20_cached(sym), get_sma200_cached(sym)
        if price and s20 is not None and s200 is not None and price > s200 and price < s20:
            dip = round((s20 - price) / s20 * 100, 1)
            if dip >= min_dip:
                dips.append({'sym': sym, 'price': price, 'dip': dip})
    dips.sort(key=lambda x: x['dip'], reverse=True)
    buy_list = dips[:10]
    logger.info(f"📡 Scan #{scan_num}: {len(buy_list)} buys from {len(candidates)} symbols (min {min_dip}% dip)")

def manual_sell(symbol):
    global cash, wins, losses, loss_streak, trading_paused
    symbol = symbol.upper()
    if symbol not in positions:
        return False, "Position not found"
    lots = positions[symbol]
    price = get_price_cached(symbol)
    if not price:
        return False, "Cannot get current price"
    shares = sum(l['shares'] for l in lots)
    avg = sum(l['shares'] * l['price'] for l in lots) / shares
    pnl = shares * (price - avg)
    cash += shares * price
    add_to_history({'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'symbol': symbol, 'type': 'MANUAL',
        'entry': round(avg,2), 'exit': round(price,2), 'pnl': round(pnl,2), 'shares': round(shares,2),
        'hold_time': round((time.time() - buy_time.get(symbol, time.time()))/3600,1)})
    logger.info(f"✋ Manual sell {symbol} @ {price:.2f} | PnL: ${pnl:.2f}")
    del positions[symbol]
    if symbol in buy_time: del buy_time[symbol]
    if symbol in trailing_state: del trailing_state[symbol]
    save_all_state()
    return True, f"Sold {symbol} at ${price:.2f}, PnL: ${pnl:.2f}"

# ===============================
#  FOREGROUND SERVICE (persistent notification + wake lock)
# ===============================
def setup_persistent_notification():
    try:
        subprocess.run(['termux-notification', '--help'], capture_output=True, check=False)
        cmd = [
            'termux-notification',
            '--id', 'trading_bot',
            '--title', '📈 Trading Bot Active',
            '--content', f'Running since {datetime.now().strftime("%H:%M:%S")}',
            '--ongoing', 'true',
            '--priority', 'max'
        ]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("✅ Persistent notification created.")

        def update_notification():
            while running:
                time.sleep(60)
                if not running: break
                try:
                    subprocess.Popen([
                        'termux-notification',
                        '--id', 'trading_bot',
                        '--content', f'Running since {datetime.now().strftime("%H:%M:%S")} | Trades: {len(trade_history)}',
                        '--ongoing', 'true'
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except: pass
        threading.Thread(target=update_notification, daemon=True).start()
    except FileNotFoundError:
        logger.warning("termux-notification not found. Install termux-api.")
    except Exception as e:
        logger.warning(f"Notification error: {e}")

def refresh_wakelock_loop():
    while running:
        try:
            subprocess.run(['termux-wake-lock'], capture_output=True, check=False)
        except:
            pass
        time.sleep(30)

def prevent_android_kill():
    logger.info("="*50)
    logger.info("📱 TO PREVENT ANDROID FROM KILLING THIS BOT:")
    logger.info("   1. Disable battery optimization for Termux")
    logger.info("   2. Run: termux-wake-lock (auto-refreshed)")
    logger.info("   3. Use tmux: tmux new -s tradingbot")
    logger.info("   4. Keep this notification visible")
    logger.info("="*50)

# ===============================
#  TRADING LOOP
# ===============================
def trading_loop():
    logger.info("="*50)
    logger.info(f"🤖 REST BOT | {len(WATCHLIST)} SYMBOLS | ${cash:.0f}")
    logger.info(f"🆔 Session: {session_id}")
    logger.info("⚡ Optimised polling with caching and memory cleanup")
    logger.info("="*50)
    fetch_prices_bulk(WATCHLIST)
    scan()
    last_scan_time = last_fetch_time = last_log_time = time.time()
    while running:
        try:
            now = time.time()
            if now - last_fetch_time >= 60:
                sample_size = min(50, len(WATCHLIST))
                symbols_to_refresh = list(set(list(positions.keys()) + random.sample(WATCHLIST, sample_size)))
                if symbols_to_refresh:
                    fetch_prices_bulk(symbols_to_refresh)
                last_fetch_time = now
            if now - last_scan_time >= 30:
                scan()
                last_scan_time = now
                record_metrics()
            check_exits()
            check_entries()
            if now - last_log_time >= 300:
                total = wins + losses
                wr = (wins/total*100) if total>0 else 0
                holdings_value = sum((sum(l['shares'] for l in lots) * (get_price_cached(sym) or 0)) for sym, lots in positions.items())
                net = cash + holdings_value
                logger.info(f"📊 VIX:{get_vix():.0f} | P:{len(positions)} | C:${cash:.0f} | NW:${net:.0f} | WR:{wr:.0f}% | Streak:{loss_streak}")
                last_log_time = now
            time.sleep(22)
        except Exception as e:
            logger.error(f"Trading error: {e}")
            traceback.print_exc()
            time.sleep(30)

def get_status():
    positions_copy = positions.copy()
    holdings_value = sum((sum(l['shares'] for l in lots) * (get_price_cached(sym) or 0)) for sym, lots in positions_copy.items())
    net = cash + holdings_value
    total = wins + losses
    wr = (wins/total*100) if total>0 else 0
    v = get_vix()
    min_dip = get_required_dip()
    tp, sl, wr_raw, wr_effect, _ = update_params()
    _, size_mult, sl_mult, vix_tier = get_vix_parameters()
    total_pnl = sum(t.get('pnl',0) for t in trade_history if 'pnl' in t)
    avg_win = sum(t.get('pnl',0) for t in trade_history if t.get('type')=='TP' and t.get('pnl',0)>0) / max(wins,1) if wins else 0
    avg_loss = abs(sum(t.get('pnl',0) for t in trade_history if t.get('type')=='SL' and t.get('pnl',0)<0) / max(losses,1)) if losses else 0
    uptime = time.time()-start_timestamp
    pause_remaining = max(0, pause_end_time - time.time())/3600 if trading_paused else 0
    holdings_list = []
    for sym, lots in positions_copy.items():
        price = get_price_cached(sym)
        if price:
            shares = sum(l['shares'] for l in lots)
            avg = sum(l['shares'] * l['price'] for l in lots) / shares
            num_entries = len(lots)
            num_pyramids = sum(1 for l in lots if l.get('is_pyramid', False))
            num_builds = sum(1 for l in lots if l.get('is_build', False))
            lots_detail = []
            for idx, lot in enumerate(lots):
                lot_type = "INITIAL"
                if idx == 0:
                    lot_type = "BASE"
                elif lot.get('is_pyramid', False):
                    lot_type = "PYRAMID"
                elif lot.get('is_build', False):
                    lot_type = "BUILD"
                else:
                    lot_type = "ADD"
                lots_detail.append({
                    'type': lot_type,
                    'price': round(lot['price'], 2),
                    'shares': round(lot['shares'], 2)
                })
            trail_active = False
            trail_price = None
            if sym in trailing_state:
                trail_active = trailing_state[sym].get('has_pyramid', False)
                if trail_active and 'trailing' in trailing_state[sym]:
                    trail_price = round(trailing_state[sym]['trailing'], 2)
            holdings_list.append({
                'sym': sym, 'shares': round(shares,2), 'entry': round(avg,2), 'cur': round(price,2),
                'pnl': round((price-avg)/avg*100,1), 'tp': round(avg*(1+tp),2),
                'sl': round(avg*(1-sl),2), 'val': round(shares*price,2),
                'entries': num_entries, 'builds': num_builds, 'pyramids': num_pyramids,
                'lots_detail': lots_detail,
                'trail_active': trail_active,
                'trail_price': trail_price
            })
    formatted_history = []
    for t in trade_history[-500:]:
        entry = t.copy()
        if 'value' not in entry:
            if entry['type'] == 'BUY' and 'position_size' in entry:
                entry['value'] = entry['position_size']
            elif entry['type'] in ('TP', 'SL', 'MANUAL') and 'pnl' in entry:
                entry['value'] = abs(entry['pnl'])
            else:
                entry['value'] = 0
        formatted_history.append(entry)
    return {
        'cash': round(cash,2), 'hold': round(holdings_value,2), 'net': round(net,2),
        'pl': round(net-1000,2), 'pos': len(positions_copy), 'wins': wins, 'losses': losses,
        'wr': round(wr,1), 'vix': round(v,1), 'size': round(cur_size*100,1),
        'tp': round(tp*100,1), 'sl': round(sl*100,1), 'dip': min_dip,
        'size_mult': round(size_mult*100,1), 'sl_mult': round(sl_mult,2),
        'buys': buy_list[:10], 'holdings': holdings_list, 'scan': scan_num,
        'total': len(WATCHLIST), 'mode': "EXTREME" if v>25 else "NORMAL",
        'wr_effect': wr_effect, 'vix_tier': vix_tier,
        'trade_history': formatted_history, 'session_id': session_id[:8],
        'start_time': start_time, 'total_trades': len(trade_history),
        'total_pnl': round(total_pnl,2), 'avg_win': round(avg_win,2),
        'avg_loss': round(avg_loss,2), 'metrics_count': len(metrics_history),
        'uptime_hours': round(uptime/3600,1), 'pid': os.getpid(),
        'trading_enabled': trading, 'loss_streak': loss_streak,
        'trading_paused': trading_paused, 'pause_remaining_hours': round(pause_remaining,1),
        'build': cfg['build'], 'max_pyramids': cfg['max_pyramids'], 'max_builds': cfg.get('max_builds', 3),
        'build_trigger_pct': cfg.get('build_trigger_pct', 2.5),
        'max_consecutive_losses': cfg['max_consecutive_losses'], 'loss_streak_cooldown': cfg['loss_streak_cooldown'],
        'scan_size': cfg['scan_size'], 'trailing_stop_pct': cfg['trailing_stop_pct'],
        'min_hold_hours': cfg['min_hold_hours'], 'build_factor': cfg['build_factor'],
        'pyramid_threshold': cfg['pyramid_threshold'], 'pyramid_size': cfg['pyramid_size'],
        'base_tp': cfg['base_tp'], 'base_sl': cfg['base_sl'], 'base_size': cfg['base_size'],
        'sl_low': cfg['sl_low'], 'reserve': cfg['reserve'],
        'wr_extreme': cfg['wr_extreme'], 'wr_very_high': cfg['wr_very_high'], 'wr_high': cfg['wr_high'], 'wr_low': cfg['wr_low'],
        'tp_extreme': cfg['tp_extreme'], 'tp_very_high': cfg['tp_very_high'], 'tp_high': cfg['tp_high'], 'tp_low': cfg['tp_low'],
        'size_extreme': cfg['size_extreme'], 'size_very_high': cfg['size_very_high'], 'size_high': cfg['size_high'], 'size_low': cfg['size_low'],
        'vix_high_tp': cfg['vix_high_tp'], 'vix_elevated_tp': cfg['vix_elevated_tp'],
        'vix_high_sl': cfg['vix_high_sl'], 'vix_elevated_sl': cfg['vix_elevated_sl'],
        'vix_high_size': cfg['vix_high_size'], 'vix_elevated_size': cfg['vix_elevated_size'], 'vix_low_size': cfg['vix_low_size'],
        'vix_high': cfg['vix_high'], 'vix_elevated': cfg['vix_elevated'],
        'watchlist': WATCHLIST, 'watchlist_count': len(WATCHLIST),
        'dip_vix_critical': cfg.get('dip_vix_critical', 8.0),
        'dip_vix_high': cfg.get('dip_vix_high', 6.0),
        'dip_vix_elevated': cfg.get('dip_vix_elevated', 5.0),
        'dip_vix_moderate': cfg.get('dip_vix_moderate', 4.0),
        'dip_vix_low': cfg.get('dip_vix_low', 3.0),
        'static_stop_loss_enabled': cfg.get('static_stop_loss_enabled', True),
        'trailing_only_after_pyramid': cfg.get('trailing_only_after_pyramid', True),
        'circuit_breaker_enabled': cfg.get('circuit_breaker_enabled', True),
    }

# ===============================
#  WEB DASHBOARD (FULL HTML – same as original)
# ===============================

HTML = '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DIP BOT</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body {
  background: #0a0f1a;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 13px;
  color: #e0e5f0;
  padding: 12px;
}
.container { max-width: 1400px; margin: 0 auto; }
.header {
  background: #11161f;
  border: 1px solid #2a3440;
  padding: 8px 12px;
  margin-bottom: 12px;
  border-radius: 6px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
}
.status { display: flex; align-items: center; gap: 12px; }
.dot { width: 10px; height: 10px; border-radius: 50%; }
.d-live { background: #2ecc71; }
.d-pause { background: #f1c40f; }
.d-off { background: #e74c3c; }
.pill {
  font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 20px;
  background: #1e2a36;
}
.p-live { color: #2ecc71; border: 1px solid #2ecc71; }
.p-pause { color: #f1c40f; border: 1px solid #f1c40f; }
.p-off { color: #e74c3c; border: 1px solid #e74c3c; }
.stats-row {
  display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0;
}
.card {
  background: #11161f; border: 1px solid #2a3440; border-radius: 6px;
  padding: 6px 10px; flex: 1; min-width: 70px;
}
.card-label { font-size: 9px; text-transform: uppercase; color: #7e8c9e; }
.card-value { font-size: 16px; font-weight: bold; line-height: 1.2; }
.pos { color: #2ecc71; }
.neg { color: #e74c3c; }
.warn { color: #f1c40f; }
.info { color: #3498db; }
.banner {
  background: #2c2a1a; border-left: 4px solid #f1c40f; padding: 6px 10px;
  margin-bottom: 12px; font-size: 12px; display: none;
}
.banner.show { display: block; }
.split {
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px;
}
.panel {
  background: #11161f; border: 1px solid #2a3440; border-radius: 6px; overflow: hidden;
}
.panel-header {
  background: #1a212c; padding: 6px 10px; font-weight: bold; font-size: 11px;
  text-transform: uppercase; border-bottom: 1px solid #2a3440;
}
.scroll-list { max-height: 280px; overflow-y: auto; }
.dip-row, .history-row {
  display: flex; justify-content: space-between; padding: 6px 10px;
  border-bottom: 1px solid #1e2630; font-size: 12px;
}
.symbol { font-weight: bold; color: #3498db; }
.dip-pct { color: #f1c40f; }
.history-type {
  font-size: 9px; padding: 2px 5px; border-radius: 3px; background: #1e2a36;
}
.type-buy { background: #1e3a2a; color: #2ecc71; }
.type-tp { background: #1a2a3a; color: #3498db; }
.type-sl { background: #3a1e1e; color: #e74c3c; }
.type-manual { background: #4a2a6a; color: #c084fc; }
.holdings-table {
  width: 100%; border-collapse: collapse; font-size: 11px;
}
.holdings-table th, .holdings-table td {
  padding: 6px 8px; text-align: right; border-bottom: 1px solid #1e2630;
}
.holdings-table th:first-child, .holdings-table td:first-child { text-align: left; }
.holdings-table th { background: #1a212c; color: #7e8c9e; font-weight: normal; }
.lot-detail-row td { background: #0d121b; padding-left: 24px; font-size: 10px; }
.lot-type {
  display: inline-block; padding: 1px 4px; border-radius: 3px; margin-right: 4px; font-size: 9px;
}
.lt-base { background: #1a3a5c; }
.lt-build { background: #5c4a1a; color: #f1c40f; }
.lt-pyramid { background: #1a5c3a; color: #2ecc71; }
.collapsible {
  background: #11161f; border: 1px solid #2a3440; border-radius: 6px; margin-bottom: 12px;
}
.collapsible-header {
  background: #1a212c; padding: 8px 12px; cursor: pointer; font-weight: bold;
  font-size: 12px; display: flex; justify-content: space-between;
}
.collapsible-body { display: none; padding: 8px 12px; }
.collapsible-body.open { display: block; }
.config-group { margin-bottom: 12px; border-bottom: 1px solid #1e2630; padding-bottom: 8px; }
.config-group-title { font-size: 11px; font-weight: bold; color: #3498db; margin-bottom: 6px; }
.config-row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 11px; gap: 8px; }
.config-row input {
  background: #1e2630; border: 1px solid #2a3440; color: #e0e5f0;
  padding: 2px 6px; border-radius: 3px; width: 80px; text-align: right;
}
.config-row input[type="checkbox"] { width: auto; }
.watchlist-add { display: flex; gap: 6px; margin-bottom: 10px; }
.watchlist-add input {
  flex: 1; background: #1e2630; border: 1px solid #2a3440; padding: 5px 8px;
  color: #e0e5f0; border-radius: 4px;
}
.watchlist-item { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #1e2630; }
.btn {
  background: #1e2a36; border: 1px solid #2a3440; padding: 4px 10px; border-radius: 4px;
  color: #e0e5f0; cursor: pointer; font-family: inherit; font-size: 11px;
}
.btn-primary { background: #2c3e50; border-color: #3498db; color: #3498db; }
.btn-danger { background: #3a1e1e; border-color: #e74c3c; color: #e74c3c; }
.btn-warning { background: #2c2a1a; border-color: #f1c40f; color: #f1c40f; }
.btn-sm { padding: 2px 6px; font-size: 10px; }
.footer {
  margin-top: 12px; font-size: 10px; color: #5a6a7a; text-align: center;
  border-top: 1px solid #1e2630; padding-top: 10px;
}
.modal {
  display: none; position: fixed; top:0; left:0; right:0; bottom:0;
  background: rgba(0,0,0,0.7); align-items: center; justify-content: center; z-index: 100;
}
.modal.open { display: flex; }
.modal-content {
  background: #11161f; border: 1px solid #2a3440; padding: 20px;
  max-width: 300px; border-radius: 8px; text-align: center;
}
</style>
</head>
<body>
<div class="container">
<div class="header">
  <div class="status">
    <div id="dot" class="dot d-live"></div>
    <span class="pill p-live" id="pill">LIVE</span>
    <strong>DIPBOT</strong>
  </div>
  <div style="display: flex; gap: 6px;">
    <button class="btn btn-primary" id="btnStart">▶ START</button>
    <button class="btn" id="btnStop">⏸ STOP</button>
    <button class="btn btn-danger" id="btnShut">⛌ SHUT</button>
  </div>
</div>

<div class="stats-row">
  <div class="card"><div class="card-label">NET</div><div class="card-value info" id="hNet">--</div></div>
  <div class="card"><div class="card-label">P&L</div><div class="card-value" id="hPl">--</div></div>
  <div class="card"><div class="card-label">WINRATE</div><div class="card-value" id="hWr">--</div></div>
  <div class="card"><div class="card-label">VIX</div><div class="card-value" id="hVix">--</div></div>
  <div class="card"><div class="card-label">POSITIONS</div><div class="card-value info" id="hPos">--</div></div>
</div>
<div class="stats-row">
  <div class="card"><div class="card-label">CASH</div><div class="card-value info" id="cash">--</div></div>
  <div class="card"><div class="card-label">HOLDINGS</div><div class="card-value" id="hold">--</div></div>
  <div class="card"><div class="card-label">W/L</div><div class="card-value" id="wl">--</div></div>
  <div class="card"><div class="card-label">STREAK</div><div class="card-value" id="streak">--</div></div>
  <div class="card"><div class="card-label">TP</div><div class="card-value pos" id="tp">--</div></div>
  <div class="card"><div class="card-label">SL</div><div class="card-value neg" id="sl">--</div></div>
  <div class="card"><div class="card-label">DIP REQ</div><div class="card-value warn" id="dip">--</div></div>
  <div class="card"><div class="card-label">POS SIZE</div><div class="card-value info" id="size">--</div></div>
</div>

<div id="banner" class="banner">⚠️ CIRCUIT BREAKER: <span id="bannerTxt">paused</span></div>

<div class="split">
  <div class="panel">
    <div class="panel-header">🔽 TOP DIPS <span id="scanBadge">#0</span></div>
    <div class="scroll-list" id="dipsList"><div>Loading...</div></div>
  </div>
  <div class="panel">
    <div class="panel-header">📜 TRADE LOG <span id="histBadge"></span></div>
    <div class="scroll-list" id="histList"><div>Loading...</div></div>
  </div>
</div>

<div class="panel" style="margin-bottom:12px">
  <div class="panel-header">📊 HOLDINGS <span id="holdBadge">0</span></div>
  <div style="overflow-x:auto">
    <table class="holdings-table">
      <thead>
        <tr><th>SYM</th><th>ENTRY</th><th>NOW</th><th>P&L%</th><th>VAL</th><th>E/B/P</th><th>TRAIL</th><th></th></tr>
      </thead>
      <tbody id="holdBody"><tr><td colspan="8">No positions</td></tr>
      </tbody>
    </table>
  </div>
</div>

<div class="collapsible" id="wlColl">
  <div class="collapsible-header" id="wlToggle">📋 WATCHLIST EDITOR <span id="wlCountBadge"></span> <span>▼</span></div>
  <div class="collapsible-body" id="wlBody">
    <div class="watchlist-add">
      <input type="text" id="wlInput" placeholder="Symbol (e.g. AAPL)" maxlength="10">
      <button class="btn" id="wlAddBtn">+ ADD</button>
    </div>
    <div id="wlList">Loading...</div>
    <button class="btn btn-warning" id="wlResetBtn" style="margin-top:8px; width:100%">⟳ RESET TO DEFAULT</button>
  </div>
</div>

<div class="collapsible" id="cfgColl">
  <div class="collapsible-header" id="cfgToggle">⚙️ CONFIGURATION <span>▼</span></div>
  <div class="collapsible-body" id="cfgBody">Loading...</div>
  <button class="btn" id="btnReset" style="width:100%; border-top:1px solid #2a3440">↺ RESET TO DEFAULTS</button>
</div>

<div class="collapsible" id="logColl">
  <div class="collapsible-header" id="logToggle">🧠 STRATEGY LOGIC <span>▼</span></div>
  <div class="collapsible-body" id="logBody">Loading...</div>
</div>

<div class="footer">
  <span>SID: <span id="sid">--</span></span> |
  <span>PID: <span id="pid">--</span></span> |
  <span>Scans: <span id="scans">--</span></span> |
  <span>Trades: <span id="trades">--</span></span> |
  <span>Avg W: <span id="avgW" class="pos">--</span></span> |
  <span>Avg L: <span id="avgL" class="neg">--</span></span> |
  <span>Total P&L: <span id="totPnl">--</span></span> |
  <span>Up: <span id="uptime">--</span>h</span> |
  <button class="btn btn-danger" id="btnClear" style="font-size:10px">🗑 CLEAR</button>
</div>
</div>

<div class="modal" id="modal">
  <div class="modal-content">
    <strong>⚠️ Clear all history?</strong>
    <p style="margin:10px 0; font-size:12px">Resets cash to $1000, wipes trades. Backup saved.</p>
    <div style="display:flex; gap:8px; justify-content:center">
      <button class="btn btn-primary" id="confirmClear">CONFIRM</button>
      <button class="btn" id="cancelClear">CANCEL</button>
    </div>
  </div>
</div>

<script>
let expandedSymbols = new Set();

async function api(url, body) {
  const opts = body ? { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) } : { method:'POST' };
  return fetch(url, opts).then(r=>r.json()).catch(()=>({}));
}

document.getElementById('btnStart').onclick = () => api('/api/start');
document.getElementById('btnStop').onclick = () => api('/api/stop');
document.getElementById('btnShut').onclick = () => { if(confirm('Shut down bot?')) { api('/api/shutdown'); setTimeout(()=>location.reload(),1500); } };
document.getElementById('btnClear').onclick = () => document.getElementById('modal').classList.add('open');
document.getElementById('cancelClear').onclick = () => document.getElementById('modal').classList.remove('open');
document.getElementById('confirmClear').onclick = async () => {
  document.getElementById('modal').classList.remove('open');
  await api('/api/clear');
  setTimeout(()=>location.reload(),1500);
};

function initColl(toggleId, bodyId) {
  const toggle = document.getElementById(toggleId);
  const body = document.getElementById(bodyId);
  if(toggle && body) toggle.onclick = () => body.classList.toggle('open');
}
initColl('wlToggle', 'wlBody');
initColl('cfgToggle', 'cfgBody');
initColl('logToggle', 'logBody');

async function loadWatchlist() {
  try {
    const d = await fetch('/api/status').then(r=>r.json());
    const wl = d.watchlist || [];
    document.getElementById('wlCountBadge').innerText = `(${wl.length})`;
    if(!wl.length) { document.getElementById('wlList').innerHTML = '<div>Empty</div>'; return; }
    let html = '';
    for(const sym of wl) html += `<div class="watchlist-item"><span>${sym}</span><button class="btn" onclick="removeSymbol('${sym}')">REMOVE</button></div>`;
    document.getElementById('wlList').innerHTML = html;
  } catch(e) { console.error(e); }
}
window.removeSymbol = async (sym) => { await api('/api/watchlist/remove',{symbol:sym}); loadWatchlist(); };
document.getElementById('wlAddBtn').onclick = async () => {
  const inp = document.getElementById('wlInput');
  const sym = inp.value.trim().toUpperCase();
  if(!sym) return;
  await api('/api/watchlist/add',{symbol:sym});
  inp.value = '';
  loadWatchlist();
};
document.getElementById('wlResetBtn').onclick = async () => { if(confirm('Reset watchlist to default 300 symbols?')) { await api('/api/watchlist/reset'); loadWatchlist(); } };

let cfgLoaded = false;
async function loadCfg() {
  if(cfgLoaded) return;
  cfgLoaded = true;
  const cfg = await fetch('/api/config').then(r=>r.json());
  const groups = {
    'Core Risk': ['base_size','reserve','base_tp','base_sl','max_pos','max_buys','min_trade','min_hold_hours','trailing_stop_pct','static_stop_loss_enabled','trailing_only_after_pyramid'],
    'Build / Pyramid': ['build','build_factor','max_builds','build_trigger_pct','pyramid_threshold','pyramid_size','max_pyramids'],
    'Win-Rate Adjust': ['wr_extreme','wr_very_high','wr_high','wr_low','tp_extreme','tp_very_high','tp_high','tp_low','size_extreme','size_very_high','size_high','size_low'],
    'VIX Adjust': ['vix_high','vix_elevated','vix_high_tp','vix_elevated_tp','sl_low','vix_high_sl','vix_elevated_sl','vix_high_size','vix_elevated_size','vix_low_size'],
    'Dip Tiers (VIX)': ['dip_vix_critical','dip_vix_high','dip_vix_elevated','dip_vix_moderate','dip_vix_low'],
    'Circuit Breaker': ['max_consecutive_losses','loss_streak_cooldown','circuit_breaker_enabled'],
    'Scanning': ['scan_size','heartbeat_interval','auto_restart']
  };
  let html = '';
  for(const [g, keys] of Object.entries(groups)) {
    html += `<div class="config-group"><div class="config-group-title">${g}</div>`;
    for(const k of keys) {
      if(cfg[k] === undefined) continue;
      const isBool = typeof cfg[k] === 'boolean';
      html += `<div class="config-row"><span>${k}</span>`;
      if(isBool) html += `<input type="checkbox" ${cfg[k] ? 'checked' : ''} onchange="updateConfig('${k}', this.checked)">`;
      else html += `<input type="number" step="any" value="${cfg[k]}" onchange="updateConfig('${k}', parseFloat(this.value))">`;
      html += `</div>`;
    }
    html += `</div>`;
  }
  document.getElementById('cfgBody').innerHTML = html;
}
window.updateConfig = async (k,v) => { await fetch('/api/config', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:k,value:v})}); };
document.getElementById('btnReset').onclick = async () => { await fetch('/api/reset_config',{method:'POST'}); cfgLoaded=false; loadCfg(); };

async function loadLogic() {
  const d = await fetch('/api/status').then(r=>r.json());
  const v = d.vix, wr = d.wr;
  const wrM = d.wr_effect === 'AGGRESSIVE' ? `TP x${d.tp_extreme} Sz x${d.size_extreme}` : d.wr_effect === 'BULLISH' ? `TP x${d.tp_very_high} Sz x${d.size_very_high}` : d.wr_effect === 'CONFIDENT' ? `TP x${d.tp_high} Sz x${d.size_high}` : d.wr_effect === 'DEFENSIVE' ? `TP x${d.tp_low} Sz x${d.size_low}` : 'x1.0';
  const vM = v > 25 ? `TP x${d.vix_high_tp} Sz x${d.vix_high_size} SL x${d.vix_high_sl}` : v > 18 ? `TP x${d.vix_elevated_tp} Sz x${d.vix_elevated_size} SL x${d.vix_elevated_sl}` : `Sz x${d.vix_low_size}`;
  document.getElementById('logBody').innerHTML = `
    <div style="margin-bottom:8px"><strong>Entry:</strong> price > 200-SMA AND dip >= ${d.dip}% below 20-SMA. VIX ${v} → ${d.vix_tier} → req ${d.dip}%</div>
    <div style="margin-bottom:8px"><strong>TP/SL:</strong> TP = base_tp x WR_mult x VIX_mult = ${d.tp}% | SL = base_sl x adj = ${d.sl}%<br>WR ${wr}% → ${d.wr_effect}: ${wrM}<br>VIX ${v}: ${vM}<br>Static SL enabled: ${d.static_stop_loss_enabled} | Trailing only after pyramid: ${d.trailing_only_after_pyramid}</div>
    <div style="margin-bottom:8px"><strong>Sizing:</strong> size = base x WR_mult x VIX_mult = ${d.size}%<br>Trail stop: peak x (1 - ${(d.trailing_stop_pct*100).toFixed(1)}%)</div>
    <div style="margin-bottom:8px"><strong>Build:</strong> ${d.build ? 'ON' : 'OFF'} | Avg-down at -${d.build_trigger_pct}% → +${(d.build_factor*100).toFixed(0)}% (max ${d.max_builds})<br>Pyramid at +${d.pyramid_threshold}% and price < SMA20 → +${(d.pyramid_size*100).toFixed(0)}% (max ${d.max_pyramids})</div>
    <div><strong>Circuit Breaker:</strong> ${d.circuit_breaker_enabled ? 'ENABLED' : 'DISABLED'} | ${d.max_consecutive_losses} losses → pause ${d.loss_streak_cooldown}h | Streak: ${d.loss_streak} | ${d.trading_paused ? 'PAUSED' : 'CLEAR'}</div>
    <div style="margin-top:8px"><strong>Scan:</strong> round‑robin ${d.scan_size}/${d.total} every 30s | Min hold ${d.min_hold_hours}h | Scans: ${d.scan}</div>
  `;
}

window.toggleLots = function(sym) {
  const el = document.getElementById(`lots-${sym}`);
  if(!el) return;
  if(el.style.display === 'none' || !el.style.display) { el.style.display = 'table-row'; expandedSymbols.add(sym); }
  else { el.style.display = 'none'; expandedSymbols.delete(sym); }
};

window.manualSell = async (sym) => {
  if(confirm(`Sell ${sym} at current market price?`)) {
    const res = await api('/api/sell', {symbol: sym});
    alert(res.message || (res.success ? 'Sold' : 'Error'));
    update();
  }
};

async function update() {
  try {
    const resp = await fetch('/api/status');
    if (!resp.ok) throw new Error('HTTP '+resp.status);
    const d = await resp.json();
    if (!d || typeof d.cash === 'undefined') throw new Error('Invalid data');
    
    const dot = document.getElementById('dot'), pill = document.getElementById('pill');
    if(!d.trading_enabled) { dot.className = 'dot d-off'; pill.className = 'pill p-off'; pill.innerText = 'OFF'; }
    else if(d.trading_paused) { dot.className = 'dot d-pause'; pill.className = 'pill p-pause'; pill.innerText = 'PAUSED'; }
    else { dot.className = 'dot d-live'; pill.className = 'pill p-live'; pill.innerText = 'LIVE'; }
    
    document.getElementById('hNet').innerText = '$' + d.net.toFixed(2);
    const plEl = document.getElementById('hPl');
    plEl.innerText = (d.pl >=0 ? '+$' : '-$') + Math.abs(d.pl).toFixed(2);
    plEl.className = 'card-value ' + (d.pl>=0 ? 'pos' : 'neg');
    const wrEl = document.getElementById('hWr');
    wrEl.innerText = d.wr.toFixed(1)+'%';
    wrEl.className = 'card-value ' + (d.wr>=60 ? 'pos' : d.wr>=45 ? 'warn' : 'neg');
    document.getElementById('hVix').innerText = d.vix.toFixed(1);
    document.getElementById('hPos').innerText = d.pos;
    
    document.getElementById('cash').innerText = '$'+d.cash.toFixed(2);
    document.getElementById('hold').innerText = '$'+d.hold.toFixed(2);
    document.getElementById('wl').innerText = d.wins+'W/'+d.losses+'L';
    const streakEl = document.getElementById('streak');
    streakEl.innerText = d.loss_streak;
    streakEl.className = 'card-value ' + (d.loss_streak>=3 ? 'neg' : d.loss_streak>=1 ? 'warn' : 'pos');
    document.getElementById('tp').innerText = d.tp.toFixed(1)+'%';
    document.getElementById('sl').innerText = d.sl.toFixed(1)+'%';
    document.getElementById('dip').innerText = '>='+d.dip+'%';
    document.getElementById('size').innerText = d.size.toFixed(1)+'%';
    
    const banner = document.getElementById('banner');
    if(d.trading_paused) { banner.classList.add('show'); document.getElementById('bannerTxt').innerText = d.pause_remaining_hours>0 ? 'resumes in '+d.pause_remaining_hours.toFixed(1)+'h' : 'resuming soon'; }
    else banner.classList.remove('show');
    
    let dipsHtml = '';
    for(const b of (d.buys || [])) dipsHtml += `<div class="dip-row"><span class="symbol">${b.sym}</span><span class="dip-pct">▼${b.dip}%</span><span class="price">$${b.price}</span></div>`;
    document.getElementById('dipsList').innerHTML = dipsHtml || '<div>No qualified dips</div>';
    document.getElementById('scanBadge').innerText = '#'+d.scan;
    
    let histHtml = '';
    for(const h of (d.trade_history || []).slice().reverse()) {
      let typeClass = 'history-type';
      if(h.type==='BUY') typeClass += ' type-buy';
      else if(h.type==='TP') typeClass += ' type-tp';
      else if(h.type==='SL') typeClass += ' type-sl';
      else if(h.type==='MANUAL') typeClass += ' type-manual';
      let val = '--';
      if(h.pnl!=null) val = (h.pnl>=0?'+$':'-$')+Math.abs(h.pnl).toFixed(2);
      else if(h.position_size) val = '$'+h.position_size.toFixed(2);
      let detail = '';
      if(h.type==='BUY' && h.dip) detail = ` ${h.dip}% dip`;
      if(h.type!=='BUY' && h.hold_time) detail = ` ${h.hold_time}h`;
      histHtml += `<div class="history-row"><div><span class="${typeClass}">${h.type}</span> <strong>${h.symbol||'--'}</strong><br><span style="font-size:9px">${(h.date||'').slice(5,16)}${detail}</span></div><div class="history-detail">${val}</div></div>`;
    }
    document.getElementById('histList').innerHTML = histHtml || '<div>No trades</div>';
    document.getElementById('histBadge').innerText = d.total_trades+' total';
    
    let rows = '';
    for(const h of (d.holdings || [])) {
      const pnlClass = h.pnl>=0 ? 'pos' : 'neg';
      let trailHtml = '';
      if(h.trail_active && h.trail_price) {
        trailHtml = `<span class="pos" title="Active trailing stop">🔻 $${h.trail_price}</span>`;
      } else {
        trailHtml = `<span class="warn" title="No pyramid yet">⛔ Inactive</span>`;
      }
      rows += `<tr class="main-row" data-sym="${h.sym}">
        <td style="cursor:pointer" onclick="toggleLots('${h.sym}')">${h.sym} ${h.entries>1 ? '▼' : ''}</td>
        <td>$${h.entry}</td>
        <td>$${h.cur}</td>
        <td class="${pnlClass}">${h.pnl>=0?'+':''}${h.pnl}%</td>
        <td>$${h.val}</td>
        <td style="color:#7e8c9e">${h.entries}/${h.builds}/${h.pyramids}</td>
        <td>${trailHtml}</td>
        <td><button class="btn btn-sm" onclick="manualSell('${h.sym}')">SELL</button></td>
        </tr>`;
      if(h.lots_detail && h.lots_detail.length>1) {
        const disp = expandedSymbols.has(h.sym) ? 'table-row' : 'none';
        rows += `<tr id="lots-${h.sym}" class="lot-detail-row" style="display:${disp}"><td colspan="8"><div style="padding:4px 0">`;
        for(const lot of h.lots_detail) {
          let ltClass = 'lt-add';
          if(lot.type==='BASE') ltClass = 'lt-base';
          else if(lot.type==='BUILD') ltClass = 'lt-build';
          else if(lot.type==='PYRAMID') ltClass = 'lt-pyramid';
          rows += `<div><span class="lot-type ${ltClass}">${lot.type}</span> @$${lot.price} (${lot.shares} sh)</div>`;
        }
        rows += `</div></td></tr>`;
      }
    }
    document.getElementById('holdBody').innerHTML = rows || '<tr><td colspan="8">No positions</td></tr>';
    document.getElementById('holdBadge').innerText = d.pos+' open';
    
    document.getElementById('sid').innerText = (d.session_id||'--').slice(0,8);
    document.getElementById('pid').innerText = d.pid;
    document.getElementById('scans').innerText = d.scan;
    document.getElementById('trades').innerText = d.total_trades;
    document.getElementById('avgW').innerText = '$'+d.avg_win.toFixed(2);
    document.getElementById('avgL').innerText = '$'+d.avg_loss.toFixed(2);
    const tpEl = document.getElementById('totPnl');
    tpEl.innerText = (d.total_pnl>=0?'+$':'-$')+Math.abs(d.total_pnl).toFixed(2);
    tpEl.className = d.total_pnl>=0 ? 'pos' : 'neg';
    document.getElementById('uptime').innerText = d.uptime_hours.toFixed(1);
  } catch(e) {
    console.error('Update error:', e);
    document.getElementById('dipsList').innerHTML = '<div>Error loading data</div>';
  }
}

loadWatchlist();
loadCfg();
loadLogic();
update();
setInterval(update, 2500);
</script>
</body>
</html>'''

# ===============================
#  HTTP SERVER
# ===============================

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(HTML.encode())
            elif self.path == '/api/status':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(get_status()).encode())
            elif self.path == '/api/config':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(cfg).encode())
            elif self.path == '/keepalive':
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'ok')
            else:
                self.send_response(404)
                self.end_headers()
        except (BrokenPipeError, ConnectionAbortedError):
            pass
        except Exception as e:
            logger.error(f"GET Error: {e}")

    def do_POST(self):
        global trading, running, cash, positions, wins, losses, trade_history, buy_time, loss_streak, trading_paused
        try:
            path = self.path
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = json.loads(self.rfile.read(content_length)) if content_length > 0 else {}
            if path == '/api/start':
                trading = True
                if trading_paused:
                    trading_paused = False
                    loss_streak = 0
                logger.info("▶ Trading STARTED")
            elif path == '/api/stop':
                trading = False
                logger.info("⏸ Trading STOPPED")
            elif path == '/api/clear':
                backup = clear_all_history()
                logger.info(f"🗑️ History cleared! Backup: {backup}")
            elif path == '/api/shutdown':
                logger.info("🛑 Shutting down...")
                running = False
                save_all_state()
                threading.Thread(target=lambda: (time.sleep(1), os._exit(0))).start()
            elif path == '/api/sell':
                symbol = post_data.get('symbol', '').upper().strip()
                if not symbol:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(json.dumps({'success': False, 'message': 'No symbol'}).encode())
                    return
                success, msg = manual_sell(symbol)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'success': success, 'message': msg}).encode())
                return
            elif path == '/api/watchlist/add':
                symbol = post_data.get('symbol', '').upper().strip()
                if symbol:
                    add_to_watchlist(symbol)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok'}).encode())
                return
            elif path == '/api/watchlist/remove':
                symbol = post_data.get('symbol', '').upper().strip()
                if symbol:
                    remove_from_watchlist(symbol)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok'}).encode())
                return
            elif path == '/api/watchlist/reset':
                reset_watchlist()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok'}).encode())
                return
            elif path == '/api/config':
                key = post_data.get('key')
                value = post_data.get('value')
                if key in cfg:
                    orig_type = type(cfg[key])
                    if orig_type == bool: value = bool(value)
                    elif orig_type == int: value = int(value)
                    elif orig_type == float: value = float(value)
                    cfg[key] = value
                    save_config()
                    logger.info(f"Config updated: {key} = {value}")
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(json.dumps({'status': 'ok'}).encode())
                    return
                else:
                    self.send_response(404)
                    self.end_headers()
                    return
            elif path == '/api/reset_config':
                default_cfg = {
                    'base_size': 0.08, 'reserve': 0.10, 'base_tp': 0.0888, 'base_sl': 0.03,
                    'max_pos': 50, 'max_buys': 10, 'min_trade': 2.0, 'min_hold_hours': 8,
                    'trailing_stop_pct': 0.0666, 'heartbeat_interval': 30, 'auto_restart': True,
                    'build': True, 'build_factor': 0.5, 'pyramid_threshold': 5.0, 'pyramid_size': 0.30,
                    'max_pyramids': 999, 'max_builds': 999, 'build_trigger_pct': 2.5,
                    'wr_extreme': 0.85, 'wr_very_high': 0.75, 'wr_high': 0.65,
                    'wr_low': 0.45, 'tp_extreme': 1.30, 'tp_very_high': 1.20, 'tp_high': 1.15,
                    'tp_low': 0.90, 'size_extreme': 1.25, 'size_very_high': 1.20, 'size_high': 1.15,
                    'size_low': 0.90, 'vix_high_tp': 1.10, 'vix_elevated_tp': 1.05, 'sl_low': 1.10,
                    'vix_high_sl': 1.20, 'vix_elevated_sl': 1.05, 'vix_high_size': 1.20,
                    'vix_elevated_size': 1.05, 'vix_low_size': 0.95, 'vix_high': 25, 'vix_elevated': 18,
                    'max_consecutive_losses': 3, 'loss_streak_cooldown': 8,
                    'scan_size': 60, 'extreme_dip': 8.0, 'normal_dip': 3.0, 'high_vix_reduction': 0.5,
                    'dip_vix_critical': 8.0, 'dip_vix_high': 6.0, 'dip_vix_elevated': 5.0,
                    'dip_vix_moderate': 4.0, 'dip_vix_low': 3.0,
                    'static_stop_loss_enabled': False,
                    'trailing_only_after_pyramid': True,
                    'circuit_breaker_enabled': False,
                }
                cfg.clear()
                cfg.update(default_cfg)
                save_config()
                logger.info("Configuration reset to defaults")
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok'}).encode())
                return
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.end_headers()
        except (BrokenPipeError, ConnectionAbortedError):
            pass
        except Exception as e:
            logger.error(f"POST Error: {e}")

    def log_message(self, format, *args):
        pass

# ===============================
#  DAEMON & MAIN
# ===============================

def run_as_daemon():
    try:
        if os.fork() > 0: sys.exit(0)
    except OSError as e: logger.error(f"Fork failed: {e}"); sys.exit(1)
    os.setsid()
    os.umask(0)
    try:
        if os.fork() > 0: sys.exit(0)
    except OSError as e: logger.error(f"Second fork failed: {e}"); sys.exit(1)
    sys.stdout.flush()
    sys.stderr.flush()
    for fd in range(3, 1024):
        try: os.close(fd)
        except: pass
    devnull = open('/dev/null', 'r')
    os.dup2(devnull.fileno(), 0)
    os.dup2(devnull.fileno(), 1)
    os.dup2(devnull.fileno(), 2)
    logger.console_output = False

def find_available_port(start_port=8888, max_tries=12):
    for offset in range(max_tries):
        port = start_port + offset
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_sock.bind(('0.0.0.0', port))
            test_sock.close()
            return port
        except OSError:
            continue
    return None

def main():
    global running, PORT
    load_watchlist()
    if '--daemon' in sys.argv:
        print("Starting bot in BACKGROUND mode...")
        run_as_daemon()
        logger.info("Bot running as daemon")
    load_config()
    load_all_state()
    save_pid()
    prevent_sleep()
    setup_persistent_notification()
    threading.Thread(target=refresh_wakelock_loop, daemon=True).start()
    prevent_android_kill()
    PORT = find_available_port(8888, 12)
    if PORT is None:
        logger.error("Could not find an available port in range 8888-8899. Exiting.")
        sys.exit(1)
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    def keepalive_loop():
        time.sleep(30)
        while running:
            try:
                urllib.request.urlopen(f'http://localhost:{PORT}/keepalive', timeout=5)
            except Exception:
                pass
            time.sleep(60)
    threading.Thread(target=keepalive_loop, daemon=True).start()
    logger.info("="*50)
    logger.info("   REST BOT - OPTIMISED CONFIGURATION")
    logger.info("="*50)
    logger.info(f"   Session ID: {session_id}")
    logger.info(f"   Watchlist: {len(WATCHLIST)} symbols (round‑robin {cfg['scan_size']} symbols / 30s)")
    logger.info(f"   Starting cash: ${cash:.2f}")
    logger.info(f"   Loaded {len(trade_history)} trades, {len(positions)} positions")
    logger.info(f"   Min hold: {cfg['min_hold_hours']} hours (from last purchase)")
    logger.info(f"   Static stop loss enabled: {cfg.get('static_stop_loss_enabled', True)}")
    logger.info(f"   Trailing stop only after pyramid: {cfg.get('trailing_only_after_pyramid', True)}")
    logger.info(f"   Circuit breaker enabled: {cfg.get('circuit_breaker_enabled', True)}")
    logger.info("="*50)
    logger.info(f"   Dashboard: http://localhost:{PORT}")
    logger.info(f"   Log file: {LOG_FILE}")
    logger.info(f"   PID file: {PID_FILE}")
    logger.info(f"   Watchlist file: {WATCHLIST_FILE}")
    logger.info("="*50)
    threading.Thread(target=trading_loop, daemon=True).start()
    if '--daemon' not in sys.argv:
        try:
            webbrowser.open(f'http://localhost:{PORT}')
            logger.info("   Dashboard opened automatically")
        except:
            logger.info(f"   Please open http://localhost:{PORT} manually")
    def shutdown_handler(signum, frame):
        logger.info("\n   Shutting down gracefully...")
        save_all_state()
        save_config()
        save_watchlist()
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
                logger.info(f"Removed PID file {PID_FILE}")
        except Exception as e:
            logger.error(f"Failed to remove PID file: {e}")
        global running
        running = False
        sys.exit(0)
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    atexit.register(lambda: (save_all_state(), save_config(), save_watchlist()))
    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown_handler(None, None)

if __name__ == '__main__':
    main()
