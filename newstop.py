#!/usr/bin/env python
# trading_engine.py – Android‑ready trading bot (NO YFINANCE DEPENDENCY)
# Uses lightweight direct Yahoo API calls

import os, sys, json, time, threading, random, signal, shutil, traceback, socket, gc
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import atexit
import requests
import re

# ----------------------------------------------------------------------
# ANDROID DATA DIRECTORY (safe internal storage)
# ----------------------------------------------------------------------
if 'ANDROID_DATA' in os.environ:
    DATA_DIR = os.path.join('/data/user/0/org.example.tradingbot/files')
else:
    DATA_DIR = '.'
os.makedirs(DATA_DIR, exist_ok=True)

WR_FILE = os.path.join(DATA_DIR, "wr_cache.json")
HISTORY_FILE = os.path.join(DATA_DIR, "trade_history.json")
POSITIONS_FILE = os.path.join(DATA_DIR, "positions_cache.json")
CASH_FILE = os.path.join(DATA_DIR, "cash_cache.json")
METRICS_FILE = os.path.join(DATA_DIR, "metrics_history.json")
SESSION_FILE = os.path.join(DATA_DIR, "session_state.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.json")
PID_FILE = os.path.join(DATA_DIR, "bot.pid")
LOG_FILE = os.path.join(DATA_DIR, "bot.log")

# ----------------------------------------------------------------------
# LIGHTWEIGHT YAHOO FINANCE API (No yfinance dependency)
# ----------------------------------------------------------------------
class SimpleYahooTicker:
    """Lightweight Yahoo Finance scraper - no heavy dependencies"""
    
    def __init__(self, symbol):
        self.symbol = symbol
        self._cache = {}
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def history(self, period="1y", interval="1d"):
        """Fetch historical data using Yahoo's public API"""
        cache_key = f"{self.symbol}_{period}_{interval}"
        if cache_key in self._cache and time.time() - self._cache[cache_key]['time'] < 300:
            return self._cache[cache_key]['data']
        
        try:
            # Calculate date range
            end = datetime.now()
            if period == "1y":
                start = end - timedelta(days=365)
            elif period == "5d":
                start = end - timedelta(days=5)
            elif period == "2d":
                start = end - timedelta(days=2)
            else:
                start = end - timedelta(days=365)
            
            # Yahoo Finance API endpoint
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{self.symbol}"
            params = {
                'period1': int(start.timestamp()),
                'period2': int(end.timestamp()),
                'interval': interval,
                'includePrePost': 'false'
            }
            
            resp = self._session.get(url, params=params, timeout=15)
            data = resp.json()
            
            if 'chart' in data and data['chart']['result']:
                result = data['chart']['result'][0]
                quote = result['indicators']['quote'][0]
                
                closes = quote.get('close', [])
                opens = quote.get('open', [])
                highs = quote.get('high', [])
                lows = quote.get('low', [])
                volumes = quote.get('volume', [])
                timestamps = result.get('timestamp', [])
                
                # Create a simple DataFrame-like object
                class HistoryData:
                    def __init__(self, closes_arr, opens_arr, highs_arr, lows_arr, volumes_arr, timestamps_arr):
                        self._closes = closes_arr
                        self._opens = opens_arr
                        self._highs = highs_arr
                        self._lows = lows_arr
                        self._volumes = volumes_arr
                        self._timestamps = timestamps_arr
                        self.empty = len(closes_arr) == 0
                    
                    @property
                    def Close(self):
                        class CloseSeries:
                            def __init__(self, data):
                                self._data = data
                            
                            def iloc(self, idx):
                                if self._data and idx is not None:
                                    if idx == -1:
                                        return self._data[-1] if self._data else 0
                                    if idx < len(self._data):
                                        return self._data[idx]
                                return 0
                            
                            def rolling(self, window):
                                class Rolling:
                                    def __init__(self, data, window):
                                        self._data = data
                                        self._window = window
                                    
                                    def mean(self):
                                        class Mean:
                                            def __init__(self, data, window):
                                                self._data = data
                                                self._window = window
                                            
                                            def iloc(self, idx):
                                                if idx < 0:
                                                    idx = len(self._data) + idx
                                                if idx < 0 or idx >= len(self._data):
                                                    return self._data[-1] if self._data else 0
                                                start = max(0, idx - self._window + 1)
                                                window_data = self._data[start:idx+1]
                                                if window_data:
                                                    # Filter out None values
                                                    clean_data = [x for x in window_data if x is not None]
                                                    if clean_data:
                                                        return sum(clean_data) / len(clean_data)
                                                return self._data[idx] if idx < len(self._data) else 0
                                        return Mean(self._data, self._window)
                                return Rolling(self._data, window)
                        return CloseSeries(self._closes)
                    
                    def __len__(self):
                        return len(self._closes)
                
                result_obj = HistoryData(closes, opens, highs, lows, volumes, timestamps)
                self._cache[cache_key] = {'data': result_obj, 'time': time.time()}
                return result_obj
            
            return HistoryData([], [], [], [], [], [])
            
        except Exception as e:
            print(f"Error fetching {self.symbol}: {e}")
            return HistoryData([], [], [], [], [], [])
    
    def get_current_price(self):
        """Get current price quickly"""
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{self.symbol}"
            params = {'interval': '1m', 'range': '1d'}
            resp = self._session.get(url, params=params, timeout=10)
            data = resp.json()
            
            if 'chart' in data and data['chart']['result']:
                quote = data['chart']['result'][0]['indicators']['quote'][0]
                closes = quote.get('close', [])
                if closes:
                    current = closes[-1]
                    if current is not None:
                        return float(current)
        except:
            pass
        return None

