# Third-party notices

No third-party source code is vendored in this repository. Dependencies are installed from PyPI at the versions pinned in `requirements.txt`, or built into the course container image from the same file. No simulator binaries, container images, or model weights are committed here.

| Component | Source | Pin | License |
| --- | --- | --- | --- |
| Eclipse SUMO (`eclipse-sumo`, `sumo-data`) | <https://sumo.dlr.de/>, PyPI | 1.28.0 | EPL-2.0, with GPL-2.0-or-later available as a secondary license |
| TraCI (`traci`) | PyPI, part of the SUMO project | 1.28.0 | EPL-2.0 or GPL-2.0-or-later |
| sumolib (`sumolib`) | PyPI, part of the SUMO project | 1.28.0 | EPL-2.0 or GPL-2.0-or-later |
| Official SUMO macOS installer (`sumo-1.28.0.pkg`), used only on the installer route in `setup/MACOS.md` | <https://sumo.dlr.de/releases/1.28.0/> | 1.28.0 | Same as SUMO |
| Python | python.org, Homebrew, or Ubuntu packages | 3.12 | PSF License |
| Ubuntu base image (container route) | `docker.io/library/ubuntu:24.04` | 24.04 | Upstream package licenses |

The intersection network, scenarios, agents, protocol, replay page, and tooling in this repository are course material under [LICENSE](LICENSE). Review each upstream license before redistributing a dependency; the course code grants no rights beyond those supplied by each copyright holder.
