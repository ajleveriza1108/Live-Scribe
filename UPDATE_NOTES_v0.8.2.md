# Live Scribe v0.8.2

## Dropdown startup hotfix

- Fixed the recursion crash in `WholeClickableDropdown`.
- CustomTkinter initialization-time `configure()` calls are now safe.
- Internal label synchronization calls the base CTkButton implementation
  directly instead of re-entering the dropdown override.
- Full-control clicking and disabled microphone entries remain supported.
- Added a regression test that reproduces the original Windows startup
  sequence.
