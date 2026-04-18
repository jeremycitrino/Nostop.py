from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
import subprocess
import os
import signal

class TradingBotApp(App):
    def build(self):
        self.process = None
        layout = BoxLayout(orientation='vertical', spacing=10, padding=20)
        
        self.status = Label(text="Bot: STOPPED", size_hint=(1, 0.3))
        self.start_btn = Button(text="START BOT", size_hint=(1, 0.2))
        self.stop_btn = Button(text="STOP BOT", size_hint=(1, 0.2))
        self.url_label = Label(text="http://localhost:8888", size_hint=(1, 0.2), font_size='12sp')
        
        self.start_btn.bind(on_press=self.start_bot)
        self.stop_btn.bind(on_press=self.stop_bot)
        
        layout.add_widget(self.status)
        layout.add_widget(self.start_btn)
        layout.add_widget(self.stop_btn)
        layout.add_widget(self.url_label)
        
        return layout
    
    def start_bot(self, instance):
        if self.process is None or self.process.poll() is not None:
            self.status.text = "Bot: STARTING..."
            self.process = subprocess.Popen(
                ['python', 'nostop.py', '--daemon'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            Clock.schedule_once(lambda dt: self.check_running(), 2)
    
    def check_running(self):
        if self.process and self.process.poll() is None:
            self.status.text = "Bot: RUNNING (dashboard ready)"
        else:
            self.status.text = "Bot: FAILED TO START"
    
    def stop_bot(self, instance):
        if self.process and self.process.poll() is None:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except:
                self.process.terminate()
            self.status.text = "Bot: STOPPED"
            self.process = None

if __name__ == '__main__':
    TradingBotApp().run()
