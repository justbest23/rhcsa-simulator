# RHCSA Mock Exam Simulator

A realistic command-line **RHCSA EX200 v10** (Red Hat Enterprise Linux 10) exam
simulator. It generates exam tasks, sets up the practice environment for you,
validates your real system configuration with safe read-only checks, and tracks
your progress over time.

> **EX200 v10 aligned** — tasks cover the Red Hat EX200 v10 objectives. The bank
> currently ships **194 tasks across 25 categories in 8 domains**. Flatpak,
> systemd timers, tuning profiles (`tuned-adm`), and secure file transfer are
> included; legacy module streams are not.

> **Active development** — functional and useful for RHCSA prep, but you may hit
> rough edges. Bug reports and contributions welcome.

---

## Quick Start

```bash
# 1. On a RHEL 10 / Rocky 10 / Alma 10 VM, become root
sudo -i

# 2. Get the code
git clone https://github.com/justbest23/rhcsa-simulator.git
cd rhcsa-simulator

# 3. Install (interactive). For an unattended install use: ./install.sh --yes
./install.sh

# 4. Launch (must be root — validation inspects real system state)
rhcsa-simulator

# 5. At the menu, press  E  for a full Mock Exam, or  Q  for a 5-task quick round.
```

That's it. The simulator **auto-creates the practice disks it needs** (loop
devices, plus any spare disk such as `/dev/sda`) and **sets up each task's
starting state** when an exam begins — so a "kill the apache processes" task
actually has processes running, and an "extend the logical volume" task actually
has a volume to extend. When the exam ends, it tears all of that back down.

**Typical loop:** read a task → do it on the system in another terminal → come
back and press Enter to validate → review per-check feedback and score.

---

## Requirements

| | Minimum |
|---|---|
| **OS** | RHEL 10, Rocky Linux 9/10, or AlmaLinux 9/10 (EX200 v10 targets RHEL 10) |
| **Python** | 3.6+ (ships with the OS) |
| **Privileges** | root (validation reads users, services, mounts, SELinux, etc.) |
| **Dependencies** | none — Python standard library only |
| **Disk** | a few hundred MB free under `/var/lib/rhcsa-simulator` for loop-device images |
| **Network** | not required (optional, only for the DNF-history practice setup) |

### Recommended VM configuration

Practice on a **throwaway VM you can snapshot/revert**, never a machine you care
about — tasks change real system state (users, partitions, services, firewall,
SELinux).

- **vCPUs:** 2
- **RAM:** 2–4 GB
- **Primary disk:** 20 GB (OS)
- **A spare disk for storage practice:** optional. The simulator auto-creates
  500 MB loop devices, so you don't *need* one. If you add a small spare disk
  (e.g. a 1–2 GB `/dev/sda`), it is detected and added to the practice device
  pool automatically — handy for realistic `fdisk`/`parted` partitioning.
- **Install type:** minimal install is fine.
- **Snapshot first:** take a VM snapshot before a session so you can revert.
- **SELinux:** leave it **Enforcing** for realistic SELinux tasks.
- **Networking:** any NAT/bridged setup; only needed if you want the optional
  DNF transaction-history practice data.

> Cloud VMs (AWS/Azure/GCP) work well — loop devices mean you don't have to
> attach extra block storage to practice LVM/partitioning.

---

## Installation

### Install script

```bash
cd rhcsa-simulator
./install.sh            # interactive
./install.sh --yes      # unattended (overwrite existing install, no prompts)
./install.sh --no-populate   # skip the optional DNF-history setup
```

The installer:
- checks the Python version and OS,
- copies files to `/opt/rhcsa-simulator`,
- creates the `rhcsa-simulator` command at `/usr/local/bin/rhcsa-simulator`,
- sets permissions,
- offers to build some DNF transaction history for the package-history tasks.

`install.sh` auto-detects a non-interactive shell (piped/scripted) and runs
unattended, so it won't stall in automation.

### Run without installing

```bash
sudo python3 rhcsa_simulator.py
```

---

## Usage

Launch the interactive menu:

```bash
sudo rhcsa-simulator
```

Main menu options:

| Key | Mode | What it does |
|---|---|---|
| `Q` | **Quick Practice** | 5 random tasks, fast feedback |
| `E` | **Mock Exam** | Full timed exam (20–25 tasks) with environment setup + reboot-persistence simulation |
| `1` | **Learn Mode** | Study by domain — concepts, commands, tips |
| `2` | **Practice Mode** | One category at a time, with retry & progressive hints |
| `3` | **Adaptive Mode** | SM-2 spaced repetition — focuses your weak/overdue areas |
| `4` | **Dashboard** | Stats, history, weak areas |
| `5` | **Export Report** | Write a progress report (text) to `data/` |
| `6` | **Result History** | Drill into past exams task by task |
| `S` | **Setup** | Practice disks, system reset, DNF-history setup |
| `0` | Exit | |