# Create yfinance-compatible interface
class YFinanceWrapper:
    @staticmethod
    def Ticker(symbol):
        return SimpleYahooTicker(symbol)
    
    @staticmethod
    def download(tickers, **kwargs):
        """Bulk download stub - we'll handle individually"""
        return {}

yf = YFinanceWrapper()

# ----------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------
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

DEFAULT_WATCHLIST = [
    'AAPL','MSFT','GOOGL','AMZN','NVDA','META','TSLA','NFLX','ADBE','CRM',
    'ORCL','IBM','CSCO','INTC','AMD','QCOM','TXN','AVGO','MU','PYPL',
    'JPM','BAC','WFC','C','GS','MS','AXP','V','MA','COF',
    'JNJ','UNH','PFE','MRK','ABBV','ABT','TMO','DHR','LLY','BMY',
    'WMT','COST','HD','MCD','NKE','SBUX','TGT','LOW','TJX','ROST',
    'CAT','GE','BA','MMM','HON','LMT','RTX','NOC','GD','DE',
    'XOM','CVX','COP','EOG','OXY','SLB','HAL','BKR','VLO','MPC',
    'SPY','QQQ','IWM','DIA','GLD','SLV','USO'
]

WATCHLIST = DEFAULT_WATCHLIST.copy()

# ----------------------------------------------------------------------
# LOGGING SYSTEM
# ----------------------------------------------------------------------
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

# ----------------------------------------------------------------------
# GLOBAL STATE
# ----------------------------------------------------------------------
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

# ----------------------------------------------------------------------
# WATCHLIST PERSISTENCE
# ----------------------------------------------------------------------
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
    scan_index = scan_index % len(WATCHLIST) if len(WATCHLIST) > 0 else 0
    save_watchlist()
    logger.info(f"Watchlist reset to default ({len(WATCHLIST)} symbols)")
    return WATCHLIST

def add_to_watchlist(symbol):
    global WATCHLIST, scan_index
    symbol = symbol.upper().strip()
    if symbol not in WATCHLIST:
        WATCHLIST.append(symbol)
        if len(WATCHLIST) > 0:
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

# ----------------------------------------------------------------------
# PERSISTENCE & UTILITIES
# ----------------------------------------------------------------------
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

