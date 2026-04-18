[app]

# (str) Title of your application
title = Trading Bot

# (str) Package name
package.name = tradingbot

# (str) Package domain (needs to be unique)
package.domain = org.example.tradingbot

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include/ignore
source.include_exts = py,png,jpg,kv,atlas,json,db
source.exclude_exts = spec
source.exclude_dirs = tests, bin, build, .buildozer, .git, __pycache__, venv

# (list) Application requirements
# IMPORTANT: setuptools==58.0.0 is pinned to avoid backend errors
requirements = python3,kivy==2.1.0,pyjnius,android,plyer,yfinance,requests,setuptools==58.0.0

# (str) Custom source folders for requirements
# (setuptools/pip requirements files)
# requirements.source = requirements.txt

# (str) Presplash file (must be in source.dir)
# presplash.filename = %(source.dir)s/presplash.png

# (str) Icon file (must be in source.dir)
# icon.filename = %(source.dir)s/icon.png

# (str) Supported orientation (one of: landscape, portrait, all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your app supports
android.minapi = 21

# (int) Android SDK version to use
android.sdk = 33

# (str) Android NDK version to use
android.ndk = 25b

# (bool) Use AndroidX instead of support library
android.use_androidx = True

# (str) Android logcat filters (e.g. 'ActivityManager:I MyApp:D *:S')
# android.logcat_filters = 

# (bool) Copy library instead of making a libsymlink
android.copy_libs = True

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.arch = arm64-v8a

# (list) Gradle dependencies to add
# android.gradle_dependencies = 'com.android.support:support-v4:27.1.1'

# (list) Java classes to add
# android.add_java_src =

# (str) python-for-android branch to use
# p4a.branch = develop

# (str) python-for-android git clone directory (if not set, uses p4a.branch)
# p4a.source_dir = 

# (bool) Enable hot reloading (requires python-for-android branch with reloader support)
# android.hotreload = False

# (str) Extra add any custom requirements for the bootstrap (comma separated)
# bootstrap.extra_jars =

# (str) Fully qualified android launcher class name (for custom bootstraps)
# android.entrance = 

# (str) Launchable activity (e.g. org.test.app.MainActivity) for custom bootstraps
# android.launcher = 

# (list) Permissions to add to AndroidManifest.xml (besides the default ones)
# android.extra_manifest_permissions = 

# (bool) Enable/disable permission checking (off by default)
# android.check_permissions = False

# (str) Android NDK directory (if using custom NDK)
# android.ndk_path = 

# (str) Android SDK directory (if using custom SDK)
# android.sdk_path = 

# (bool) Use deprecated NDK r17c (for compatibility)
# android.use_deprecated_ndk = False

# (str) Android entry point (e.g. main.py)
# android.entrypoint = 

# (list) Prebuild commands to run before build
# CRITICAL FIX: Upgrades setuptools to avoid BackendUnavailable error
android.add_prebuild_command = pip install --upgrade setuptools

# (list) Postbuild commands to run after build
# android.add_postbuild_command = 

# (list) Commands to run before the build starts (inside build container)
# android.pre_build_commands = 

# (list) Commands to run after the build finishes (inside build container)
# android.post_build_commands = 

# (list) Meta-data to add to AndroidManifest.xml (key, value)
# android.manifest_metadata = 

# (list) Meta-data to add to the activity section (key, value)
# android.manifest_activity_metadata = 

# (str) Launch mode for the main activity (standard, singleTop, singleTask, singleInstance)
# android.manifest_launch_mode = 

# (list) Additional Java paths (e.g. for third-party jars)
# android.add_src =

# (list) Additional Java libraries (e.g. for third-party jars)
# android.add_libs_java =

# (str) Path to custom AndroidManifest.xml (replaces default)
# android.manifest = 

# (str) Path to custom strings.xml (replaces default)
# android.strings = 

# (str) Path to custom build.gradle (replaces default)
# android.gradle = 

# (str) Path to custom permissions.xml (replaces default)
# android.permissions_xml = 

