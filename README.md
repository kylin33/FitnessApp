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

To make CI APKs upgradeable over previous installs on your phone, configure a fixed signing key in GitHub repository secrets:

- `ANDROID_SIGNING_KEYSTORE_BASE64` (base64 of your `.jks/.keystore` file)
- `ANDROID_SIGNING_KEYSTORE_PASSWORD`
- `ANDROID_SIGNING_KEY_ALIAS`
- `ANDROID_SIGNING_KEY_PASSWORD`

When these secrets are present, CI also builds and uploads `app-release-signed`. Use that APK for installation/upgrade.

Example commands to generate and encode a keystore locally:

```bash
keytool -genkeypair \
  -v \
  -storetype PKCS12 \
  -keystore fitness-release.jks \
  -alias fitnessapp \
  -keyalg RSA \
  -keysize 2048 \
  -validity 36500

base64 -w 0 fitness-release.jks
```

If you previously installed an APK with a different signature, Android requires one-time uninstall before switching to this new signing key. After that, later CI builds can be installed as upgrades.
