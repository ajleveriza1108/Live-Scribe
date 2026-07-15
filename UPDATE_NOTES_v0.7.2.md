# Live Scribe v0.7.2

## Model download progress correction

- A model download can no longer display 100% before the model is ready.
- Downloading and finalizing phases are capped at 99%.
- The finalizing stage uses an animated progress bar.
- The UI explains that remaining files are being placed and verified.
- The ready state is the only state that displays a full 100% bar.
- Existing resumed bytes no longer create false terabyte-per-second speed.
- Unrealistic local filesystem progress spikes are excluded from the speed
  estimate.
- Zero-second ETA is hidden while files are still being finalized.
- Download units use decimal KB, MB, and GB to better match displayed model
  sizes.
