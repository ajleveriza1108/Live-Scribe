# Windows selected-app audio helper

`LiveScribeApplicationLoopback.exe` is built by the repository workflow:

```text
.github/workflows/build-windows-app-audio-helper.yml
```

The workflow checks out Microsoft's official Windows ApplicationLoopback
sample, restores its WIL package, changes the temporary WAV sharing mode so
Live Scribe can read it while capture is active, builds x64 Release, and
commits the renamed executable into this folder.

Until the executable exists, **Selected app audio (Windows)** is visible but
disabled. Normal microphone and whole-computer audio remain available.

The helper requires Windows build 20348 or newer.
