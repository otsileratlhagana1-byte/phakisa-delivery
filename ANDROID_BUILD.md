# Build a downloadable Android APK

## Easiest method: GitHub Actions

1. Create a GitHub repository named `phakisa-delivery`.
2. Upload the contents of this project to the repository.
3. Open `android_app/app/src/main/java/za/co/phakisa/delivery/MainActivity.java`.
4. Replace:
   `https://YOUR-PHAKISA-RENDER-URL.onrender.com`
   with the real HTTPS URL of your deployed Phakisa Delivery Flask site.
5. Commit the change.
6. Open GitHub → Actions → **Build Phakisa Delivery APK**.
7. Run the workflow if it did not start automatically.
8. Open the completed workflow → Artifacts → download `phakisa-delivery-debug-apk`.
9. Extract the ZIP and install `app-debug.apk` on Android.

## Android Studio method

Open the `android_app` folder in Android Studio, wait for Gradle sync, then:
Build → Generate App Bundle / APK → Generate APK.

## Important

The APK is a native Android WebView shell around your deployed Phakisa Delivery service. The Flask service must be online for the app to work.

For production, use HTTPS and a production database such as PostgreSQL rather than the local SQLite database.
