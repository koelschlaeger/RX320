# RX320 — notes for Claude Code

PyQt6 control panel for the Ten-Tec RX-320 receiver. See `README.md` for what
the app does and how users run it; this file covers how to work on it.

## Commands

- `uv sync` — create/update `.venv` from `uv.lock` (Python pinned to 3.13 in
  `.python-version`)
- `uv run pytest` — full suite, headless, about 6 s
- `uv run src/main.py` — run the app
- `uv add <pkg>` / `uv add --dev <pkg>` — never edit dependencies by hand;
  there are no `requirements*.txt` files

## Safety

- **Never send commands to the real radio.** A real RX-320 may be attached
  (e.g. `/dev/ttyUSB0`). Test against the fakes in `tests/fakes.py` instead:
  `FakeRadio` (stands in for the `RX320` wrapper), `FakeSerial` (in-memory
  port) and `PtyRadio` (a pseudo-terminal acting as the device).
- Don't run the app against the real settings when testing: tests replace
  `gui.main_window.open_settings()` with a temporary INI file; for manual
  headless runs on Linux set `XDG_CONFIG_HOME` to a scratch directory.

## Architecture

- `src/RX320/RX320_Data.py` — single source of truth for radio facts: frozen
  record dataclasses (`Mode`, `Filter`, `AGCMode`, `VolumeTarget`,
  `SerialSettings`), the command tables, tuning limits, power-up defaults,
  attenuation range (codes 0–63 over 96 dB) and `SIGNAL_MAX`. Driver, wrapper
  and GUI derive from it; don't hard-code these values elsewhere.
- `src/RX320/RX320_Driver.py` — serial protocol. Setters queue commands; a
  daemon worker thread (`_service_queue`) sends them and polls signal strength
  (`X`) after `POLL_INTERVAL` idle. `_queue_write` merges queued commands: a
  new command replaces a waiting one of the same kind in place (keeps order,
  so volume stays last on connect), and `C` (both volumes) supersedes waiting
  `A`/`V`. `open_serial()` on a running driver is a no-op.
  `measure()` queues a signal measurement (settle, then back-to-back `X` polls) and returns a `Future`; commands are never merged across a waiting measurement, and closing or losing the port cancels pending ones.
  `close_serial()` ends measurements at once but still sends the commands
  already queued (for up to `DRAIN_TIMEOUT`), so settings restored just
  before a disconnect reach the radio; after a lost port it doesn't wait.
- `src/RX320/RX320.py` — the interface the GUI uses (`connect`, `set_mode`,
  `set_filter`, …; `connected` and `signal_strength` are live properties).
  Mode and filter changes retune, because the tune command's offsets depend on
  them (required by the programmer's guide).
- `src/gui/main_window.py` — the window. Gets the radio passed in
  (`MainWindow(sdr)`). On connect, `_sync_radio_to_gui()` sends every setting
  with volume last. `_update_status` (every 250 ms) detects a lost connection
  and updates the signal meter. Settings persist via `open_settings()`
  (native QSettings storage per OS); volume is never restored. "Scan…" opens
  the scan window (one instance, closed with the app): while a scan runs the
  radio controls are locked and the radio is muted, in `SCAN_MODE` (CW) with
  `scan_filter()` (the widest filter no wider than the step) and `SCAN_AGC`
  (Fast); afterwards `_sync_radio_to_gui()` restores everything, volume last.
  Disconnect and closing the app stop a running scan first, so it restores
  while the port is still open.
- `src/gui/radio_controller.py` — VFO A/B state, no Qt.
- `src/gui/scanner.py` — signal-strength scan logic, no Qt: frequency plan
  (whole Hz, both ends, clamped), `Scanner` driven by a GUI timer calling
  `poll()` (one measurement outstanding at a time), time estimate, and
  `nearest_point()` for click-to-tune.
- `src/gui/scan_window.py` — separate scan window: inputs with a time
  estimate, Start/Stop, live pyqtgraph plot (unreadable steps are gaps; it
  works in Hz, because pyqtgraph's automatic SI prefix on MHz data would
  label sub-MHz scans "mMHz"),
  click-to-tune after a scan. It tunes the radio itself while scanning and
  talks to the main window only through signals: `scanStarted` (before the
  first tune), `scanFinished` and `tuneRequested(freq)`. Scan defaults are in
  `gui/constants.py`; its inputs are saved under `scan/` in the main
  window's settings, which hands it a `QSettings` to read and write
  (corrupt values fall back via `gui/settings_utils.read_setting()`).

## Conventions

- PEP 8 in `src/RX320/` (methods snake_case, class constants UPPER_CASE).
  GUI methods are snake_case (`on_<what>` for slots), but widget attributes
  keep Qt-style camelCase (`sliderBW`, `comboBoxSerialPort`), as do
  `MainWindow`'s own `Modes`/`AGCModes`/`Filters`.
- Changes come with tests. For behavior changes, write the failing test first.
- The protocol reference is `doc/rx320prg.pdf` (Ten-Tec's programmer's guide).
  Command bytes are locked by the known-good byte tests in
  `tests/test_driver.py`.

## CI

`.github/workflows/tests.yml` runs `uv sync --locked` + `uv run pytest` on
Ubuntu, Windows and macOS. Things learned the hard way:

- `astral-sh/setup-uv` publishes no major-only tags after v7, so it is pinned
  by commit SHA; check a tag exists before referencing one.
- Windows' minimum window width (~808 px) is larger than Linux's (~673 px):
  don't assert fixed window widths.
- On macOS, closing a pseudo-terminal blocks while another thread reads it;
  `PtyRadio` therefore stops its reader thread before closing.
- Hang diagnostics: pytest `faulthandler_timeout = 60` dumps all thread
  stacks, and the job times out after 15 minutes.
- Dependabot updates actions and `uv.lock` monthly.

## Backlog

Open work is tracked in GitHub issues.
