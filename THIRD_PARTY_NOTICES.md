# Third-Party Notices

Live Scribe uses third-party components including Faster-Whisper,
CTranslate2, Whisper-compatible model files, Hugging Face Hub, tokenizers,
PyAV, ONNX Runtime, python-sounddevice, PortAudio, NumPy, python-docx, lxml,
Tk, and PyInstaller.

Each component remains subject to its own license and terms. Portable release
builds must retain license files collected by PyInstaller and any notices
required by the component authors. Speech-model weights are not redistributed
in the base buyer package; they are downloaded from their model host when the
buyer chooses a model for the first time.

The `engines` registry also names optional researched projects such as
DeepFilterNet, Qwen3-ASR, and whisper.cpp. They are not bundled or activated in
v0.7.5. Before distributing any optional pack, review its code license, model
license, model card, commercial-use terms, attribution requirements, binary
redistribution requirements, and transitive dependencies.

Before every commercial release, generate an exact dependency inventory,
retain full license texts, scan the final archives, and test on the target
operating systems.

## SoundCard

Live Scribe uses SoundCard for system-output and livestream audio capture.
SoundCard is distributed under the BSD 3-Clause License. Its original license
and copyright remain with its authors.

## CustomTkinter

Live Scribe uses CustomTkinter for its modern cross-platform interface. CustomTkinter is distributed under the MIT License. Its original license and copyright remain with its authors.
