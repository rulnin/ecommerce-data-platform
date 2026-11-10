# Environment evidence — 2026-11-10

Commands executed in `/home/fakhrul/dep/ecommerce-data-platform`:

| Check | Actual result |
|---|---|
| `cat /etc/os-release` | Ubuntu 26.04.1 LTS |
| `uname -rm` | 6.18.33.2-microsoft-standard-WSL2 x86_64 |
| `free -h` | 11 GiB total, 9.8 GiB available, 3 GiB swap |
| `df -h .` | 1007 GiB filesystem, 952 GiB available |
| `python3 --version` | Python 3.14.4 |
| `python3.12 --version` | command not found |
| `python3 -m pip --version` | No module named pip |
| `git --version` | git version 2.53.0 |
| `git status --short --branch` | fatal: not a git repository |
| `docker --version`, `docker compose version`, `docker info` | command not found |
| `python3 -m venv .venv` | failed: ensurepip unavailable; matching venv package required |
| `make profile` | make: command not found |

The repository metadata directory is empty and mounted read-only. No repository
initialization, package installation, host configuration, or database startup was
performed. Docker Desktop state on Windows cannot be inferred from a missing WSL
command. P1.1 remains blocked until a daemon is reachable; installed-package and
container compatibility remain unverified.

## P1.1 recheck — 2026-11-10

The next unchecked task was rechecked without installing software or changing host
configuration. Current observations:

| Command/check | Result |
|---|---|
| `cat /etc/os-release` | Ubuntu 26.04.1 LTS |
| `uname -rm` | 6.18.33.2-microsoft-standard-WSL2 x86_64 |
| `free -h` | 11 GiB total RAM, 9.7 GiB available, 3.0 GiB swap |
| `df -h .` | 952 GiB available on the Linux filesystem |
| `python3 --version` | Python 3.14.4; executable `/usr/bin/python3` |
| `python3.12 --version` | executable not found |
| `python3 -m pip --version` | exit 1: No module named pip |
| Python module discovery | venv present; ensurepip absent |
| `git --version` | exit 0: git version 2.53.0 |
| `docker --version` | executable not found |
| `docker compose version` | executable not found |
| `docker info` | executable not found; daemon reachability not verified |
| `/var/run/docker.sock` | absent |
| `/mnt/wsl/docker-desktop` | absent |
| `/mnt/wsl/docker-desktop/cli-tools/usr/bin/docker` | absent |

Python subprocess checks used a 15-second timeout per command. Missing executables
were reported explicitly; successful execution of the diagnostic wrapper does not
mean its individual checks passed. No containers or application tests were run.

**P1.1 status: BLOCKED.** WSL2 and the observed Linux environment are confirmed,
but Docker/Compose and a reachable daemon are required to complete this task.
The expected Ubuntu/Python versions differ from the observed versions; project
dependency compatibility remains unverified. SQL Server compatibility is deferred
to P3.4, as required by the architecture.

Next action on the Windows host: check whether Docker Desktop is installed and
running and, if so, enable WSL integration for this distribution. Its Windows state
is inaccessible from this execution environment, so absence of a WSL command does
not establish that Desktop is absent. Once integration is available, run these in
the project WSL terminal:

```bash
docker --version
docker compose version
docker info
```

If Desktop is intentionally not used, configure Docker Engine as the chosen
alternative before retrying these checks. Do not install a second engine without
first establishing the host's existing Docker setup. No later checklist task was
attempted during this recheck.

## P1.1 subsequent recheck — Docker installed, access blocked

On 2026-11-10, Docker availability changed:

| Check | Actual result |
|---|---|
| `docker --version` | Docker version 29.9.3, build 5457199; exit 0 |
| `docker compose version` | Docker Compose version v5.7.0; exit 0 |
| `docker info` | exit 1: permission denied while trying to connect to the docker API at unix:///var/run/docker.sock |
| `docker info` outside the sandbox | same permission-denied error; exit 1 |
| Docker executable | /usr/bin/docker |
| `/var/run/docker.sock` | present; socket mode srw-rw----, owner nobody, group nogroup |
| `/mnt/wsl/docker-desktop` | absent; Windows Desktop state still unknown |
| OS/kernel | Ubuntu 26.04.1; 6.18.33.2-microsoft-standard-WSL2 x86_64 |
| Available resources | 11 GiB RAM, 9.6 GiB available; 952 GiB free disk |
| Python/Git | Python 3.14.4; Git 2.53.0 |
| `python3 -m pip --version` | exit 1: No module named pip |
| `python3.12 --version` | command not found |

