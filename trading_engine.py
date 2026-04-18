#!/usr/bin/env python
# trading_engine.py – Pure trading logic extracted from nostop.py
# Android‑ready: uses internal storage, no web server, no Termux.

import os, sys, json, time, threading, random, gc
from datetime import datetime

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
LOG_FILE = os.path.join(DATA_DIR, "bot.log")

# ----------------------------------------------------------------------
# YFINANCE IMPORT
# ----------------------------------------------------------------------
try:
    import yfinance as yf
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

# ----------------------------------------------------------------------
# CONFIGURATION (unchanged from nostop.py)
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

# ----------------------------------------------------------------------
# LOGGING (simplified – writes to file)
# ----------------------------------------------------------------------
class Logger:
    def __init__(self, log_file=LOG_FILE):
        self.log_file = log_file
    def log(self, message, level="INFO"):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"[{ts}] [{level}] {message}\n")
        except:
            pass
        print(f"[{ts}] [{level}] {message}")
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
                'uptime': time.time() - start_timestamp,
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
# PRICE & INDICATORS
# ----------------------------------------------------------------------
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

# ----------------------------------------------------------------------
# TRADING LOOP
# ----------------------------------------------------------------------
def trading_loop():
    logger.info("="*50)
    logger.info(f"🤖 TRADING BOT | {len(WATCHLIST)} SYMBOLS | ${cash:.0f}")
    logger.info(f"🆔 Session: {session_id}")
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
                lot_type = "BASE" if idx == 0 else ("PYRAMID" if lot.get('is_pyramid') else ("BUILD" if lot.get('is_build') else "ADD"))
                lots_detail.append({'type': lot_type, 'price': round(lot['price'],2), 'shares': round(lot['shares'],2)})
            trail_active = trailing_state.get(sym, {}).get('has_pyramid', False)
            trail_price = round(trailing_state[sym]['trailing'],2) if trail_active and 'trailing' in trailing_state.get(sym,{}) else None
            holdings_list.append({
                'sym': sym, 'shares': round(shares,2), 'entry': round(avg,2), 'cur': round(price,2),
                'pnl': round((price-avg)/avg*100,1), 'val': round(shares*price,2),
                'entries': num_entries, 'builds': num_builds, 'pyramids': num_pyramids,
                'trail_active': trail_active, 'trail_price': trail_price
            })
    return {
        'cash': round(cash,2), 'hold': round(holdings_value,2), 'net': round(net,2),
        'pos': len(positions_copy), 'wins': wins, 'losses': losses, 'wr': round(wr,1),
        'vix': round(v,1), 'size': round(cur_size*100,1), 'tp': round(tp*100,1), 'sl': round(sl*100,1),
        'dip': min_dip, 'buys': buy_list[:10], 'holdings': holdings_list, 'scan': scan_num,
        'total_trades': len(trade_history), 'total_pnl': round(total_pnl,2),
        'uptime_hours': round(uptime/3600,1), 'trading_enabled': trading, 'loss_streak': loss_streak,
        'trading_paused': trading_paused, 'pause_remaining_hours': round(pause_remaining,1),
        'watchlist': WATCHLIST, 'watchlist_count': len(WATCHLIST)
    }

# ----------------------------------------------------------------------
# ENTRY POINT FOR ANDROID SERVICE
# ----------------------------------------------------------------------
def start_bot():
    global running, trading
    load_watchlist()
    load_config()
    load_all_state()
    prevent_sleep()

    # Start trading loop in background
    trading_thread = threading.Thread(target=trading_loop, daemon=True)
    trading_thread.start()

    logger.info("="*50)
    logger.info("   TRADING BOT STARTED (ANDROID MODE)")
    logger.info("="*50)

    # Keep the function alive (service runs until stopped)
    while running:
        time.sleep(1)
