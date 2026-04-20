#!/usr/bin/env python
# main.py – DIP BOT: Kivy Android APK wrapper
# Trading logic runs as a background thread; Kivy WebView shows the dashboard.

import os, sys, json, time, threading, random, signal, shutil, traceback, socket, gc
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import atexit

# ── Android / Kivy imports (graceful fallback on desktop) ──────────────────
try:
    import android                        # noqa: F401 – exists only on device
    from android.permissions import request_permissions, Permission
    from jnius import autoclass
    ANDROID = True
except ImportError:
    ANDROID = False

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

# WebView via android.webview (Kivy-for-Android provides this)
try:
    from kivy.uix.webview import WebView  # available in newer KivyMD / p4a builds
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False

try:
    import yfinance as yf
except ImportError:
    os.system('pip install yfinance --quiet')
    import yfinance as yf

# ═══════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

def _data_dir():
    """Return a writable directory on both Android and desktop."""
    if ANDROID:
        from android.storage import app_storage_path
        return app_storage_path()
    return os.path.dirname(os.path.abspath(__file__))

DATA = _data_dir()

WR_FILE        = os.path.join(DATA, "wr_cache.json")
HISTORY_FILE   = os.path.join(DATA, "trade_history.json")
POSITIONS_FILE = os.path.join(DATA, "positions_cache.json")
CASH_FILE      = os.path.join(DATA, "cash_cache.json")
METRICS_FILE   = os.path.join(DATA, "metrics_history.json")
SESSION_FILE   = os.path.join(DATA, "session_state.json")
CONFIG_FILE    = os.path.join(DATA, "config.json")
WATCHLIST_FILE = os.path.join(DATA, "watchlist.json")
LOG_FILE       = os.path.join(DATA, "bot.log")

cfg = {
    'base_size': 0.08, 'reserve': 0.10, 'base_tp': 0.0888, 'base_sl': 0.03,
    'max_pos': 50, 'max_buys': 10, 'min_trade': 2.0, 'min_hold_hours': 8,
    'trailing_stop_pct': 0.0666, 'heartbeat_interval': 30, 'auto_restart': True,
    'build': True, 'build_factor': 0.5, 'pyramid_threshold': 5.0,
    'pyramid_size': 0.30, 'max_pyramids': 999, 'max_builds': 999,
    'build_trigger_pct': 2.5,
    'wr_extreme': 0.85, 'wr_very_high': 0.75, 'wr_high': 0.65, 'wr_low': 0.45,
    'tp_extreme': 1.30, 'tp_very_high': 1.20, 'tp_high': 1.15, 'tp_low': 0.90,
    'size_extreme': 1.25, 'size_very_high': 1.20, 'size_high': 1.15, 'size_low': 0.90,
    'vix_high_tp': 1.10, 'vix_elevated_tp': 1.05, 'sl_low': 1.10,
    'vix_high_sl': 1.20, 'vix_elevated_sl': 1.05,
    'vix_high_size': 1.20, 'vix_elevated_size': 1.05, 'vix_low_size': 0.95,
    'vix_high': 25, 'vix_elevated': 18,
    'max_consecutive_losses': 3, 'loss_streak_cooldown': 8,
    'circuit_breaker_enabled': False,
    'scan_size': 60, 'extreme_dip': 8.0, 'normal_dip': 3.0, 'high_vix_reduction': 0.5,
    'dip_vix_critical': 8.0, 'dip_vix_high': 6.0, 'dip_vix_elevated': 5.0,
    'dip_vix_moderate': 4.0, 'dip_vix_low': 3.0,
    'static_stop_loss_enabled': False, 'trailing_only_after_pyramid': True,
}

# ═══════════════════════════════════════════════════════════════════════════
#  DEFAULT WATCHLIST  (unchanged from original)
# ═══════════════════════════════════════════════════════════════════════════

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
    'NEE','DUK','SO','D','AEP','EXC','SRE','XEL','WEC','PPL',
]
WATCHLIST = DEFAULT_WATCHLIST.copy()

# ═══════════════════════════════════════════════════════════════════════════
#  LOGGER
# ═══════════════════════════════════════════════════════════════════════════

class Logger:
    def __init__(self):
        self.console_output = True
    def _write(self, level, msg):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{ts}] [{level}] {msg}\n"
        try:
            with open(LOG_FILE, 'a') as f:
                f.write(line)
        except Exception:
            pass
        if self.console_output:
            print(line, end='')
    def info(self, m):    self._write("INFO", m)
    def error(self, m):   self._write("ERROR", m)
    def warning(self, m): self._write("WARNING", m)

logger = Logger()

# ═══════════════════════════════════════════════════════════════════════════
#  GLOBAL STATE
# ═══════════════════════════════════════════════════════════════════════════