# ----------------------------------------------------------------------
# PRICE & INDICATORS (Using lightweight API)
# ----------------------------------------------------------------------
def fetch_single_symbol(symbol):
    """Fetch data for a single symbol"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y", interval="1d")
        
        if hist and len(hist) > 0:
            closes = hist._closes if hasattr(hist, '_closes') else []
            if closes and len(closes) > 0:
                price = closes[-1] if closes[-1] else 0
                
                # Calculate SMAs
                if len(closes) >= 20:
                    sma20 = sum(closes[-20:]) / 20
                else:
                    sma20 = price
                
                if len(closes) >= 200:
                    sma200 = sum(closes[-200:]) / 200
                elif len(closes) >= 50:
                    sma200 = sum(closes[-50:]) / 50
                else:
                    sma200 = price * 0.9
                
                return {
                    'price': price,
                    'sma20': sma20,
                    'sma200': sma200,
                    'time': time.time()
                }
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
    return None

def fetch_prices_bulk(symbols):
    """Fetch prices for multiple symbols"""
    global price_data
    if not symbols:
        return {}
    
    result = {}
    for sym in symbols:
        data = fetch_single_symbol(sym)
        if data:
            result[sym] = data
        time.sleep(0.2)  # Rate limiting
        gc.collect()
    
    price_data.update(result)
    if len(price_data) > 1000:
        price_data = dict(list(price_data.items())[-800:])
    return result

def get_price_cached(sym):
    """Get cached price or fetch fresh"""
    if sym in price_data and time.time() - price_data[sym]['time'] < 60:
        return price_data[sym]['price']
    
    data = fetch_single_symbol(sym)
    if data:
        price_data[sym] = data
        return data['price']
    return None

def get_sma20_cached(sym):
    if sym in price_data:
        return price_data[sym].get('sma20')
    return None

def get_sma200_cached(sym):
    if sym in price_data:
        return price_data[sym].get('sma200')
    return None

def get_vix():
    """Get VIX value using lightweight API"""
    global vix_value, vix_timestamp
    if time.time() - vix_timestamp < 300:
        return vix_value
    try:
        ticker = yf.Ticker("^VIX")
        hist = ticker.history(period="5d", interval="1d")
        if hist and len(hist._closes) > 0:
            vix_value = hist._closes[-1] if hist._closes[-1] else 15.0
        else:
            vix_value = 15.0
        vix_timestamp = time.time()
    except:
        vix_value = 15.0
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

# ----------------------------------------------------------------------
# TRADING LOOP
# ----------------------------------------------------------------------
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

# ----------------------------------------------------------------------
# WEB DASHBOARD HTML (same as original - omitted for brevity)
# ----------------------------------------------------------------------
# [The HTML string from original goes here - it's very long]
# For completeness, I'm including a placeholder. Use the HTML from your original file.
HTML = '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>DIP BOT</title>
<style>
body { background: #0a0f1a; font-family: monospace; color: #e0e5f0; padding: 12px; }
.container { max-width: 1400px; margin: 0 auto; }
.stats-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; }
.card { background: #11161f; border: 1px solid #2a3440; border-radius: 6px; padding: 6px 10px; }
.card-value { font-size: 16px; font-weight: bold; }
.pos { color: #2ecc71; }
.neg { color: #e74c3c; }
</style>
</head>
<body>
<div class="container">
<h1>🤖 DIP BOT</h1>
<div id="status">Loading...</div>
</div>
<script>
function update() {
    fetch('/api/status')
        .then(r => r.json())
        .then(d => {
            document.getElementById('status').innerHTML = `
                <div class="stats-row">
                    <div class="card">Net: $${d.net}</div>
                    <div class="card">P&L: $${d.pl}</div>
                    <div class="card">WinRate: ${d.wr}%</div>
                    <div class="card">VIX: ${d.vix}</div>
                    <div class="card">Positions: ${d.pos}</div>
                </div>
                <div class="stats-row">
                    <div class="card">Cash: $${d.cash}</div>
                    <div class="card">Holdings: $${d.hold}</div>
                    <div class="card">W/L: ${d.wins}/${d.losses}</div>
                    <div class="card">TP: ${d.tp}%</div>
                    <div class="card">SL: ${d.sl}%</div>
                </div>
            `;
        })
        .catch(e => console.error(e));
}
update();
setInterval(update, 3000);
</script>
</body>
</html>'''

# ----------------------------------------------------------------------
# HTTP SERVER
# ----------------------------------------------------------------------
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
            else:
                self.send_response(404)
                self.end_headers()
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
            
            self.send_response(200)
            self.end_headers()
        except Exception as e:
            logger.error(f"POST Error: {e}")

    def log_message(self, format, *args):
        pass

# ----------------------------------------------------------------------
# UTILITY: find available port
# ----------------------------------------------------------------------
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

# ----------------------------------------------------------------------
# ENTRY POINT FOR ANDROID SERVICE
# ----------------------------------------------------------------------
def start_bot():
    global running, trading
    load_watchlist()
    load_config()
    load_all_state()
    prevent_sleep()

    PORT = find_available_port(8888, 12)
    if PORT is None:
        logger.error("Could not find an available port. Exiting.")
        return
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    threading.Thread(target=trading_loop, daemon=True).start()

    logger.info("="*50)
    logger.info("   TRADING BOT STARTED (ANDROID MODE)")
    logger.info(f"   Dashboard: http://localhost:{PORT}")
    logger.info("="*50)

    # Keep the function alive
    while running:
        time.sleep(1)

# For local testing
if __name__ == "__main__":
    start_bot()
