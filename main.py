"""
Trading Bot for Android - Main Entry Point
Keeps all original trading logic, adds Android service compatibility
"""

import os
import sys
import threading
import time
from kivy.lang import Builder
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ListProperty

# Android-specific imports (safe for desktop)
try:
    from android.permissions import request_permissions, Permission
    from android import AndroidService
    HAS_ANDROID = True
except ImportError:
    HAS_ANDROID = False

# Import your trading engine
from nostop import (
    start_bot, get_status, manual_sell, add_to_watchlist, 
    remove_from_watchlist, reset_watchlist, clear_all_history,
    cfg, save_config, running, trading, logger
)

# ============== KIVY UI STRING (Simplified for APK) ==============
KV = '''
<MainScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(10)
        spacing: dp(5)
        
        # Header
        BoxLayout:
            size_hint_y: 0.08
            Label:
                text: '🤖 DIP BOT'
                font_size: '20sp'
                bold: True
            Label:
                text: 'v1.0'
                size_hint_x: 0.3
        
        # Status Bar
        BoxLayout:
            size_hint_y: 0.08
            spacing: dp(5)
            Button:
                id: start_btn
                text: 'START'
                background_color: (0.2, 0.6, 0.2, 1) if root.trading_enabled else (0.4, 0.4, 0.4, 1)
                on_press: root.toggle_trading()
            Button:
                text: 'SELL ALL'
                background_color: (0.8, 0.3, 0.2, 1)
                on_press: root.show_sell_dialog()
            Button:
                text: '⚙️'
                size_hint_x: 0.15
                on_press: root.show_config()
        
        # Main Stats Grid
        GridLayout:
            size_hint_y: 0.20
            cols: 3
            spacing: dp(5)
            padding: dp(5)
            
            Card:
                title: 'NET WORTH'
                value: f'${root.net_worth:,.0f}'
                value_color: (0.3, 0.7, 1, 1)
            
            Card:
                title: 'CASH'
                value: f'${root.cash:,.0f}'
                value_color: (0.3, 0.8, 0.3, 1)
            
            Card:
                title: 'P&L'
                value: f'{root.pl:+.0f}'
                value_color: (0.3, 0.8, 0.3, 1) if root.pl >= 0 else (0.9, 0.3, 0.3, 1)
            
            Card:
                title: 'WIN RATE'
                value: f'{root.win_rate:.0f}%'
            
            Card:
                title: 'POSITIONS'
                value: str(root.positions_count)
            
            Card:
                title: 'VIX'
                value: f'{root.vix:.1f}'
        
        # Holdings Title
        BoxLayout:
            size_hint_y: 0.05
            Label:
                text: '📊 HOLDINGS'
                bold: True
                size_hint_x: 0.7
            Label:
                text: f'Total: {root.positions_count}'
                size_hint_x: 0.3
        
        # Holdings Scroll List
        ScrollView:
            size_hint_y: 0.44
            GridLayout:
                id: holdings_grid
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(2)
        
        # Bottom Status
        BoxLayout:
            size_hint_y: 0.05
            Label:
                text: root.status_text
                font_size: '10sp'
                color: (0.7, 0.7, 0.7, 1)

<Card@BoxLayout>:
    orientation: 'vertical'
    padding: dp(8)
    spacing: dp(2)
    canvas.before:
        Color:
            rgba: (0.15, 0.15, 0.2, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(5)]
    
    title: ''
    value: ''
    value_color: (1, 1, 1, 1)
    
    Label:
        text: root.title
        font_size: '10sp'
        color: (0.6, 0.6, 0.6, 1)
        size_hint_y: 0.4
    
    Label:
        text: root.value
        font_size: '18sp'
        bold: True
        color: root.value_color
        size_hint_y: 0.6

<PositionItem@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(50)
    padding: dp(10)
    spacing: dp(5)
    canvas.before:
        Color:
            rgba: (0.12, 0.12, 0.16, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(4)]
    
    symbol: ''
    pnl_pct: 0.0
    entry: 0.0
    current: 0.0
    shares: 0.0
    
    Label:
        text: root.symbol
        bold: True
        size_hint_x: 0.2
    
    Label:
        text: f'${root.entry:.2f}'
        size_hint_x: 0.2
        font_size: '11sp'
    
    Label:
        text: f'${root.current:.2f}'
        size_hint_x: 0.2
        font_size: '11sp'
    
    Label:
        text: f'{root.pnl_pct:+.1f}%'
        color: (0.3, 0.8, 0.3, 1) if root.pnl_pct >= 0 else (0.9, 0.3, 0.3, 1)
        size_hint_x: 0.2
    
    Button:
        text: 'SELL'
        size_hint_x: 0.2
        background_color: (0.7, 0.3, 0.2, 1)
        on_press: app.root.current_screen.sell_position(root.symbol)
'''

