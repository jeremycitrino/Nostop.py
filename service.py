import threading
from time import sleep

try:
    from android import PythonService
    from jnius import autoclass
    PythonService.mService.setAutoRestartService(True)
    Context = autoclass('android.content.Context')
    PowerManager = autoclass('android.os.PowerManager')
    pm = PythonService.mService.getSystemService(Context.POWER_SERVICE)
    wl = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "TradingBot::WakeLock")
    wl.acquire()
except Exception as e:
    print(f"WakeLock error: {e}")

import nostop

def run():
    try:
        nostop.start_bot()
    except Exception as e:
        print(f"Bot crashed: {e}")
        sleep(10)
        run()

thread = threading.Thread(target=run, daemon=True)
thread.start()

while True:
    sleep(1)
