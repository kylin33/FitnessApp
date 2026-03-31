# FitnessApp
android app for fit 

## Android permission

The build configuration is defined in `pyproject.toml`.

Current size-oriented defaults:

- exclude `.git`, `.github`, `.venv` and caches from the packaged app
- split Android builds per ABI to avoid a single fat APK
- keep only the `WAKE_LOCK` Android permission required by this app

Recommended build commands:

- Play Store: `flet build aab`
- Local install with smaller APKs: `flet build apk`

If you only need a package for a real Android phone, you can further reduce output size by building only arm64:

`flet build apk --arch arm64-v8a`