running          = True
trading          = True
cash             = 1000.0
positions        = {}
buy_time         = {}
trailing_state   = {}
wins = losses    = 0
trade_history    = []
session_id       = datetime.now().strftime('%Y%m%d_%H%M%S')
start_time       = datetime.now().isoformat()
start_timestamp  = time.time()
cur_size         = cfg['base_size']
buy_list         = []
scan_num         = 0
metrics_history  = []
loss_streak      = 0
trading_paused   = False
pause_end_time   = 0
price_data       = {}
vix_value        = 15.0
vix_timestamp    = 0
scan_index       = 0
PORT             = 8888

# ═══════════════════════════════════════════════════════════════════════════
#  WATCHLIST PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════════

def save_watchlist():
    try:
        with open(WATCHLIST_FILE, 'w') as f:
            json.dump(WATCHLIST, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving watchlist: {e}")

def load_watchlist():
    global WATCHLIST
    try:
        with open(WATCHLIST_FILE, 'r') as f:
            loaded = json.load(f)
            if isinstance(loaded, list) and loaded:
                WATCHLIST = loaded
    except FileNotFoundError:
        WATCHLIST = DEFAULT_WATCHLIST.copy()
        save_watchlist()
    except Exception as e:
        logger.error(f"Error loading watchlist: {e}")
        WATCHLIST = DEFAULT_WATCHLIST.copy()

def reset_watchlist():
    global WATCHLIST, scan_index
    WATCHLIST = DEFAULT_WATCHLIST.copy()
    scan_index = scan_index % len(WATCHLIST)
    save_watchlist()
    return WATCHLIST

def add_to_watchlist(symbol):
    global WATCHLIST, scan_index
    symbol = symbol.upper().strip()
    if symbol not in WATCHLIST:
        WATCHLIST.append(symbol)
        scan_index = scan_index % len(WATCHLIST)
        save_watchlist()
        return True
    return False

def remove_from_watchlist(symbol):
    global WATCHLIST, scan_index
    symbol = symbol.upper().strip()
    if symbol in WATCHLIST:
        WATCHLIST.remove(symbol)
        scan_index = scan_index % max(len(WATCHLIST), 1)
        save_watchlist()
        return True
    return False

# ═══════════════════════════════════════════════════════════════════════════
#  PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════════

def load_config():
    global cfg
    try:
        with open(CONFIG_FILE, 'r') as f:
            cfg.update(json.load(f))
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.error(f"Error loading config: {e}")

def save_config():
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving config: {e}")

def save_all_state():
    global cash, positions, wins, losses, trade_history, metrics_history
    try:
        with open(WR_FILE, 'w') as f:
            json.dump({'wins': wins, 'losses': losses, 'last_updated': datetime.now().isoformat()}, f, indent=2)
        recent = trade_history[-1000:]
        with open(HISTORY_FILE, 'w') as f:
            json.dump(recent, f, indent=2)
        pd = {s: {'lots': lots, 'buy_time': buy_time.get(s, 0)} for s, lots in positions.items()}
        with open(POSITIONS_FILE, 'w') as f:
            json.dump(pd, f, indent=2)
        with open(CASH_FILE, 'w') as f:
            json.dump({'cash': cash, 'initial_cash': 1000.0, 'last_updated': datetime.now().isoformat()}, f, indent=2)
        with open(METRICS_FILE, 'w') as f:
            json.dump(metrics_history[-1000:], f, indent=2)
        with open(SESSION_FILE, 'w') as f:
            json.dump({
                'session_id': session_id, 'start_time': start_time,
                'total_trades': len(trade_history), 'total_wins': wins, 'total_losses': losses,
                'current_cash': cash, 'positions_count': len(positions),
                'last_save': datetime.now().isoformat(), 'uptime': time.time() - start_timestamp,
                'loss_streak': loss_streak, 'trading_paused': trading_paused,
                'trailing_state': trailing_state,
            }, f, indent=2)
    except Exception as e:
        logger.error(f"Save error: {e}")

def load_all_state():
    global cash, positions, wins, losses, trade_history, metrics_history
    global buy_time, session_id, start_time, loss_streak, trading_paused, trailing_state
    try:
        with open(SESSION_FILE, 'r') as f:
            d = json.load(f)
            session_id = d.get('session_id', session_id)
            start_time = d.get('start_time', start_time)
            loss_streak = d.get('loss_streak', 0)
            trading_paused = d.get('trading_paused', False)
            trailing_state = d.get('trailing_state', {})
    except Exception:
        pass
    try:
        with open(WR_FILE, 'r') as f:
            d = json.load(f)
            wins, losses = d.get('wins', 0), d.get('losses', 0)
    except Exception:
        wins = losses = 0
    try:
        with open(HISTORY_FILE, 'r') as f:
            trade_history = json.load(f)
    except Exception:
        trade_history = []
    try:
        with open(POSITIONS_FILE, 'r') as f:
            pd = json.load(f)
            positions = {s: d['lots'] for s, d in pd.items()}
            buy_time  = {s: d.get('buy_time', 0) for s, d in pd.items()}
    except Exception:
        positions = {}; buy_time = {}
    try:
        with open(CASH_FILE, 'r') as f:
            cash = json.load(f).get('cash', 1000.0)
    except Exception:
        cash = 1000.0
    try:
        with open(METRICS_FILE, 'r') as f:
            metrics_history = json.load(f)
    except Exception:
        metrics_history = []

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
    wr = (wins / total * 100) if total > 0 else 0
    hv = sum((sum(l['shares'] for l in lots) * (get_price_cached(sym) or 0))
             for sym, lots in positions.items())
    metrics_history.append({
        'timestamp': time.time(), 'datetime': datetime.now().isoformat(),
        'cash': cash, 'holdings': hv, 'net': cash + hv,
        'positions': len(positions), 'wins': wins, 'losses': losses, 'win_rate': wr,
        'loss_streak': loss_streak, 'trading_paused': trading_paused,
        'vix': get_vix(), 'session_id': session_id, 'uptime': time.time() - start_timestamp,
    })
    if len(metrics_history) % 10 == 0:
        save_all_state()

def clear_all_history():
    global cash, positions, wins, losses, trade_history, metrics_history
    global buy_time, session_id, start_time, loss_streak, trading_paused, trailing_state
    bu = os.path.join(DATA, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(bu, exist_ok=True)
    for fp in [WR_FILE, HISTORY_FILE, POSITIONS_FILE, CASH_FILE, METRICS_FILE, SESSION_FILE]:
        if os.path.exists(fp):
            shutil.copy(fp, os.path.join(bu, os.path.basename(fp)))
    cash = 1000.0; positions = {}; buy_time = {}
    wins = losses = loss_streak = 0
    trading_paused = False; trailing_state = {}
    trade_history = []; metrics_history = []
    session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    start_time  = datetime.now().isoformat()
    save_all_state()
    return bu

# ═══════════════════════════════════════════════════════════════════════════
#  PRICE & INDICATORS
# ═══════════════════════════════════════════════════════════════════════════

def fetch_prices_bulk(symbols):
    global price_data
    if not symbols:
        return {}
    result = {}
    for i in range(0, len(symbols), 20):
        chunk = symbols[i:i + 20]
        try:
            data = yf.download(
                tickers=chunk, period="1y", interval="1d",
                group_by='ticker', threads=False, progress=False, timeout=15,
            )
            for sym in chunk:
                try:
                    if sym in data and data[sym] is not None and not data[sym].empty:
                        df = data[sym]
                        if len(df) > 0:
                            price  = float(df['Close'].iloc[-1])
                            sma20  = float(df['Close'].rolling(20).mean().iloc[-1]) if len(df) >= 20 else price
                            sma200 = float(df['Close'].rolling(200).mean().iloc[-1]) if len(df) >= 200 else (
                                     float(df['Close'].rolling(50).mean().iloc[-1])  if len(df) >= 50 else price * 0.9)
                            result[sym] = {'price': price, 'sma20': sma20, 'sma200': sma200, 'time': time.time()}
                except Exception:
                    continue
            time.sleep(0.3)
            gc.collect()
        except Exception as e:
            logger.error(f"Fetch error: {e}")
    price_data.update(result)
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
            price_data.setdefault(sym, {})
            price_data[sym]['price'] = price
            price_data[sym]['time']  = time.time()
            return price
    except Exception:
        pass
    return None

def get_sma20_cached(sym):  return price_data[sym].get('sma20')  if sym in price_data else None
def get_sma200_cached(sym): return price_data[sym].get('sma200') if sym in price_data else None

def get_vix():
    global vix_value, vix_timestamp
    if time.time() - vix_timestamp < 300:
        return vix_value
    try:
        d = yf.Ticker("^VIX").history(period="5d", timeout=10)
        vix_value = float(d['Close'].iloc[-1]) if not d.empty else 15.0
        vix_timestamp = time.time()
    except Exception:
        vix_value = 15.0
    return vix_value

def get_vix_parameters():
    v = get_vix()
    if   v > 30: return 8.0, 0.40, 1.30, "CRITICAL"
    elif v > 25: return 6.0, 0.50, 1.20, "HIGH"
    elif v > 20: return 5.0, 0.70, 1.10, "ELEVATED"
    elif v > 18: return 4.0, 0.85, 1.05, "MODERATE"
    else:        return 3.0, 1.00, 1.00, "LOW"

def get_required_dip():
    v = get_vix()
    if   v > 30: return cfg.get('dip_vix_critical', 8.0)
    elif v > 25: return cfg.get('dip_vix_high', 6.0)
    elif v > 20: return cfg.get('dip_vix_elevated', 5.0)
    elif v > 18: return cfg.get('dip_vix_moderate', 4.0)
    else:        return cfg.get('dip_vix_low', 3.0)

def update_params():
    global cur_size
    total = wins + losses
    wr    = wins / total if total > 0 else 0.5
    v     = get_vix()
    _, _, sl_mult, _ = get_vix_parameters()
    if   wr > cfg['wr_extreme']:   tp_w, sz_w, wr_effect = cfg['tp_extreme'],   cfg['size_extreme'],   "AGGRESSIVE"
    elif wr > cfg['wr_very_high']: tp_w, sz_w, wr_effect = cfg['tp_very_high'], cfg['size_very_high'], "BULLISH"
    elif wr > cfg['wr_high']:      tp_w, sz_w, wr_effect = cfg['tp_high'],      cfg['size_high'],      "CONFIDENT"
    elif wr < cfg['wr_low']:       tp_w, sz_w, wr_effect = cfg['tp_low'],       cfg['size_low'],       "DEFENSIVE"
    else:                          tp_w = sz_w = 1.0;                            wr_effect = "NEUTRAL"
    if   v > cfg['vix_high']:      tp_v, sl_v, size_v = cfg['vix_high_tp'],      cfg['vix_high_sl'],      cfg['vix_high_size']
    elif v > cfg['vix_elevated']:  tp_v, sl_v, size_v = cfg['vix_elevated_tp'],  cfg['vix_elevated_sl'],  cfg['vix_elevated_size']
    else:                          tp_v = sl_v = 1.0;  size_v = cfg['vix_low_size']
    tp = cfg['base_tp'] * tp_w * tp_v
    sl = cfg['base_sl'] * (cfg['sl_low'] if wr < cfg['wr_low'] else 1.0) * sl_v
    cur_size = cfg['base_size'] * sz_w * size_v
    if loss_streak > 0:
        cur_size *= max(1 - loss_streak * 0.15, cfg['base_size'] * 0.3 / cfg['base_size'])
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
        trailing_state[sym] = {
            'highest': entry_avg,
            'trailing': entry_avg * (1 - cfg['trailing_stop_pct']),
            'has_pyramid': False,
        }
    if current_price > trailing_state[sym]['highest']:
        trailing_state[sym]['highest'] = current_price
        trailing_state[sym]['trailing'] = current_price * (1 - cfg['trailing_stop_pct'])
    return trailing_state[sym]['trailing']

# ═══════════════════════════════════════════════════════════════════════════
#  TRADING LOGIC  (identical to original, no subprocess / daemon calls)
# ═══════════════════════════════════════════════════════════════════════════

def check_exits():
    global cash, wins, losses, loss_streak, trading_paused, pause_end_time
    to_remove = []
    tp, sl, _, _, _ = update_params()
    for sym, lots in list(positions.items()):
        price = get_price_cached(sym)
        if not price: continue
        shares = sum(l['shares'] for l in lots)
        avg    = sum(l['shares'] * l['price'] for l in lots) / shares
        if not can_sell(sym): continue
        if price >= avg * (1 + tp):
            pnl = shares * (price - avg)
            cash += shares * price
            wins += 1
            to_remove.append(sym)
            if loss_streak > 0:
                loss_streak = 0
                trading_paused = False
            add_to_history({'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'symbol': sym,
                'type': 'TP', 'entry': round(avg, 2), 'exit': round(price, 2),
                'pnl': round(pnl, 2), 'shares': round(shares, 2),
                'hold_time': round((time.time() - buy_time.get(sym, time.time())) / 3600, 1)})
            logger.info(f"TP {sym}: +${pnl:.2f}")
        else:
            trail_triggered = False
            if cfg['trailing_stop_pct'] > 0:
                if not cfg['trailing_only_after_pyramid'] or (
                        sym in trailing_state and trailing_state[sym].get('has_pyramid', False)):
                    trail_sl = update_trailing_stop(sym, price, avg)
                    if price <= trail_sl:
                        trail_triggered = True
                        pnl  = shares * (price - avg)
                        cash += shares * price
                        losses += 1
                        to_remove.append(sym)
                        loss_streak += 1
                        if cfg.get('circuit_breaker_enabled') and loss_streak >= cfg['max_consecutive_losses']:
                            trading_paused = True
                            pause_end_time = time.time() + cfg['loss_streak_cooldown'] * 3600
                        add_to_history({'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'symbol': sym,
                            'type': 'SL', 'entry': round(avg, 2), 'exit': round(price, 2),
                            'pnl': round(pnl, 2), 'shares': round(shares, 2),
                            'hold_time': round((time.time() - buy_time.get(sym, time.time())) / 3600, 1)})
            if not trail_triggered and cfg['static_stop_loss_enabled'] and price <= avg * (1 - sl):
                pnl  = shares * (price - avg)
                cash += shares * price
                losses += 1
                to_remove.append(sym)
                loss_streak += 1
                if cfg.get('circuit_breaker_enabled') and loss_streak >= cfg['max_consecutive_losses']:
                    trading_paused = True
                    pause_end_time = time.time() + cfg['loss_streak_cooldown'] * 3600
                add_to_history({'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'symbol': sym,
                    'type': 'SL', 'entry': round(avg, 2), 'exit': round(price, 2),
                    'pnl': round(pnl, 2), 'shares': round(shares, 2),
                    'hold_time': round((time.time() - buy_time.get(sym, time.time())) / 3600, 1)})
    for sym in to_remove:
        positions.pop(sym, None); buy_time.pop(sym, None); trailing_state.pop(sym, None)
    if to_remove:
        save_all_state()

def check_entries():
    global cash, trading_paused, loss_streak
    if trading_paused:
        if time.time() < pause_end_time: return
        trading_paused = False
        loss_streak = 0
    if not trading or len(positions) >= cfg['max_pos']: return
    avail = available_cash()
    if avail < cfg['min_trade']: return
    tp, sl, _, _, _ = update_params()
    trade_val = avail * cur_size
    if trade_val < cfg['min_trade']: return
    candidates = buy_list[:cfg['max_buys']]
    bought = 0
    for dip_info in candidates:
        if bought >= cfg['max_buys'] or len(positions) >= cfg['max_pos']: break
        sym   = dip_info['sym']
        price = get_price_cached(sym) or dip_info['price']
        if not price: continue
        existing = positions.get(sym)
        add_type = None
        add_size_mult = 1.0
        if existing and cfg['build']:
            total_shares = sum(l['shares'] for l in existing)
            avg = sum(l['shares'] * l['price'] for l in existing) / total_shares
            pnl_pct = (price - avg) / avg * 100
            build_count   = sum(1 for l in existing if l.get('is_build', False))
            pyramid_count = sum(1 for l in existing if l.get('is_pyramid', False))
            if pnl_pct <= -cfg.get('build_trigger_pct', 2.5) and build_count < cfg.get('max_builds', 3):
                add_type, add_size_mult = "AVG_DOWN", cfg['build_factor']
            elif pnl_pct >= cfg['pyramid_threshold']:
                s20 = get_sma20_cached(sym)
                if s20 and price < s20 and pyramid_count < cfg['max_pyramids']:
                    add_type, add_size_mult = "PYRAMID", cfg['pyramid_size']
        if add_type or (sym not in positions and can_buy(sym, price)):
            s20 = get_sma20_cached(sym)
            dip  = ((s20 - price) / s20 * 100) if s20 else 0
            size = max(min(trade_val * add_size_mult, avail), cfg['min_trade'])
            if size < cfg['min_trade']: continue
            shares = size / price
            lot = {'shares': shares, 'price': price}
            if add_type == "PYRAMID":
                lot['is_pyramid'] = True
                trailing_state.setdefault(sym, {'highest': price,
                    'trailing': price * (1 - cfg['trailing_stop_pct']), 'has_pyramid': False})
                trailing_state[sym]['has_pyramid'] = True
            if add_type == "AVG_DOWN":
                lot['is_build'] = True
            positions.setdefault(sym, []).append(lot)
            buy_time[sym] = time.time()
            trailing_state.setdefault(sym, {'highest': price,
                'trailing': price * (1 - cfg['trailing_stop_pct']), 'has_pyramid': False})
            cash   -= size
            bought += 1
            avail   = available_cash()
            trade_val = avail * cur_size
            entry_type = add_type if add_type else "BUY"
            add_to_history({'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'symbol': sym,
                'type': entry_type, 'entry': round(price, 2), 'shares': round(shares, 2),
                'dip': round(dip, 1), 'position_size': round(size, 2)})
            logger.info(f"{entry_type} {sym} @ {price:.2f} (Dip:{dip:.1f}%, Size:${size:.2f})")
            if trade_val < cfg['min_trade']: break
    if bought:
        save_all_state()

def scan():
    global buy_list, scan_num, scan_index
    scan_num += 1
    min_dip = get_required_dip()
    if scan_num == 1:
        candidates = WATCHLIST.copy()
    else:
        cs    = cfg['scan_size']
        start = scan_index
        end   = start + cs
        candidates = WATCHLIST[start:] + WATCHLIST[:end - len(WATCHLIST)] if end >= len(WATCHLIST) else WATCHLIST[start:end]
        scan_index = (scan_index + cs) % len(WATCHLIST)
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
    logger.info(f"Scan #{scan_num}: {len(buy_list)} candidates from {len(candidates)} symbols")

def manual_sell(symbol):
    global cash, wins, losses
    symbol = symbol.upper()
    if symbol not in positions:
        return False, "Position not found"
    lots  = positions[symbol]
    price = get_price_cached(symbol)
    if not price:
        return False, "Cannot get current price"
    shares = sum(l['shares'] for l in lots)
    avg    = sum(l['shares'] * l['price'] for l in lots) / shares
    pnl    = shares * (price - avg)
    cash  += shares * price
    add_to_history({'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'symbol': symbol,
        'type': 'MANUAL', 'entry': round(avg, 2), 'exit': round(price, 2),
        'pnl': round(pnl, 2), 'shares': round(shares, 2),
        'hold_time': round((time.time() - buy_time.get(symbol, time.time())) / 3600, 1)})
    positions.pop(symbol, None); buy_time.pop(symbol, None); trailing_state.pop(symbol, None)
    save_all_state()
    return True, f"Sold {symbol} at ${price:.2f}, PnL: ${pnl:.2f}"

# ═══════════════════════════════════════════════════════════════════════════
#  BACKGROUND SERVICES  (no os.fork / daemon – Android-safe threads only)
# ═══════════════════════════════════════════════════════════════════════════

def _auto_save_loop():
    while running:
        time.sleep(60)
        if running:
            save_all_state()
            record_metrics()

def _heartbeat_loop():
    while running:
        time.sleep(cfg['heartbeat_interval'])
        if running:
            hv = sum((sum(l['shares'] for l in lots) * (get_price_cached(sym) or 0))
                     for sym, lots in positions.items())
            logger.info(f"Heartbeat – Cash:${cash:.0f} Holdings:${hv:.0f} Pos:{len(positions)}")

def _trading_loop():
    fetch_prices_bulk(WATCHLIST)
    scan()
    last_scan = last_fetch = last_log = time.time()
    while running:
        try:
            now = time.time()
            if now - last_fetch >= 60:
                sample = list(set(list(positions.keys()) + random.sample(WATCHLIST, min(50, len(WATCHLIST)))))
                fetch_prices_bulk(sample)
                last_fetch = now
            if now - last_scan >= 30:
                scan()
                last_scan = now
                record_metrics()
            check_exits()
            check_entries()
            if now - last_log >= 300:
                total = wins + losses
                wr = (wins / total * 100) if total else 0
                hv = sum((sum(l['shares'] for l in lots) * (get_price_cached(sym) or 0))
                         for sym, lots in positions.items())
                logger.info(f"VIX:{get_vix():.0f} Pos:{len(positions)} Cash:${cash:.0f} NW:${cash+hv:.0f} WR:{wr:.0f}%")
                last_log = now
            time.sleep(22)
        except Exception as e:
            logger.error(f"Trading error: {e}")
            traceback.print_exc()
            time.sleep(30)

def _keepalive_loop():
    import urllib.request
    time.sleep(30)
    while running:
        try:
            urllib.request.urlopen(f'http://localhost:{PORT}/keepalive', timeout=5)
        except Exception:
            pass
        time.sleep(60)

def start_background_services():
    threading.Thread(target=_trading_loop,   daemon=True, name="TradingLoop").start()
    threading.Thread(target=_auto_save_loop, daemon=True, name="AutoSave").start()
    threading.Thread(target=_heartbeat_loop, daemon=True, name="Heartbeat").start()
    threading.Thread(target=_keepalive_loop, daemon=True, name="KeepAlive").start()

# ═══════════════════════════════════════════════════════════════════════════
#  STATUS
# ═══════════════════════════════════════════════════════════════════════════

def get_status():
    pos_copy = positions.copy()
    hv = sum((sum(l['shares'] for l in lots) * (get_price_cached(sym) or 0))
             for sym, lots in pos_copy.items())
    net   = cash + hv
    total = wins + losses
    wr    = (wins / total * 100) if total else 0
    v     = get_vix()
    tp, sl, wr_raw, wr_effect, _ = update_params()
    _, size_mult, sl_mult, vix_tier = get_vix_parameters()
    total_pnl = sum(t.get('pnl', 0) for t in trade_history if 'pnl' in t)
    avg_win   = sum(t.get('pnl', 0) for t in trade_history if t.get('type') == 'TP'  and t.get('pnl', 0) > 0) / max(wins, 1)
    avg_loss  = abs(sum(t.get('pnl', 0) for t in trade_history if t.get('type') == 'SL' and t.get('pnl', 0) < 0)) / max(losses, 1)
    holdings_list = []
    for sym, lots in pos_copy.items():
        price = get_price_cached(sym)
        if price:
            shares = sum(l['shares'] for l in lots)
            avg    = sum(l['shares'] * l['price'] for l in lots) / shares
            trail_active = sym in trailing_state and trailing_state[sym].get('has_pyramid', False)
            trail_price  = round(trailing_state[sym]['trailing'], 2) if trail_active and 'trailing' in trailing_state.get(sym, {}) else None
            holdings_list.append({
                'sym': sym, 'shares': round(shares, 2), 'entry': round(avg, 2),
                'cur': round(price, 2), 'pnl': round((price - avg) / avg * 100, 1),
                'tp': round(avg * (1 + tp), 2), 'sl': round(avg * (1 - sl), 2),
                'val': round(shares * price, 2),
                'entries': len(lots),
                'builds':   sum(1 for l in lots if l.get('is_build', False)),
                'pyramids': sum(1 for l in lots if l.get('is_pyramid', False)),
                'trail_active': trail_active, 'trail_price': trail_price,
            })
    return {
        'cash': round(cash, 2), 'hold': round(hv, 2), 'net': round(net, 2),
        'pl': round(net - 1000, 2), 'pos': len(pos_copy),
        'wins': wins, 'losses': losses, 'wr': round(wr, 1),
        'vix': round(v, 1), 'size': round(cur_size * 100, 1),
        'tp': round(tp * 100, 1), 'sl': round(sl * 100, 1), 'dip': get_required_dip(),
        'size_mult': round(size_mult * 100, 1), 'sl_mult': round(sl_mult, 2),
        'buys': buy_list[:10], 'holdings': holdings_list, 'scan': scan_num,
        'total': len(WATCHLIST), 'mode': "EXTREME" if v > 25 else "NORMAL",
        'wr_effect': wr_effect, 'vix_tier': vix_tier,
        'trade_history': trade_history[-500:], 'session_id': session_id[:8],
        'start_time': start_time, 'total_trades': len(trade_history),
        'total_pnl': round(total_pnl, 2), 'avg_win': round(avg_win, 2), 'avg_loss': round(avg_loss, 2),
        'uptime_hours': round((time.time() - start_timestamp) / 3600, 1),
        'trading_enabled': trading, 'loss_streak': loss_streak,
        'trading_paused': trading_paused,
        'pause_remaining_hours': round(max(0, pause_end_time - time.time()) / 3600, 1),
        'watchlist': WATCHLIST, 'watchlist_count': len(WATCHLIST),
        **{k: cfg[k] for k in [
            'build', 'max_pyramids', 'max_builds', 'build_trigger_pct',
            'max_consecutive_losses', 'loss_streak_cooldown', 'scan_size',
            'trailing_stop_pct', 'min_hold_hours', 'build_factor',
            'pyramid_threshold', 'pyramid_size', 'base_tp', 'base_sl',
            'base_size', 'sl_low', 'reserve',
            'wr_extreme', 'wr_very_high', 'wr_high', 'wr_low',
            'tp_extreme', 'tp_very_high', 'tp_high', 'tp_low',
            'size_extreme', 'size_very_high', 'size_high', 'size_low',
            'vix_high_tp', 'vix_elevated_tp', 'vix_high_sl', 'vix_elevated_sl',
            'vix_high_size', 'vix_elevated_size', 'vix_low_size', 'vix_high', 'vix_elevated',
            'static_stop_loss_enabled', 'trailing_only_after_pyramid', 'circuit_breaker_enabled',
        ]},
        'dip_vix_critical': cfg.get('dip_vix_critical', 8.0),
        'dip_vix_high':     cfg.get('dip_vix_high', 6.0),
        'dip_vix_elevated': cfg.get('dip_vix_elevated', 5.0),
        'dip_vix_moderate': cfg.get('dip_vix_moderate', 4.0),
        'dip_vix_low':      cfg.get('dip_vix_low', 3.0),
    }

# ═══════════════════════════════════════════════════════════════════════════
#  HTTP SERVER  (same REST API surface as original)
# ═══════════════════════════════════════════════════════════════════════════

# Reuse the full HTML from original (served from string below)
HTML = open(os.path.join(os.path.dirname(__file__), 'dashboard.html')).read() if os.path.exists(
    os.path.join(os.path.dirname(__file__), 'dashboard.html')) else "<h1>Dashboard loading…</h1>"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            path = self.path.split('?')[0]
            if path in ('/', '/dashboard'):
                body = HTML.encode()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif path == '/api/status':
                body = json.dumps(get_status()).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(body)
            elif path == '/keepalive':
                self.send_response(200); self.end_headers()
                self.wfile.write(b'ok')
            elif path == '/api/log':
                try:
                    with open(LOG_FILE, 'r') as f:
                        lines = f.readlines()[-200:]
                    body = json.dumps({'log': ''.join(lines)}).encode()
                except Exception:
                    body = json.dumps({'log': ''}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404); self.end_headers()
        except (BrokenPipeError, ConnectionAbortedError):
            pass
        except Exception as e:
            logger.error(f"GET Error: {e}")

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            post_data = json.loads(self.rfile.read(length)) if length else {}
            path = self.path.split('?')[0]

            def ok(data=None):
                body = json.dumps(data or {'status': 'ok'}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(body)

            global trading, trading_paused, loss_streak

            if path == '/api/toggle':
                trading = not trading
                ok({'trading': trading})
            elif path == '/api/sell':
                sym = post_data.get('symbol', '').upper().strip()
                if not sym:
                    self.send_response(400); self.end_headers(); return
                success, msg = manual_sell(sym)
                ok({'success': success, 'message': msg})
            elif path == '/api/clear_history':
                bu = clear_all_history()
                ok({'backup': bu})
            elif path == '/api/resume':
                trading_paused = False
                loss_streak = 0
                ok()
            elif path == '/api/watchlist/add':
                sym = post_data.get('symbol', '').upper().strip()
                if sym: add_to_watchlist(sym)
                ok()
            elif path == '/api/watchlist/remove':
                sym = post_data.get('symbol', '').upper().strip()
                if sym: remove_from_watchlist(sym)
                ok()
            elif path == '/api/watchlist/reset':
                reset_watchlist(); ok()
            elif path == '/api/config':
                key, value = post_data.get('key'), post_data.get('value')
                if key in cfg:
                    t = type(cfg[key])
                    cfg[key] = bool(value) if t == bool else (int(value) if t == int else float(value))
                    save_config()
                    ok()
                else:
                    self.send_response(404); self.end_headers()
            elif path == '/api/reset_config':
                cfg.clear(); cfg.update({
                    'base_size': 0.08, 'reserve': 0.10, 'base_tp': 0.0888, 'base_sl': 0.03,
                    'max_pos': 50, 'max_buys': 10, 'min_trade': 2.0, 'min_hold_hours': 8,
                    'trailing_stop_pct': 0.0666, 'heartbeat_interval': 30, 'auto_restart': True,
                    'build': True, 'build_factor': 0.5, 'pyramid_threshold': 5.0,
                    'pyramid_size': 0.30, 'max_pyramids': 999, 'max_builds': 999,
                    'build_trigger_pct': 2.5,
                    'wr_extreme': 0.85, 'wr_very_high': 0.75, 'wr_high': 0.65, 'wr_low': 0.45,
                    'tp_extreme': 1.30, 'tp_very_high': 1.20, 'tp_high': 1.15, 'tp_low': 0.90,
                    'size_extreme': 1.25, 'size_very_high': 1.20, 'size_high': 1.15, 'size_low': 0.90,
                    'vix_high_tp': 1.10, 'vix_elevated_tp': 1.05, 'sl_low': 1.10,
                    'vix_high_sl': 1.20, 'vix_elevated_sl': 1.05,
                    'vix_high_size': 1.20, 'vix_elevated_size': 1.05, 'vix_low_size': 0.95,
                    'vix_high': 25, 'vix_elevated': 18,
                    'max_consecutive_losses': 3, 'loss_streak_cooldown': 8,
                    'scan_size': 60, 'extreme_dip': 8.0, 'normal_dip': 3.0, 'high_vix_reduction': 0.5,
                    'dip_vix_critical': 8.0, 'dip_vix_high': 6.0, 'dip_vix_elevated': 5.0,
                    'dip_vix_moderate': 4.0, 'dip_vix_low': 3.0,
                    'static_stop_loss_enabled': False, 'trailing_only_after_pyramid': True,
                    'circuit_breaker_enabled': False,
                })
                save_config(); ok()
            else:
                self.send_response(404); self.end_headers()
        except (BrokenPipeError, ConnectionAbortedError):
            pass
        except Exception as e:
            logger.error(f"POST Error: {e}")

    def log_message(self, *_): pass


def find_available_port(start=8888, tries=12):
    for offset in range(tries):
        port = start + offset
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', port))
            s.close()
            return port
        except OSError:
            continue
    return None

def start_http_server():
    global PORT
    PORT = find_available_port(8888)
    if PORT is None:
        logger.error("No available port in 8888-8899 range.")
        return
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True, name="HTTPServer").start()
    logger.info(f"Dashboard: http://localhost:{PORT}")

# ═══════════════════════════════════════════════════════════════════════════
#  KIVY UI
# ═══════════════════════════════════════════════════════════════════════════

class BotLayout(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation='vertical', **kw)
        if HAS_WEBVIEW:
            self._wv = WebView(url=f'http://localhost:{PORT}')
            self.add_widget(self._wv)
        else:
            self.add_widget(Label(
                text=f"[b]DIP BOT running[/b]\nOpen browser → http://localhost:{PORT}",
                markup=True,
                halign='center',
            ))

    def reload(self, *_):
        if HAS_WEBVIEW:
            self._wv.url = f'http://localhost:{PORT}'


class DipBotApp(App):
    title = "DIP BOT"

    def build(self):
        if ANDROID:
            request_permissions([
                Permission.INTERNET,
                Permission.ACCESS_NETWORK_STATE,
                Permission.WAKE_LOCK,
            ])
        # Initialise everything
        load_watchlist()
        load_config()
        load_all_state()
        start_http_server()
        start_background_services()
        atexit.register(lambda: (save_all_state(), save_config(), save_watchlist()))
        self.layout = BotLayout()
        # Reload webview once port is definitely up (2 s grace)
        Clock.schedule_once(self.layout.reload, 2)
        return self.layout

    def on_stop(self):
        global running
        running = False
        save_all_state()
        save_config()
        save_watchlist()


if __name__ == '__main__':
    DipBotApp().run()
