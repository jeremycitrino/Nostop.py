"""
Android Trading Bot - APK Entry Point
"""
import os
import sys
import threading
import time

# Android imports (safe wrapper)
try:
    from android.permissions import request_permissions, Permission
    HAS_ANDROID = True
except ImportError:
    HAS_ANDROID = False

# Kivy imports
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle

# Import your trading engine
from nostop import (
    get_status, manual_sell, trading, running,
    logger, start_bot as start_engine
)


class TradingCard(BoxLayout):
    """Custom widget for stats"""
    def __init__(self, title, value, value_color=(1,1,1,1), **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = [8, 8]
        self.spacing = 2
        self.size_hint_y = None
        self.height = 70
        
        with self.canvas.before:
            Color(0.15, 0.15, 0.2, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[5])
        
        self.bind(pos=self.update_rect, size=self.update_rect)
        
        self.add_widget(Label(
            text=title, font_size='10sp', 
            color=(0.6,0.6,0.6,1), size_hint_y=0.4
        ))
        self.value_label = Label(
            text=value, font_size='18sp', bold=True,
            color=value_color, size_hint_y=0.6
        )
        self.add_widget(self.value_label)
    
    def update_rect(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.15, 0.15, 0.2, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[5])
    
    def set_value(self, text, color=(1,1,1,1)):
        self.value_label.text = text
        self.value_label.color = color


class PositionRow(BoxLayout):
    """Custom widget for position display"""
    def __init__(self, symbol, entry, current, shares, **kwargs):
        super().__init__(**kwargs)
        self.symbol = symbol
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 50
        self.padding = [10, 5]
        self.spacing = 5
        
        with self.canvas.before:
            Color(0.12, 0.12, 0.16, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[4])
        
        self.bind(pos=self.update_rect, size=self.update_rect)
        
        pnl_pct = ((current - entry) / entry) * 100
        
        self.add_widget(Label(text=symbol, bold=True, size_hint_x=0.25))
        self.add_widget(Label(text=f'${entry:.2f}', size_hint_x=0.2, font_size='11sp'))
        self.add_widget(Label(text=f'${current:.2f}', size_hint_x=0.2, font_size='11sp'))
        
        pnl_color = (0.3, 0.8, 0.3, 1) if pnl_pct >= 0 else (0.9, 0.3, 0.3, 1)
        self.add_widget(Label(
            text=f'{pnl_pct:+.1f}%', color=pnl_color, size_hint_x=0.2
        ))
        
        sell_btn = Button(text='SELL', size_hint_x=0.15, background_color=(0.7, 0.3, 0.2, 1))
        sell_btn.bind(on_press=self.sell_position)
        self.add_widget(sell_btn)
    
    def update_rect(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.12, 0.12, 0.16, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[4])
    
    def sell_position(self, instance):
        success, msg = manual_sell(self.symbol)
        app = App.get_running_app()
        if hasattr(app, 'main_widget'):
            app.main_widget.status_label.text = msg[:50]


class TradingBotWidget(BoxLayout):
    """Main UI Widget"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = [10, 10]
        self.spacing = 5
        
        # Header
        header = BoxLayout(size_hint_y=0.08, spacing=5)
        header.add_widget(Label(text='🤖 DIP BOT', font_size='20sp', bold=True))
        
        # Control buttons
        btn_layout = BoxLayout(size_hint_x=0.4, spacing=5)
        self.start_btn = Button(text='START', background_color=(0.2, 0.6, 0.2, 1))
        self.start_btn.bind(on_press=self.toggle_trading)
        btn_layout.add_widget(self.start_btn)
        header.add_widget(btn_layout)
        self.add_widget(header)
        
        # Stats grid
        stats_grid = GridLayout(cols=3, size_hint_y=0.25, spacing=5, padding=[0,5])
        
        self.net_card = TradingCard('NET WORTH', '$0', (0.3, 0.7, 1, 1))
        self.cash_card = TradingCard('CASH', '$0', (0.3, 0.8, 0.3, 1))
        self.pl_card = TradingCard('P&L', '$0')
        self.wr_card = TradingCard('WIN RATE', '0%')
        self.pos_card = TradingCard('POSITIONS', '0')
        self.vix_card = TradingCard('VIX', '0')
        
        stats_grid.add_widget(self.net_card)
        stats_grid.add_widget(self.cash_card)
        stats_grid.add_widget(self.pl_card)
        stats_grid.add_widget(self.wr_card)
        stats_grid.add_widget(self.pos_card)
        stats_grid.add_widget(self.vix_card)
        
        self.add_widget(stats_grid)
        
        # Holdings title
        title_bar = BoxLayout(size_hint_y=0.06)
        title_bar.add_widget(Label(text='📊 HOLDINGS', bold=True, size_hint_x=0.7))
        self.holdings_count = Label(text='0', size_hint_x=0.3)
        title_bar.add_widget(self.holdings_count)
        self.add_widget(title_bar)
        
        # Scrollable holdings list
        scroll = ScrollView(size_hint_y=0.45)
        self.holdings_layout = GridLayout(cols=1, size_hint_y=None, spacing=2)
        self.holdings_layout.bind(minimum_height=self.holdings_layout.setter('height'))
        scroll.add_widget(self.holdings_layout)
        self.add_widget(scroll)
        
        # Status bar
        self.status_label = Label(
            text='Initializing...', font_size='10sp',
            color=(0.7, 0.7, 0.7, 1), size_hint_y=0.05
        )
        self.add_widget(self.status_label)
        
        # Start periodic updates
        Clock.schedule_interval(self.update_ui, 2.0)
        
        # Start bot in background
        threading.Thread(target=self.start_bot, daemon=True).start()
    
    def start_bot(self):
        """Start trading engine"""
        time.sleep(1)
        start_engine()
    
    def toggle_trading(self, instance):
        """Start/Stop trading"""
        global trading
        trading = not trading
        self.start_btn.text = 'STOP' if trading else 'START'
        self.start_btn.background_color = (0.6, 0.2, 0.2, 1) if trading else (0.2, 0.6, 0.2, 1)
        logger.info(f"Trading toggled: {trading}")
    
    def update_ui(self, dt):
        """Update UI with latest data"""
        try:
            status = get_status()
            
            # Update cards
            net = status.get('net', 0)
            self.net_card.set_value(f'${net:,.0f}', (0.3, 0.7, 1, 1))
            self.cash_card.set_value(f'${status.get("cash", 0):,.0f}', (0.3, 0.8, 0.3, 1))
            
            pl = status.get('pl', 0)
            pl_color = (0.3, 0.8, 0.3, 1) if pl >= 0 else (0.9, 0.3, 0.3, 1)
            self.pl_card.set_value(f'{pl:+.0f}', pl_color)
            
            self.wr_card.set_value(f'{status.get("wr", 0):.0f}%')
            pos_count = status.get('pos', 0)
            self.pos_card.set_value(str(pos_count))
            self.vix_card.set_value(f'{status.get("vix", 15):.1f}')
            self.holdings_count.text = str(pos_count)
            
            # Update holdings list
            self.holdings_layout.clear_widgets()
            holdings = status.get('holdings', [])
            
            if not holdings:
                self.holdings_layout.add_widget(Label(
                    text='No open positions', size_hint_y=None, height=40
                ))
            else:
                for pos in holdings:
                    row = PositionRow(
                        symbol=pos.get('sym', ''),
                        entry=pos.get('entry', 0),
                        current=pos.get('cur', 0),
                        shares=pos.get('shares', 0)
                    )
                    self.holdings_layout.add_widget(row)
            
            # Update status
            if status.get('trading_paused', False):
                self.status_label.text = f"⏸ PAUSED - {status.get('pause_remaining_hours', 0):.1f}h left"
            elif not status.get('trading_enabled', True):
                self.status_label.text = "⏹ STOPPED - Press START"
            else:
                self.status_label.text = f"🟢 ACTIVE | Scans: {status.get('scan', 0)} | Trades: {status.get('total_trades', 0)}"
                
        except Exception as e:
            self.status_label.text = f"Error: {str(e)[:40]}"


class TradingBotApp(App):
    def build(self):
        if HAS_ANDROID:
            request_permissions([
                Permission.INTERNET,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE
            ])
        
        if not HAS_ANDROID:
            Window.size = (400, 700)
        
        self.main_widget = TradingBotWidget()
        return self.main_widget


if __name__ == '__main__':
    TradingBotApp().run()
