# FitnessApp

Android fitness timer app built with Kotlin + Jetpack Compose.

## Local build

Use the Gradle wrapper committed in this repo:

- Run unit tests: `./gradlew testDebugUnitTest`
- Build debug APK: `./gradlew assembleDebug`

The generated APK will be written to:

- `app/build/outputs/apk/debug/`

## GitHub Actions

The workflow in `.github/workflows/build.yml` builds the Android app on every push, pull request, and manual dispatch. It validates the Gradle wrapper, runs unit tests, assembles a debug APK, and uploads the APK as an artifact.