### Command-line shortcuts

```bash
rhcsa-simulator --quick            # 5 random tasks
rhcsa-simulator --quick lvm        # 5 LVM tasks
rhcsa-simulator --exam             # jump straight into a mock exam
rhcsa-simulator --practice lvm     # practice a specific category
rhcsa-simulator --learn            # study mode
rhcsa-simulator --adaptive         # SM-2 weak-area practice
rhcsa-simulator --list-categories  # list categories/domains (no root needed)
rhcsa-simulator --version
```

---

## Practice disks (LVM / partitioning / swap / filesystems)

You normally don't have to do anything — exams provision disks automatically.
To manage them yourself, use **Setup → Practice Disks**:

- **Create loop devices** — three 500 MB virtual disks (no spare hardware needed).
- **Use a real disk** — point practice at a spare drive already in the VM.
- **Clean up / reset** — remove practice LVM structures and detach loop devices.

Under the hood, every whole-disk task in an exam is handed a **distinct** device
from the pool, so an LVM task and a partitioning task never collide on the same
disk. Loop-device images live in `/var/lib/rhcsa-simulator/loops/`.

**Setup also offers:** *System Reset* (remove practice artifacts — LVM, swap
files, practice repos, cron/at jobs, scripts — without touching SSH/network/users)
and *Populate Practice Environment* (build DNF transaction history).

---

## Task domains & categories

8 EX200 v10 domains, 25 categories:

1. **Software Management** — packages, repos, flatpak
2. **System Setup & Boot** — boot targets, boot recovery, journald
3. **Users, Groups & Permissions** — users/groups, permissions/ACLs, essential tools
4. **Storage & Filesystems** — partitioning, LVM, filesystems, swap, network storage
5. **Network & DNS** — networking, SSH
6. **Systemd, Services & Processes** — services, systemd timers, processes, time services, troubleshooting
7. **Security** — SELinux, firewall
8. **Automation & Scripting** — scheduling (cron/at/timers), shell scripting

Run `rhcsa-simulator --list-categories` for the live list and per-category task counts.

---

## How it works

**Read-only validation.** The simulator checks your work with whitelisted,
timeout-protected, read-only commands (`id`, `lsblk`, `systemctl is-active`,
`getenforce`, …). It does not modify your system *to grade* it — only the
exam's setup/teardown phase changes state, and it reverses what it created.

**Scoring.** Each task is worth points with multiple checks and partial credit.
Default pass threshold is 70%. A full exam is 20–25 tasks over a 3-hour timer
(configurable), followed by a reboot-persistence simulation for tasks that must
survive a reboot.

**Progress.** Results and spaced-repetition state are stored in a local SQLite
database under `/opt/rhcsa-simulator/data/` (`ResultsDB`). Adaptive mode uses an
SM-2 schedule (per-category easiness factor, 1→6→interval×EF progression).

---

## Architecture

```
rhcsa-simulator/
├── rhcsa_simulator.py   # entry point / CLI
├── config/              # settings, exam objectives
├── core/                # exam, practice, learn, adaptive, menu, results_db, reboot engine
├── tasks/               # task definitions by category (+ fault injection/teardown)
├── validators/          # safe read-only validation framework
├── device/              # loop-device / practice-disk management
├── utils/               # helpers, formatting, logging, device pool/allocator
└── data/                # SQLite progress DB
```

## Extending — adding a task

1. Open the category file (e.g. `tasks/users_groups.py`).
2. Subclass `BaseTask`, decorate with `@TaskRegistry.register("category")`.
3. Implement `generate()` (build the prompt) and `validate()` (return a
   `ValidationResult`).
4. If the task needs a whole disk, set `disk_slots = 1` so the allocator gives
   it a dedicated device. If it needs a starting state (a process to kill, an LV
   to extend), add `has_fault_injection = True` with `inject_fault()` /
   `restore_fault()`.

## AI-powered feedback (optional)

Set `ANTHROPIC_API_KEY` to enable line-by-line command analysis. See
[AI_SETUP.md](AI_SETUP.md).

## Troubleshooting

- **"must be run as root"** — launch with `sudo`; validation needs root.
- **Storage tasks fail in a container** — loop devices/SELinux/systemd may be
  limited; use a real RHEL/Rocky/Alma VM.
- **Left in a messy state after a crash** — run **Setup → System Reset**; it also
  restores any practice "faults" that were still active.
- **Reinstall from scratch** — re-run `./install.sh --yes`.

## License

See [LICENSE](LICENSE).
