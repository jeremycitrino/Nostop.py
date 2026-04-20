[app]

# Application information
title = DipBot
package.name = dipbot
package.domain = org.tradingbot
version = 1.0.0
version.regex = 
version.filename = 

# Source files
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
source.exclude_exts = spec
source.include_patterns = 
source.exclude_patterns = 

# Requirements
requirements = python3,kivy,yfinance,requests,numpy,pandas

# Android specific
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 30
android.minapi = 21
android.ndk = 25b
android.sdk = 30
android.arch = armeabi-v7a
android.allow_backup = True
android.add_services = 
android.add_authorities = 
android.add_presplash = 
android.add_activity = 
android.add_meta_data = 
android.gradle_dependencies = 
android.enable_androidx = true

# Screen
fullscreen = 1
orientation = portrait

# Logging
log_level = 2

# Private libraries
private.deps = True

# NDK version
android.ndk_api = 21

# Debug
android.debug = 0

[buildozer]

# Global settings
log_level = 2
warn_on_higher_version = False
android.accept_sdk_license = True
