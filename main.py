"""
Complete Kivy Trading Bot App
Includes trading engine + native Kivy dashboard
"""

import os
import json
import time
import threading
from datetime import datetime
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ListProperty
from kivy.metrics import dp

# Import your trading engine
from nostop import (
    get_status, manual_sell, add_to_watchlist, remove_from_watchlist,
    reset_watchlist, clear_all_history, cfg, save_config,
    start_bot as start_engine, running, trading, logger
)

# ============== KIVY UI STRING ==============
KV = '''
<MainScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(8)
        spacing: dp(5)
        
        # Status Bar
        BoxLayout:
            size_hint_y: 0.07
            spacing: dp(5)
            Label:
                text: '🤖 DIP BOT'
                font_size: '18sp'
                bold: True
                size_hint_x: 0.4
            Label:
                id: status_label
                text: '● LIVE'
                font_size: '12sp'
                color: (0.3, 0.8, 0.3, 1)
                size_hint_x: 0.3
            Button:
                id: start_stop_btn
                text: 'STOP'
                background_color: (0.6, 0.2, 0.2, 1) if root.trading_enabled else (0.2, 0.6, 0.2, 1)
                size_hint_x: 0.3
                on_press: root.toggle_trading()
        
        # Tab Panel
        TabbedPanel:
            id: tabs
            do_default_tab: False
            tab_width: dp(100)
            
            TabbedPanelItem:
                text: '📊 DASHBOARD'
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(5)
                    spacing: dp(5)
                    
                    # Stats Grid
                    GridLayout:
                        size_hint_y: 0.35
                        cols: 2
                        spacing: dp(5)
                        padding: dp(5)
                        
                        StatCard:
                            title: 'NET WORTH'
                            value: f'${root.net_worth:,.0f}'
                            value_color: (0.3, 0.7, 1, 1)
                        
                        StatCard:
                            title: 'CASH'
                            value: f'${root.cash:,.0f}'
                            value_color: (0.3, 0.8, 0.3, 1)
                        
                        StatCard:
                            title: 'P&L'
                            value: f'{root.pl:+.0f}'
                            value_color: (0.3, 0.8, 0.3, 1) if root.pl >= 0 else (0.9, 0.3, 0.3, 1)
                        
                        StatCard:
                            title: 'WIN RATE'
                            value: f'{root.win_rate:.0f}%'
                        
                        StatCard:
                            title: 'POSITIONS'
                            value: str(root.positions_count)
                        
                        StatCard:
                            title: 'VIX'
                            value: f'{root.vix:.1f}'
                        
                        StatCard:
                            title: 'TP/SL'
                            value: f'{root.tp:.1f}%/{root.sl:.1f}%'
                        
                        StatCard:
                            title: 'SIZE'
                            value: f'{root.position_size:.1f}%'
                    
                    # Holdings Title
                    BoxLayout:
                        size_hint_y: 0.05
                        Label:
                            text: '📈 HOLDINGS'
                            bold: True
                            size_hint_x: 0.7
                        Label:
                            text: f'Total: {root.positions_count}'
                            size_hint_x: 0.3
                    
                    # Holdings List
                    ScrollView:
                        size_hint_y: 0.5
                        GridLayout:
                            id: holdings_grid
                            cols: 1
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(2)
            
            TabbedPanelItem:
                text: '🔽 TOP DIPS'
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(5)
                    Label:
                        text: 'Best Entry Opportunities'
                        size_hint_y: 0.08
                    ScrollView:
                        GridLayout:
                            id: dips_grid
                            cols: 1
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(2)
            
            TabbedPanelItem:
                text: '📜 HISTORY'
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(5)
                    BoxLayout:
                        size_hint_y: 0.08
                        Label:
                            text: 'Trade History'
                            bold: True
                        Label:
                            id: trade_count_label
                            text: '0 trades'
                            size_hint_x: 0.3
                    ScrollView:
                        GridLayout:
                            id: history_grid
                            cols: 1
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(2)
            
            TabbedPanelItem:
                text: '⚙️ CONFIG'
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(5)
                    spacing: dp(5)
                    
                    ScrollView:
                        GridLayout:
                            id: config_grid
                            cols: 1
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(3)
                    
                    Button:
                        text: 'SAVE CONFIG'
                        size_hint_y: 0.08
                        background_color: (0.2, 0.5, 0.8, 1)
                        on_press: root.save_config()
                    
                    Button:
                        text: 'RESET TO DEFAULTS'
                        size_hint_y: 0.08
                        background_color: (0.6, 0.4, 0.1, 1)
                        on_press: root.reset_config()
                    
                    Button:
                        text: '🗑 CLEAR ALL HISTORY'
                        size_hint_y: 0.08
                        background_color: (0.8, 0.2, 0.2, 1)
                        on_press: root.clear_history()
            
            TabbedPanelItem:
                text: '📋 WATCHLIST'
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(5)
                    spacing: dp(5)
                    
                    BoxLayout:
                        size_hint_y: 0.08
                        spacing: dp(5)
                        TextInput:
                            id: add_symbol_input
                            hint_text: 'Symbol (e.g., AAPL)'
                            multiline: False
                            size_hint_x: 0.7
                        Button:
                            text: 'ADD'
                            size_hint_x: 0.3
                            on_press: root.add_watchlist_symbol(add_symbol_input.text)
                    
                    ScrollView:
                        GridLayout:
                            id: watchlist_grid
                            cols: 1
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(2)
                    
                    Button:
                        text: '⟳ RESET TO DEFAULT'
                        size_hint_y: 0.08
                        background_color: (0.6, 0.4, 0.1, 1)
                        on_press: root.reset_watchlist()

<StatCard@BoxLayout>:
    orientation: 'vertical'
    padding: dp(8)
    spacing: dp(2)
    size_hint_y: None
    height: dp(70)
    canvas.before:
        Color:
            rgba: (0.12, 0.12, 0.16, 1)
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
    padding: dp(8)
    spacing: dp(5)
    canvas.before:
        Color:
            rgba: (0.1, 0.1, 0.14, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(4)]
    
    symbol: ''
    pnl_pct: 0.0
    entry: 0.0
    current: 0.0
    
    Label:
        text: root.symbol
        bold: True
        size_hint_x: 0.25
    
    Label:
        text: f'${root.entry:.2f}'
        font_size: '11sp'
        size_hint_x: 0.2
    
    Label:
        text: f'${root.current:.2f}'
        font_size: '11sp'
        size_hint_x: 0.2
    
    Label:
        text: f'{root.pnl_pct:+.1f}%'
        color: (0.3, 0.8, 0.3, 1) if root.pnl_pct >= 0 else (0.9, 0.3, 0.3, 1)
        size_hint_x: 0.2
    
    Button:
        text: 'SELL'
        size_hint_x: 0.15
        background_color: (0.7, 0.3, 0.2, 1)
        on_press: app.root.current_screen.sell_position(root.symbol)

<DipItem@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(40)
    padding: dp(8)
    spacing: dp(5)
    canvas.before:
        Color:
            rgba: (0.1, 0.1, 0.14, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(4)]
    
    symbol: ''
    dip: 0.0
    price: 0.0
    
    Label:
        text: root.symbol
        bold: True
        size_hint_x: 0.35
    Label:
        text: f'▼{root.dip:.1f}%'
        color: (0.9, 0.7, 0.2, 1)
        size_hint_x: 0.3
    Label:
        text: f'${root.price:.2f}'
        size_hint_x: 0.35

<HistoryItem@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(45)
    padding: dp(8)
    spacing: dp(5)
    canvas.before:
        Color:
            rgba: (0.1, 0.1, 0.14, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(4)]
    
    trade_type: ''
    symbol: ''
    pnl: 0.0
    date: ''
    
    BoxLayout:
        orientation: 'vertical'
        size_hint_x: 0.5
        Label:
            text: f'{root.symbol}'
            bold: True
            halign: 'left'
            size_hint_y: 0.5
        Label:
            text: f'{root.date[-8:]}'
            font_size: '9sp'
            color: (0.6, 0.6, 0.6, 1)
            halign: 'left'
            size_hint_y: 0.5
    
    Label:
        text: root.trade_type
        size_hint_x: 0.25
        color: (0.3, 0.8, 0.3, 1) if root.trade_type == 'TP' else (0.9, 0.3, 0.3, 1) if root.trade_type in ('SL', 'MANUAL') else (0.4, 0.6, 0.9, 1)
    
    Label:
        text: f'${root.pnl:+.2f}' if root.pnl != 0 else '--'
        size_hint_x: 0.25
        color: (0.3, 0.8, 0.3, 1) if root.pnl > 0 else (0.9, 0.3, 0.3, 1) if root.pnl < 0 else (0.7, 0.7, 0.7, 1)

<ConfigRow@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(40)
    padding: dp(5)
    spacing: dp(5)
    
    key: ''
    value: 0
    is_boolean: False
    
    Label:
        text: root.key
        size_hint_x: 0.6
        font_size: '11sp'
        halign: 'left'
    
    Widget:
        size_hint_x: 0.4
        BoxLayout:
            if root.is_boolean:
                ToggleButton:
                    id: bool_toggle
                    text: 'ON' if root.value else 'OFF'
                    state: 'down' if root.value else 'normal'
                    on_press: root.parent.update_config(root.key, not root.value)
            else:
                TextInput:
                    id: num_input
                    text: str(root.value)
                    multiline: False
                    input_filter: 'float'
                    size_hint_x: 0.7
                    on_text_validate: root.parent.update_config(root.key, float(self.text))
                Button:
                    text: 'SET'
                    size_hint_x: 0.3
                    on_press: root.parent.update_config(root.key, float(num_input.text))

<WatchlistItem@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(35)
    padding: dp(8)
    spacing: dp(5)
    canvas.before:
        Color:
            rgba: (0.1, 0.1, 0.14, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(4)]
    
    symbol: ''
    
    Label:
        text: root.symbol
        bold: True
        size_hint_x: 0.7
    
    Button:
        text: 'REMOVE'
        size_hint_x: 0.3
        background_color: (0.7, 0.3, 0.2, 1)
        on_press: app.root.current_screen.remove_watchlist_symbol(root.symbol)
'''

