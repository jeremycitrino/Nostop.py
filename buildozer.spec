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

# Dependencies
# lxml/html5lib/bs4 removed â€“ yfinance uses stdlib html.parser as fallback
requirements    = python3,kivy==2.3.0,requests,urllib3,charset-normalizer,certifi,idna,multitasking,six,yfinance,numpy,pandas

# Orientation
orientation     = portrait

# Android-specific
android.permissions          = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK,FOREGROUND_SERVICE
android.api                  = 33
android.minapi               = 21
android.ndk                  = 25b
android.ndk_api              = 21
android.archs                = arm64-v8a
android.accept_sdk_license   = True

# Allow cleartext traffic for localhost WebView dashboard
android.manifest.attributes  = android:usesCleartextTraffic="true"

# p4a / bootstrap
p4a.bootstrap                = sdl2

[buildozer]

log_level    = 2
warn_on_root = 1