A formatted Docker info probe also reported permission denied and returned empty
server fields. These fields are not valid daemon capability evidence. The plain
`docker info` retry established the failing exit status explicitly.

**P1.1 remains BLOCKED:** client and Compose versions are verified, but server
reachability and compatibility cannot be established. No host permissions,
packages, containers, or data were changed. Application tests are not relevant to
these read-only environment checks.

Next action: have the Docker host/integration administrator restore access to the
intended socket for this WSL execution environment, then retry `docker info` here.
The observed nobody/nogroup ownership does not establish that adding the user to a
docker group would fix access. Do not make the socket world-writable or install a
second engine as a workaround.

## P1.1 verified — sandbox boundary diagnosed

On 2026-11-10, a fresh outside-sandbox check succeeded without sudo:

| Check | Actual result |
|---|---|
| Host identity | fakhrul, uid 1000; supplementary docker group 986 |
| Host socket | root:docker (0:986), mode 660 |
| `docker --version` | Docker 29.9.3, build 5457199 |
| `docker compose version` | v5.7.0 |
| `timeout 20 docker info` outside sandbox | exit 0; server 29.9.3, Linux x86_64 |
| Server capabilities observed | 16 CPUs, 11.02 GiB RAM, overlayfs storage, cgroup v2 |
| Sandbox Docker check | exit 1, socket permission denied |
| Sandbox identity mapping | uid_map and gid_map each contain `1000 0 1`; host supplementary groups appear as 65534 |
| Sandbox socket view | nobody:nogroup (65534:65534), mode 660 |
| WSL OS/kernel | Ubuntu 26.04.1; 6.18.33.2-microsoft-standard-WSL2 x86_64 |
| Available resources | 9.8 GiB available RAM, 952 GiB free disk |
| Python/Git | Python 3.14.4, Git 2.53.0 |

**P1.1 PASS.** The current denial is specific to the AI sandbox boundary. Docker
works through the approved outside-sandbox execution path. Earlier blocked entries
are historical observations, superseded by this verification. No installation,
socket permissions, user groups, or daemon configuration were changed.

Use the outside-sandbox execution path for subsequent authorized Docker checks
when this sandbox denies access. Do not repair the host installation to compensate
for sandbox identity mapping. Python dependency compatibility/venv work belongs to
P1.4; database and application container compatibility remains to be tested in its
respective tasks. No application tests or containers were run for P1.1.

## P1.4a verification — Python prerequisites missing

On 2026-11-10, Python prerequisite checks were repeated both in the sandbox and
through the approved host execution path. Both reported Python 3.14.4, no pip
module, an available venv module, and an absent ensurepip module. Git reports
2.53.0; `python3.12` is not on PATH.

Host `dpkg-query` confirms python3-venv and python3.14-venv are not installed;
python3-pip has no installed package. `apt-cache policy` reported these candidates
from the configured Ubuntu repositories (metadata only; no installation executed):

| Package | Candidate |
|---|---|
| python3.14-venv | 3.14.4-1ubuntu0.2 |
| python3-venv | 3.14.3-0ubuntu2 |
| python3-pip | 25.1.1+dfsg-1ubuntu2 |
| python3.12 / python3.12-venv | No candidate reported |

**P1.4a BLOCKED.** These are missing host prerequisites, not merely sandbox
visibility restrictions. The smallest proposed fix for the current interpreter is
`sudo apt install python3.14-venv python3-pip`, followed by
`python3 -m pip --version` and `python3 -c 'import venv, ensurepip'`. This command
has not been executed. No external package repository was added.

Python 3.14 compatibility with the planned ingestion and dbt dependencies remains
unverified; it is not yet the chosen project interpreter. Existing profiler success
only establishes compatibility for that standard-library script. No project venv
was created or modified, and no project dependencies were installed. Creating the
project venv remains P1.4b after prerequisite verification succeeds.
