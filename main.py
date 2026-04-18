from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.utils import platform
from kivy_garden.xwebview import WebView

if platform == 'android':
    from android import AndroidService
    from jnius import autoclass


class TradingBotApp(App):
    def build(self):
        self.service = None
        layout = BoxLayout(orientation='vertical', padding=10, spacing=5)

        self.status = Label(text='Bot: Stopped', size_hint=(1, 0.1))
        layout.add_widget(self.status)

        btn_start = Button(text='Start Bot', size_hint=(1, 0.1))
        btn_start.bind(on_press=self.start_bot)
        layout.add_widget(btn_start)

        btn_stop = Button(text='Stop Bot', size_hint=(1, 0.1))
        btn_stop.bind(on_press=self.stop_bot)
        layout.add_widget(btn_stop)

        self.webview = WebView(url='http://127.0.0.1:8888', size_hint=(1, 0.7))
        layout.add_widget(self.webview)

        return layout

    def start_bot(self, instance):
        if platform == 'android':
            self._create_notification_channel()
            self.service = AndroidService('TradingBot', 'Bot is running')
            self.service.start('')
            self.status.text = 'Bot: Running'
            Clock.schedule_once(lambda dt: self.webview.reload(), 5)

    def stop_bot(self, instance):
        if self.service:
            self.service.stop()
            self.status.text = 'Bot: Stopped'

    def _create_notification_channel(self):
        try:
            Context = autoclass('android.content.Context')
            NotificationManager = autoclass('android.app.NotificationManager')
            NotificationChannel = autoclass('android.app.NotificationChannel')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Build = autoclass('android.os.Build')
            if Build.VERSION.SDK_INT >= 26:
                activity = PythonActivity.mActivity
                manager = activity.getSystemService(Context.NOTIFICATION_SERVICE)
                channel = NotificationChannel(
                    "tradingbot_channel",
                    "Trading Bot Service",
                    NotificationManager.IMPORTANCE_LOW
                )
                manager.createNotificationChannel(channel)
        except Exception as e:
            print(f"Notification error: {e}")


if __name__ == '__main__':
    TradingBotApp().run()
