[app]

# App metadata
title           = DIP BOT
package.name    = dipbot
package.domain  = org.dipbot

# Source
source.dir      = .
source.include_exts = py,png,jpg,kv,atlas,json,html

# Version
version         = 1.0.0

# Dependencies â€“ yfinance + its chain, requests, kivy
requirements    = python3,kivy==2.3.0,requests,urllib3,charset-normalizer,certifi,idna,multitasking,lxml,html5lib,six,webencodings,beautifulsoup4,yfinance,numpy,pandas,frozendict,platformdirs,appdirs,pycparser,cffi,cryptography

# Orientation
orientation     = portrait

# Android-specific
android.permissions     = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK,FOREGROUND_SERVICE
android.api             = 33
android.minapi          = 21
android.ndk             = 25b
android.ndk_api         = 21
android.arch            = arm64-v8a

# Allow cleartext for localhost WebView
android.manifest.attributes = android:usesCleartextTraffic="true"

# Keep app alive (foreground service)
android.service             = dipbot_service:org.kivy.android.PythonService

# Icons (place a 512Ã—512 icon.png next to this file â€“ optional)
# icon.filename = icon.png
# presplash.filename = presplash.png

# p4a / bootstrap
p4a.bootstrap           = sdl2
# p4a.branch            = master   # uncomment to use latest p4a

[buildozer]

# Log level: 0=error 1=info 2=debug
log_level       = 2
warn_on_root    = 1