# (str) Path to custom src/main/res directory (overrides default)
# android.resources =

# (bool) Use a fullscreen splash screen (PWA style)
# android.splash_fullscreen = False

# (str) Splash image to show during boot (use for fullscreen splash)
# android.splash_image = 

# (str) Color of the status bar during splash (e.g. '#123456')
# android.splash_statusbar_color = 

# (str) Color of the splash screen background (e.g. '#123456')
# android.splash_background_color = 

# (str) Icon theme (e.g. 'material')
# android.icon_theme = 

# (bool) Use Gradle's build cache (experimental)
# android.gradle_build_cache = False

# (str) Extra arguments to pass to Gradle (e.g. -PmyProp=value)
# android.gradle_args = 

# (str) Custom python-for-android recipe to use (instead of default)
# p4a.recipe = 

# (str) Custom python-for-android distribution name
# p4a.dist_name = 

# (bool) Enable/disable building with debug symbols
# android.debug_build = True

# (str) Log level for python-for-android (debug, info, warning, error)
# android.p4a_log_level = info

# (str) NDK API level (default is android.minapi)
# android.ndk_api = 

# (list) Architectures to build for (overrides android.arch)
# android.archs = arm64-v8a, armeabi-v7a

# (bool) Enable Java 8 features (e.g. lambda expressions)
# android.java8 = False

# (bool) Enable Kotlin support
# android.kotlin = False

# (str) Kotlin version (if enabled)
# android.kotlin_version = 1.3.72

# (list) Extra JVM arguments for Gradle
# android.gradle_jvm_args = 

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (str) Path to build output directory
build_dir = %(source.dir)s/.buildozer

# (str) Path to bin directory (where APKs will be stored)
bin_dir = %(source.dir)s/bin

# (str) Path to the android SDK directory (if not set, will be downloaded)
# android_sdk_dir = 

# (str) Path to the android NDK directory (if not set, will be downloaded)
# android_ndk_dir = 

# (str) Path to the android ant directory (if not set, will be downloaded)
# android_ant_dir = 

# (str) Path to the java (JDK) directory (if not set, uses JAVA_HOME)
# java_dir = 

# (str) Accept Android SDK licenses automatically (set to True to accept)
android.accept_sdk_license = True

# (str) Path to the Android ABI to use (if not set, will be auto-detected)
# android_abi = 

# (bool) Run the application after build (debug mode)
# android.run = False

# (bool) Automatically restart the ADB server when needed (debug mode)
# android.adb_auto_restart = True

# (str) ADB server host IP (for remote debugging)
# android.adb_host = 127.0.0.1

# (int) ADB server port (for remote debugging)
# android.adb_port = 5037

# (str) Command to execute when the APK is installed (debug mode)
# android.command_install = adb -s %(android_serial)s install -r %(apk_file)s

# (str) Command to execute when the APK is launched (debug mode)
# android.command_run = adb -s %(android_serial)s shell start -a android.intent.action.MAIN -n org.example.tradingbot/org.kivy.android.PythonActivity

# (str) Android device serial number (if multiple devices connected)
# android.serial = 

# (str) Path to the application's icon (for iOS)
# ios.icon.filename = %(source.dir)s/icon.png

# (str) Path to the application's launch image (for iOS)
# ios.launch_image.filename = %(source.dir)s/launch.png

# (bool) Use the iOS keyboard (for iOS)
# ios.use_keyboard = False

# (str) Path to the .pem certificate for iOS signing
# ios.codesign.certificate = 

# (str) Path to the .mobileprovision profile for iOS signing
# ios.codesign.profile = 

# (str) iOS bundle identifier (if different from package.domain)
# ios.bundle_identifier = 

# (bool) Enable iOS multitasking (requires iOS 9+)
# ios.multitasking = False

# (list) iOS frameworks to add
# ios.frameworks = 

# (list) iOS plist entries to add
# ios.plist_items = 

# (list) iOS xib files to add
# ios.xib_files = 
