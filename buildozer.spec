[app]

title = DipBot
package.name = dipbot
package.domain = org.tradingbot

source.dir = .
source.include_exts = py

requirements = python3,kivy,yfinance,requests,numpy,pandas

android.permissions = INTERNET
android.api = 30
android.minapi = 21
android.ndk = 25b
android.sdk = 30

fullscreen = 1
orientation = portrait

log_level = 2

[buildozer]
log_level = 2
android.accept_sdk_license = True