Builder.load_string(KV)


class MainScreen(Screen):
    # Properties for UI binding
    net_worth = NumericProperty(0)
    cash = NumericProperty(0)
    pl = NumericProperty(0)
    win_rate = NumericProperty(0)
    positions_count = NumericProperty(0)
    vix = NumericProperty(0)
    trading_enabled = BooleanProperty(True)
    status_text = StringProperty("Initializing...")
    holdings_list = ListProperty([])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_event = None
        self.trading_enabled = trading
        
    def on_enter(self):
        # Start periodic updates
        self.update_event = Clock.schedule_interval(self.update_ui, 2.0)
        self.status_text = "Bot running..."
        
    def on_leave(self):
        if self.update_event:
            self.update_event.cancel()
    
    def update_ui(self, dt):
        """Fetch status and update UI"""
        try:
            status = get_status()
            
            self.net_worth = status.get('net', 0)
            self.cash = status.get('cash', 0)
            self.pl = status.get('pl', 0)
            self.win_rate = status.get('wr', 0)
            self.positions_count = status.get('pos', 0)
            self.vix = status.get('vix', 15)
            
            # Update holdings list
            holdings = status.get('holdings', [])
            self.update_holdings_grid(holdings)
            
            # Update status text
            if status.get('trading_paused', False):
                self.status_text = f"⏸ PAUSED - Cooldown: {status.get('pause_remaining_hours', 0):.1f}h"
            elif not status.get('trading_enabled', True):
                self.status_text = "⏹ STOPPED - Press START"
            else:
                self.status_text = f"🟢 ACTIVE | Scans: {status.get('scan', 0)} | Trades: {status.get('total_trades', 0)}"
                
        except Exception as e:
            logger.error(f"UI update error: {e}")
            self.status_text = f"Error: {str(e)[:30]}"
    
    def update_holdings_grid(self, holdings):
        """Dynamically create position items"""
        grid = self.ids.holdings_grid
        grid.clear_widgets()
        
        if not holdings:
            grid.add_widget(Label(text="No open positions", size_hint_y=None, height=dp(40)))
            return
        
        for pos in holdings:
            item = PositionItem(
                symbol=pos.get('sym', ''),
                pnl_pct=pos.get('pnl', 0),
                entry=pos.get('entry', 0),
                current=pos.get('cur', 0),
                shares=pos.get('shares', 0)
            )
            grid.add_widget(item)
    
    def toggle_trading(self):
        """Start/Stop trading"""
        global trading
        trading = not trading
        self.trading_enabled = trading
        logger.info(f"Trading toggled to: {trading}")
        self.status_text = "STARTING..." if trading else "STOPPED"
    
    def sell_position(self, symbol):
        """Sell a specific position"""
        success, msg = manual_sell(symbol)
        self.status_text = msg[:50]
        if success:
            logger.info(f"Sold {symbol}: {msg}")
    
    def show_sell_dialog(self):
        """Show dialog to confirm sell all"""
        # Simple implementation - could be enhanced
        self.status_text = "Use individual SELL buttons"
    
    def show_config(self):
        """Navigate to config screen"""
        self.manager.current = 'config'


class ConfigScreen(Screen):
    """Basic configuration screen"""
    def on_enter(self):
        self.load_config()
    
    def load_config(self):
        """Load current config values"""
        # Simplified - just display key params
        pass
    
    def save_and_return(self):
        save_config()
        self.manager.current = 'main'


class TradingBotApp(App):
    def build(self):
        # Request Android permissions if on device
        if HAS_ANDROID:
            request_permissions([
                Permission.INTERNET,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.FOREGROUND_SERVICE
            ])
        
        # Set window size for desktop testing
        if not HAS_ANDROID:
            Window.size = (400, 700)
        
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(ConfigScreen(name='config'))
        
        return sm
    
    def on_start(self):
        """Start the trading bot in background thread"""
        logger.info("App starting, launching bot thread...")
        
        # Start bot in background thread
        def run_bot():
            try:
                start_bot()
            except Exception as e:
                logger.error(f"Bot error: {e}")
        
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        
        # Give bot time to initialize
        time.sleep(2)
        logger.info("Bot thread started")


if __name__ == '__main__':
    TradingBotApp().run()
