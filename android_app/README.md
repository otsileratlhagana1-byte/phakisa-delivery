# Android app wrapper

This is the Android Studio project for Phakisa Delivery. It opens the deployed Flask service inside a native Android WebView and requests location permission for driver GPS.

Before building:
1. Deploy the Flask app to Render.
2. Replace YOUR-PHAKISA-RENDER-URL.onrender.com in MainActivity.java with your HTTPS Render URL.
3. Open this `android_app` folder in Android Studio.
4. Build > Generate App Bundle / APK > Generate APK.

An APK cannot be produced in this environment because Android SDK/Gradle build tools are not installed here.
