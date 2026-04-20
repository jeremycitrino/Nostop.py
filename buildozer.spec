[app]

# (str) Title of your application
title = DipBot

# (str) Package name
package.name = dipbot

# (str) Package domain (needs to be unique)
package.domain = org.tradingbot

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (relative to source.dir)
source.include_exts = py,png,jpg,kv,atlas

# (list) Requirements (CRITICAL: all dependencies here)
requirements = python3,kivy,kivymd,requests,yfinance,numpy,pandas,android

# (str) Presplash file (loading screen)
# presplash.filename = %(source.dir)s/presplash.png

# (str) Icon of the application
# icon.filename = %(source.dir)s/icon.png

# (list) Permissions
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,FOREGROUND_SERVICE,WAKE_LOCK

# (int) Target Android API
android.api = 33

# (int) Minimum Android API
android.minapi = 21

# (int) Android SDK version
android.sdk = 33

# (str) Android NDK version
android.ndk = 25b

# (bool) Use AndroidX
android.use_androidx = true

# (bool) Enable Java source compilation
android.enable_java_source = true

# (list) Gradle dependencies
android.gradle_dependencies = 'androidx.core:core:1.9.0'

# (bool) Enable Android services
android.add_services = true

# (str) Android logcat filters
android.logcat_filters = *:S python:D

# (bool) Fullscreen
fullscreen = 1

# (str) Orientation
orientation = portrait

# (list) Services (foreground service for background operation)
services = YOUR_PACKAGE:Service

# (bool) Allow Internet
wifi = True

# (bool) Allow Android to restart the app if it crashes
android.allow_backup = True

# (str) Debug mode
# android.debug = 0

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 1

# (bool) Warn if exist a higher version of the buildozer we run
warn_on_higher_version = False

# (str) Path to Android SDK
# android_sdk = 

# (str) Path to Android NDK
# android_ndk = 

# (str) Path to Java JDK
# java_jdk =

# (str) Android entry point
android.entrypoint = org.kivy.android.PythonActivity

# (list) Permissions
android.permissions = INTERNET

# (str) Android NDK API
android.ndk_api = 21
