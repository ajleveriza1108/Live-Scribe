# Live Scribe v0.6.1

## First-run PC capability check

Live Scribe now checks the local computer before offering speech-model
downloads.

### Checked locally

- System RAM
- CPU thread count
- Processor architecture
- Free storage in the portable model location
- CTranslate2 NVIDIA CUDA access
- NVIDIA name and VRAM when available

No hardware information is uploaded.

### Model decisions

Each model is classified as:

- Recommended
- May run slowly / uncertain
- Unavailable for download

The app disables a download only when it detects a clear minimum failure, such
as insufficient RAM, storage, or unsupported architecture. CPU speed and
uncertain GPU support produce a note instead of a block.

The largest model receives a caution note when Live Scribe cannot confidently
predict that it will run well.

### Portable recheck

The Models page includes Check This PC Again for users who move the portable app
to another computer, free storage, add RAM, or configure an NVIDIA GPU.