Builder.load_string(KV)


class MainScreen(Screen):
    net_worth = NumericProperty(0)
    cash = NumericProperty(0)
    pl = NumericProperty(0)
    win_rate = NumericProperty(0)
    positions_count = NumericProperty(0)
    vix = NumericProperty(0)
    tp = NumericProperty(0)
    sl = NumericProperty(0)
    position_size = NumericProperty(0)
    trading_enabled = BooleanProperty(True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_event = None
        self.trading_enabled = trading
        
    def on_enter(self):
        self.update_event = Clock.schedule_interval(self.update_ui, 2.0)
        # Start bot in background if not already running
        if running:
            threading.Thread(target=start_engine, daemon=True).start()
    
    def on_leave(self):
        if self.update_event:
            self.update_event.cancel()
    
    def update_ui(self, dt):
        try:
            status = get_status()
            
            self.net_worth = status.get('net', 0)
            self.cash = status.get('cash', 0)
            self.pl = status.get('pl', 0)
            self.win_rate = status.get('wr', 0)
            self.positions_count = status.get('pos', 0)
            self.vix = status.get('vix', 15)
            self.tp = status.get('tp', 0)
            self.sl = status.get('sl', 0)
            self.position_size = status.get('size', 0)
            
            # Update status label
            status_label = self.ids.get('status_label')
            if status_label:
                if status.get('trading_paused', False):
                    status_label.text = '⏸ PAUSED'
                    status_label.color = (0.9, 0.7, 0.2, 1)
                elif self.trading_enabled:
                    status_label.text = '● LIVE'
                    status_label.color = (0.3, 0.8, 0.3, 1)
                else:
                    status_label.text = '○ STOPPED'
                    status_label.color = (0.6, 0.6, 0.6, 1)
            
            # Update holdings
            self.update_holdings_grid(status.get('holdings', []))
            
            # Update dips
            self.update_dips_grid(status.get('buys', []))
            
            # Update history
            self.update_history_grid(status.get('trade_history', []))
            
            # Update trade count
            trade_label = self.ids.get('trade_count_label')
            if trade_label:
                trade_label.text = f"{status.get('total_trades', 0)} trades"
            
        except Exception as e:
            logger.error(f"UI update error: {e}")
    
    def update_holdings_grid(self, holdings):
        grid = self.ids.get('holdings_grid')
        if not grid:
            return
        grid.clear_widgets()
        
        if not holdings:
            grid.add_widget(Label(text='No open positions', size_hint_y=None, height=dp(40)))
            return
        
        for pos in holdings:
            item = PositionItem(
                symbol=pos.get('sym', ''),
                pnl_pct=pos.get('pnl', 0),
                entry=pos.get('entry', 0),
                current=pos.get('cur', 0)
            )
            grid.add_widget(item)
    
    def update_dips_grid(self, dips):
        grid = self.ids.get('dips_grid')
        if not grid:
            return
        grid.clear_widgets()
        
        if not dips:
            grid.add_widget(Label(text='No qualified dips', size_hint_y=None, height=dp(40)))
            return
        
        for dip in dips[:15]:
            item = DipItem(
                symbol=dip.get('sym', ''),
                dip=dip.get('dip', 0),
                price=dip.get('price', 0)
            )
            grid.add_widget(item)
    
    def update_history_grid(self, history):
        grid = self.ids.get('history_grid')
        if not grid:
            return
        grid.clear_widgets()
        
        if not history:
            grid.add_widget(Label(text='No trades yet', size_hint_y=None, height=dp(40)))
            return
        
        for trade in reversed(history[-50:]):
            item = HistoryItem(
                trade_type=trade.get('type', ''),
                symbol=trade.get('symbol', ''),
                pnl=trade.get('pnl', 0),
                date=trade.get('date', '')
            )
            grid.add_widget(item)
    
    def update_config_grid(self):
        grid = self.ids.get('config_grid')
        if not grid:
            return
        grid.clear_widgets()
        
        config_items = [
            ('base_size', cfg.get('base_size', 0.08), False),
            ('base_tp', cfg.get('base_tp', 0.0888), False),
            ('base_sl', cfg.get('base_sl', 0.03), False),
            ('max_pos', cfg.get('max_pos', 50), False),
            ('max_buys', cfg.get('max_buys', 10), False),
            ('min_trade', cfg.get('min_trade', 2.0), False),
            ('min_hold_hours', cfg.get('min_hold_hours', 8), False),
            ('trailing_stop_pct', cfg.get('trailing_stop_pct', 0.0666), False),
            ('build', cfg.get('build', True), True),
            ('pyramid_threshold', cfg.get('pyramid_threshold', 5.0), False),
            ('scan_size', cfg.get('scan_size', 60), False),
            ('static_stop_loss_enabled', cfg.get('static_stop_loss_enabled', False), True),
            ('circuit_breaker_enabled', cfg.get('circuit_breaker_enabled', False), True),
        ]
        
        for key, val, is_bool in config_items:
            row = ConfigRow(key=key, value=val, is_boolean=is_bool)
            grid.add_widget(row)
    
    def update_watchlist_grid(self):
        from nostop import WATCHLIST
        grid = self.ids.get('watchlist_grid')
        if not grid:
            return
        grid.clear_widgets()
        
        for sym in WATCHLIST[:100]:
            item = WatchlistItem(symbol=sym)
            grid.add_widget(item)
        
        if len(WATCHLIST) > 100:
            grid.add_widget(Label(
                text=f'... and {len(WATCHLIST) - 100} more',
                size_hint_y=None, height=dp(30),
                color=(0.6, 0.6, 0.6, 1)
            ))
    
    def toggle_trading(self):
        global trading
        trading = not trading
        self.trading_enabled = trading
        
        btn = self.ids.get('start_stop_btn')
        if btn:
            btn.text = 'STOP' if trading else 'START'
            btn.background_color = (0.6, 0.2, 0.2, 1) if trading else (0.2, 0.6, 0.2, 1)
        
        logger.info(f"Trading toggled: {trading}")
    
    def sell_position(self, symbol):
        success, msg = manual_sell(symbol)
        popup = Popup(title='Sell Order',
                      content=Label(text=msg),
                      size_hint=(0.7, 0.3))
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 2)
    
    def add_watchlist_symbol(self, symbol):
        if symbol.strip():
            add_to_watchlist(symbol.strip().upper())
            self.update_watchlist_grid()
            self.ids.add_symbol_input.text = ''
    
    def remove_watchlist_symbol(self, symbol):
        remove_from_watchlist(symbol)
        self.update_watchlist_grid()
    
    def reset_watchlist(self):
        reset_watchlist()
        self.update_watchlist_grid()
    
    def update_config(self, key, value):
        cfg[key] = value
        save_config()
        logger.info(f"Config updated: {key} = {value}")
    
    def save_config(self):
        save_config()
        popup = Popup(title='Config Saved',
                      content=Label(text='Configuration saved successfully'),
                      size_hint=(0.6, 0.2))
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 1.5)
    
    def reset_config(self):
        from nostop import cfg as default_cfg
        default_values = {
            'base_size': 0.08, 'base_tp': 0.0888, 'base_sl': 0.03,
            'max_pos': 50, 'max_buys': 10, 'min_trade': 2.0,
            'min_hold_hours': 8, 'trailing_stop_pct': 0.0666,
            'build': True, 'pyramid_threshold': 5.0, 'scan_size': 60,
        }
        for key, val in default_values.items():
            cfg[key] = val
        save_config()
        self.update_config_grid()
        popup = Popup(title='Config Reset',
                      content=Label(text='Reset to defaults'),
                      size_hint=(0.6, 0.2))
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 1.5)
    
    def clear_history(self):
        def confirm_clear(instance):
            clear_all_history()
            popup.dismiss()
            confirm_popup = Popup(title='Cleared',
                                  content=Label(text='All history cleared'),
                                  size_hint=(0.6, 0.2))
            confirm_popup.open()
            Clock.schedule_once(lambda dt: confirm_popup.dismiss(), 1.5)
        
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        content.add_widget(Label(text='Clear all trade history?\nThis will reset cash to $1000'))
        btn_layout = BoxLayout(spacing=dp(10), size_hint_y=0.3)
        btn_layout.add_widget(Button(text='CANCEL', on_press=lambda x: popup.dismiss()))
        btn_layout.add_widget(Button(text='CLEAR', background_color=(0.8, 0.2, 0.2, 1), on_press=confirm_clear))
        content.add_widget(btn_layout)
        
        popup = Popup(title='Confirm Clear', content=content, size_hint=(0.7, 0.3))
        popup.open()


class ConfigScreen(Screen):
    pass


class TradingBotApp(App):
    def build(self):
        # Set window size for desktop testing
        Window.size = (400, 700)
        Window.clearcolor = (0.05, 0.05, 0.08, 1)
        
        sm = ScreenManager()
        main_screen = MainScreen(name='main')
        sm.add_widget(main_screen)
        
        # Load config grid after UI is built
        Clock.schedule_once(lambda dt: main_screen.update_config_grid(), 0.5)
        Clock.schedule_once(lambda dt: main_screen.update_watchlist_grid(), 0.5)
        
        return sm
    
    def on_start(self):
        logger.info("App starting...")


if __name__ == '__main__':
    TradingBotApp().run()
