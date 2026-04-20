
"""
Android Foreground Service - Keeps bot running in background
"""

import time
import threading
from jnius import autoclass

PythonService = autoclass('org.kivy.android.PythonService')
Context = autoclass('android.content.Context')

class TradingService(PythonService):
    """Android service to keep bot alive in background"""
    
    def onCreate(self):
        super().onCreate()
        self.start_thread()
    
    def start_thread(self):
        """Start the trading bot in a background thread"""
        thread = threading.Thread(target=self.run_bot)
        thread.daemon = True
        thread.start()
    
    def run_bot(self):
        """Run the trading engine"""
        from nostop import start_bot
        start_bot()

# Service entry point
if __name__ == '__main__':
    TradingService().run()
