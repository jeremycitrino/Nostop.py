[app]

# Application name
title = Trading Bot

# Package name
package.name = tradingbot

# Package domain (reverse domain notation)
package.domain = org.example.tradingbot

# Version
version = 1.0

# Source code directory
source.dir = .

# File extensions to include
source.include_exts = py,png,jpg,kv,atlas,json,db

# File extensions to exclude
source.exclude_exts = spec

# Directories to exclude
source.exclude_dirs = tests, bin, build, .buildozer, .git, __pycache__, venv

# Dependencies (NO yfinance/pandas/numpy!)
requirements = python3,kivy==2.1.0,pyjnius,android,plyer,requests,setuptools==58.0.0

# Orientation
orientation = portrait

# Fullscreen
fullscreen = 0

# Android permissions
android.permissions = INTERNET, FOREGROUND_SERVICE, WAKE_LOCK

# Android API level
android.api = 33

# Minimum Android version
android.minapi = 21

# NDK version
android.ndk = 25b

# Use AndroidX
android.use_androidx = True

# Copy libraries
android.copy_libs = True

# Architecture (arm64-v8a for modern phones)
android.archs = arm64-v8a

# Keep screen on
android.wakelock = True

# Run as foreground service
android.foreground = True

# Presplash image (optional - remove if no image)
# presplash.filename = %(source.dir)s/presplash.png

# Icon (optional - remove if no icon)
# icon.filename = %(source.dir)s/icon.png

[buildozer]

# Log level (0=error,1=warn,2=info,3=debug)
log_level = 2

# Build directory
build_dir = ./.buildozer

# Binary directory  
bin_dir = ./bin

# Accept SDK license automatically
android.accept_sdk_license = True
