[app]

# (str) Title of your application
title = Trading Bot

# (str) Package name
package.name = tradingbot

# (str) Package domain (needed for android/ios packaging)
package.domain = org.example

# (str) Source directory where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,json,txt

# (list) Application version
version = 0.1

# (list) Application requirements
# Added setuptools to fix build backend error
requirements = python3,kivy==2.1.0,pyjnius,android,plyer,yfinance,requests,setuptools

# (str) Presplash of the application
presplash.filename = %(source.dir)s/presplash.png

# (str) Icon of the application
icon.filename = %(source.dir)s/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (str) The Android arch to build for
android.archs = arm64-v8a

# (int) Android API to use
android.api = 30

# (int) Minimum API required
android.minapi = 21

# (str) Android NDK version to use (25b is stable with p4a develop)
android.ndk = 25b

# (list) Gradle dependencies
android.gradle_dependencies = 'androidx.core:core:1.6.0'

# (bool) Use Android private storage (True) or SD card (False)
android.private_storage = False

# (list) Android services (name:entrypoint)
android.services = service:service.py

# (list) Android permissions
android.permissions = INTERNET,WAKE_LOCK,FOREGROUND_SERVICE,ACCESS_NETWORK_STATE

# (str) Additional manifest entries – allows cleartext (HTTP) for local dashboard
android.manifest_extra = <application android:usesCleartextTraffic="true" />

# (bool) Run service in foreground
android.foreground_service = True

# (bool) Auto‑restart service if killed
android.service_auto_restart = True

# (str) Notification channel ID (Android 8+)
android.notification_channel_id = tradingbot_channel

# (str) Notification channel name
android.notification_channel_name = Trading Bot Service

# (int) Notification ID
android.notification_id = 1001

# (str) Notification title
android.notification_title = Trading Bot

# (str) Notification text
android.notification_text = Bot is running in background

# (bool) Automatically accept Android SDK licenses
android.accept_sdk_license = True

# (str) python-for-android branch to use (develop is more up‑to‑date)
p4a.branch = develop

# (str) Bootstrap to use (sdl2 for Kivy apps)
p4a.bootstrap = sdl2

# (str) Service which will be started automatically
p4a.service = service

# (str) Main python file entry point
p4a.main = main.py

# (int) Log level (2 = debug, helps troubleshoot build issues)
log_level = 2
