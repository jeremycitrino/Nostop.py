[app]

title = Trading Bot
package.name = tradingbot
package.domain = org.example.tradingbot
version = 1.0
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,db
source.exclude_exts = spec
source.exclude_dirs = tests, bin, build, .buildozer, .git, __pycache__, venv
requirements = python3,kivy==2.1.0,pyjnius,android,plyer,yfinance,requests,setuptools==58.0.0
orientation = portrait
fullscreen = 0
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.use_androidx = True
android.copy_libs = True
android.arch = arm64-v8a
android.add_prebuild_command = pip install --upgrade setuptools

[buildozer]

log_level = 2
build_dir = ./.buildozer
bin_dir = ./bin
android.accept_sdk_license = True
