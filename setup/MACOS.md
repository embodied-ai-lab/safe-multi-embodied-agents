# Option 2: Native macOS

Supported hardware: **Apple Silicon** (M-series) Macs. Both routes below ship arm64-only binaries; there is no SUMO 1.28.0 distribution for Intel Macs (neither a PyPI wheel nor an official installer), and Rosetta does not help because the Python packages are also arm64-only. Intel Mac users should use Sol (`setup/SOL.md`) or a Linux virtual machine (`setup/UBUNTU.md`).

| Apple Silicon Mac | Route |
| --- | --- |
| macOS 15 or newer | **Route A**, PyPI wheel: the same `pip install -r requirements.txt` as Linux |
| macOS 14 or older (installer supports 10.14 and newer) | **Route B**, official `sumo-1.28.0.pkg` plus the two pure-Python packages |

The reason is packaging, not the lab: the `eclipse-sumo` and `sumo-data` 1.28.0 packages on PyPI ship exactly one macOS wheel each, tagged `macosx_15_0_arm64`. On older macOS `pip` reports "No matching distribution found for eclipse-sumo", and route B is the supported alternative. Both routes end with the same `check_environment.py` report and produce identical experiment results.

Tested: Apple Silicon (M5 Pro) on macOS 26.5, both routes, with Homebrew Python 3.12.15. macOS 15 and macOS 14 or older were not tested; their support is inferred from the wheel tag and the installer's declared minimum version.

## Common step: Python 3.12

```bash
brew install python@3.12
/opt/homebrew/opt/python@3.12/bin/python3.12 --version
```

Use the full path shown above when creating the virtual environment if another `python3.12` (pyenv, python.org) is earlier on your `PATH`; Homebrew warns when that is the case. The python.org 3.12 installer also works. Keep the interpreter native: `python3.12 -c "import platform; print(platform.machine())"` must print `arm64`.

## Route A: Apple Silicon on macOS 15 or newer

```bash
cd safe-multi-embodied-agents
/opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python check_environment.py
```

No Homebrew libraries are required. The wheels bundle every shared library they need (Xerces-C, PROJ, GDAL, FOX, X11, and the rest) under `sumo_data/.libs` inside the virtual environment, and the headless `sumo` and `netconvert` load nothing from `/opt/homebrew` or `/opt/X11`. SUMO's documentation still mentions `brew install xerces-c fox proj gdal gl2ps`; that was verified to be unnecessary for 1.28.0 and is not part of this lab's setup. The download is about 175 MB and the environment about 560 MB.

XQuartz is only relevant to the optional `sumo-gui` window; the graded runs never open a window and were verified without any XQuartz library loaded.

## Route B: Apple Silicon on macOS 14 or older

1. Download the official installer from the [SUMO downloads page](https://sumo.dlr.de/docs/Downloads.php#macos): `https://sumo.dlr.de/releases/1.28.0/sumo-1.28.0.pkg` (about 128 MB). Compare its SHA-256 with the value shown on that page before installing:

   ```bash
   shasum -a 256 ~/Downloads/sumo-1.28.0.pkg
   ```

   The package is signed and notarized by the Eclipse Foundation (`pkgutil --check-signature` shows "Developer ID Application: Eclipse Foundation, Inc."). It requires an administrator password and installs `/Library/Frameworks/EclipseSUMO.framework` plus three launcher apps in `/Applications` (sumo-gui, netedit, Scenario Wizard) that need XQuartz; the lab does not use them.

2. The command-line tools live inside the framework. Set `SUMO_HOME` and `PATH` for your shell (for example in `~/.zshrc`):

   ```bash
   export SUMO_HOME=/Library/Frameworks/EclipseSUMO.framework/Versions/Current/EclipseSUMO/share/sumo
   export PATH="$SUMO_HOME/bin:$PATH"
   ```

   `$SUMO_HOME/bin` is a link to the framework's `bin` directory, which is the layout the installer's own launcher apps use. Confirm with `sumo --version` and `netconvert --version`; both must print 1.28.0 so that they match the pinned Python packages.

3. Install only the two pure-Python packages at the version pinned in `requirements.txt`:

   ```bash
   cd safe-multi-embodied-agents
   /opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv
   source .venv/bin/activate
   python -m pip install traci==1.28.0 sumolib==1.28.0
   python check_environment.py
   ```

The lab finds `sumo` and `netconvert` in the virtual environment first, then on `PATH`, then in `$SUMO_HOME/bin`. On this route the check reports the `eclipse-sumo` and `sumo-data` packages as "not installed, external SUMO 1.28.0 found at ...", which is expected; every other line must be `ok`. Run metadata records those two packages as `null`.

## First run

```bash
python run_lab.py --scenario nominal --mode independent --out results/baseline
```

Open `results/baseline/replay.html` in Google Chrome, the browser the replay page is verified in. If Chrome is not installed, Safari renders the page as well. Collision warnings on the terminal are expected for this unsafe baseline. Apple's `/usr/bin/make` (GNU Make 3.81) runs every `make` target; a Homebrew `gmake` also works.

## If something fails

- `No matching distribution found for eclipse-sumo`: you are on an Intel Mac (unsupported) or on macOS 14 or older (use route B). `python -m pip debug --verbose` lists the wheel tags your interpreter accepts; route A needs `macosx_15_0_arm64` in that list.
- `sumo: not found in this environment, PATH, or SUMO_HOME/bin` from the environment check on route B: `SUMO_HOME` is not exported in this shell, or points at the framework root instead of its `share/sumo` directory.
- `reports '1.xx.x', expected 1.28.0`: another SUMO (Homebrew `dlr-ts/sumo` tap, an older installer) is earlier on your `PATH`. The Homebrew tap builds a different version and is not a match for this lab.
- A "cannot be opened because the developer cannot be verified" dialog: install from the downloaded `.pkg` through the normal Installer, which handles the notarized package. Do not disable Gatekeeper.
- Architecture or shared-library errors: confirm `arch` prints `arm64`, that the virtual environment was created from an arm64 `python3.12`, and that you did not run the terminal under Rosetta (`sysctl -n sysctl.proc_translated` prints `0`).

When asking for help, include the macOS version, `arch`, `python --version`, `sumo --version`, and the full output of `python check_environment.py`. References: [SUMO Python package notes](https://sumo.dlr.de/docs/Downloads.php#python_packages_virtual_environments) and [SUMO macOS installation](https://sumo.dlr.de/docs/Installing/index.html#macos).
