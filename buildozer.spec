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
# Removed: lxml, html5lib, webencodings, beautifulsoup4 (all optional yfinance HTML parsers)
# Removed: frozendict, platformdirs, appdirs (pulled in automatically by pip/p4a)
# Removed: pycparser, cffi, cryptography (not needed at runtime for yfinance on Android)
# yfinance uses html.parser (stdlib) when lxml/html5lib are absent â€” this is fine
requirements    = python3,kivy==2.3.0,requests,urllib3,charset-normalizer,certifi,idna,multitasking,six,yfinance,numpy,pandas

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

# p4a / bootstrap
p4a.bootstrap           = sdl2

[buildozer]

# Log level: 0=error 1=info 2=debug
log_level       = 2
warn_on_root    = 1
