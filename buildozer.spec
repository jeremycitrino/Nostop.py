[app]

# (str) Title of your application
title = DipBot

# (str) Package name
package.name = dipbot

# (str) Package domain (unique identifier)
package.domain = org.tradingbot

# (str) Source code directory
source.dir = .

# (list) Source files to include
source.include_exts = py,png,jpg,kv,atlas

# (list) Version
version = 1.0.0

# (list) Requirements (optimized for Android)
requirements = python3==3.11.0,kivy==2.2.1,yfinance==0.2.28,requests==2.31.0,numpy==1.24.3,pandas==2.0.3,android

# (str) Presplash filename
# presplash.filename = %(source.dir)s/presplash.png

# (str) Icon filename
# icon.filename = %(source.dir)s/icon.png

# (list) Permissions
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,FOREGROUND_SERVICE,WAKE_LOCK,ACCESS_NETWORK_STATE

# (int) Android API level
android.api = 33

# (int) Minimum API level
android.minapi = 21

# (int) Android SDK version
android.sdk = 33

# (str) Android NDK version
android.ndk = 25b

# (bool) Use AndroidX
android.use_androidx = true

# (bool) Enable Java source
android.enable_java_source = true

# (list) Gradle dependencies
android.gradle_dependencies = 'androidx.core:core:1.9.0','androidx.work:work-runtime:2.8.1'

# (bool) Fullscreen mode
fullscreen = 1

# (str) Orientation
orientation = portrait

# (bool) Allow Internet
wifi = True

# (bool) Allow backup
android.allow_backup = True

# (str) Log level
log_level = 2

# (bool) Debug mode (set to 0 for release)
android.debug = 0

# (bool) Enable ARMv7 (most compatible)
android.arch = arm64-v8a

# (str) NDK API
android.ndk_api = 21

# (str) Java JDK
java_jdk = 17

# (bool) Copy Python libs
copy_libs = 1

[buildozer]

# (int) Log level
log_level = 2

# (bool) Warn on higher version
warn_on_higher_version = False

# (str) Android SDK directory
# android_sdk = 

# (str) Android NDK directory
# android_ndk = 

# (str) Java JDK directory
# java_jdk =

# (bool) Accept SDK license
android.accept_sdk_license = True
