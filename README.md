# RHCSA Mock Exam Simulator

A command-line **RHCSA EX200 v10** (Red Hat Enterprise Linux 10) exam simulator.
It generates tasks, sets up each task's starting state, validates your real
system configuration with safe read-only checks, and tracks progress over time.

> **188 tasks · 25 categories · 8 domains**, aligned to EX200 v10 — including
> Flatpak, systemd timers, `tuned-adm`, and secure file transfer (no legacy
> module streams).
>
> **Active development** — useful for prep, but expect rough edges. Bug reports
> and contributions welcome.

---

## Quick Start

```bash
# On a RHEL 10 / Rocky 10 / Alma 10 VM, as root:
sudo -i
git clone https://github.com/justbest23/rhcsa-simulator.git
cd rhcsa-simulator
./install.sh          # interactive (use --yes for unattended)
rhcsa-simulator       # launch (must be root — validation reads real state)
```

At the menu, press **E** for a full Mock Exam or **Q** for a 5-task quick round.

The simulator **auto-creates the practice disks it needs** (loop devices, plus
any spare disk like `/dev/sda`) and **sets up each task's starting state** at
exam start — so a "kill the apache processes" task actually has processes
running, and an "extend the logical volume" task actually has a volume — then
tears it all down when the exam ends.

**Typical loop:** read a task → do it on the system in another terminal → return
and press Enter to validate → review per-check feedback and score.

---

## Requirements

| | Minimum |
|---|---|
| **OS** | RHEL 10, Rocky Linux 9/10, or AlmaLinux 9/10 |
| **Python** | 3.6+ (ships with the OS) |
| **Privileges** | root (validation reads users, services, mounts, SELinux, …) |
| **Dependencies** | none — Python standard library only |
| **Disk** | a few hundred MB under `/var/lib/rhcsa-simulator` for loop images |
| **Network** | not required (only for the optional DNF-history setup) |

**Use a throwaway VM you can snapshot/revert** — tasks change real system state
(users, partitions, services, firewall, SELinux). 2 vCPU, 2–4 GB RAM, 20 GB OS
disk is plenty. A spare disk is optional (loop devices cover storage practice; a
small spare like `/dev/sda` is auto-added if present). Keep SELinux
**Enforcing**; snapshot before each session. Cloud VMs (AWS/Azure/GCP) work well.

### Packages for task scenarios

A **minimal install doesn't ship `httpd`, `vsftpd`, `samba`, `tuned`** and a few
others that Domain 6/7 tasks use to build a realistic scenario. If a package is
missing, the task's fault-injection silently no-ops and the scenario looks empty
when you go to work on it. Every launch runs a read-only `rpm -q` preflight and
warns about what's missing — **nothing is installed automatically**.

| Package | Used by |
|---|---|
| `httpd` | Apache SELinux context/boolean, firewall, service troubleshooting |
| `vsftpd` | FTP service tasks |
| `nfs-utils` | NFS server/client and network storage tasks |
| `samba` | Samba/SMB file sharing tasks |
| `chrony` | time synchronization tasks |
| `firewalld` | firewall management/troubleshooting tasks |
| `bind-utils` | DNS lookup tooling for networking tasks |
| `tuned` | tuning profile (`tuned-adm`) tasks |

```bash
dnf install -y httpd vsftpd nfs-utils samba chrony firewalld bind-utils tuned
```

**Baseline services** tasks start/stop/enable (install the package, then leave
the service as a fresh install sets it): `httpd`, `vsftpd`, `nfs-server`, `smb`,
`chronyd`, `firewalld`, `sshd`, `crond`, `rsyslog`.

On **RHEL 10**, `firewalld` and `chrony` are enabled by default; the rest above
are not — install them before a session that may draw a Domain 6/7 or NFS task.

---

## Installation

```bash
./install.sh                 # interactive
./install.sh --yes           # unattended (overwrite, no prompts)
./install.sh --no-populate   # skip the optional DNF-history setup
```

The installer checks Python/OS, copies files to `/opt/rhcsa-simulator`, creates
the `rhcsa-simulator` command in `/usr/local/bin`, and optionally builds some DNF
transaction history for the package-history tasks. It auto-detects a
non-interactive shell and runs unattended, so it won't stall in automation.

Run without installing: `sudo python3 rhcsa_simulator.py`.

---

## Usage

```bash
sudo rhcsa-simulator    # interactive menu
```

| Key | Mode | What it does |
|---|---|---|
| `Q` | **Quick Practice** | 5 random tasks, fast feedback |
| `E` | **Mock Exam** | Full timed exam (20–25 tasks) with setup + reboot-persistence simulation |
| `1` | **Learn Mode** | Study by domain — concepts, commands, tips |
| `2` | **Practice Mode** | One category at a time, with retry & progressive hints |
| `3` | **Adaptive Mode** | SM-2 spaced repetition — focuses weak/overdue areas |
| `4` | **Dashboard** | Stats, history, weak areas |
| `5` | **Export Report** | Write a progress report to `data/` |
| `6` | **Result History** | Drill into past exams (press `d` on a task to dispute a check) |
| `S` | **Setup** | Practice disks, resets, remote NFS server, lab cleanup, DNF-history |
| `0` | Exit | |

### Command-line shortcuts

```bash
rhcsa-simulator --quick [lvm]        # 5 random (or category) tasks
rhcsa-simulator --exam               # jump straight into a mock exam
rhcsa-simulator --practice lvm       # practice a specific category
rhcsa-simulator --learn              # study mode
rhcsa-simulator --adaptive           # SM-2 weak-area practice
rhcsa-simulator --list-categories    # categories/domains (no root needed)
rhcsa-simulator --export-code        # print a progress backup code (no root)
rhcsa-simulator --import-code CODE   # restore progress (use - for stdin)
```

---

## Progress snapshots (backup & restore, no login)

Your task history and adaptive (SM-2) state live in a local SQLite DB. Export a
**progress code** — a self-contained, copy-pasteable string — and import it on
any box. No account, no server.

**In the app:** menu → **7. Progress Snapshot** — Export (also saved to
`data/progress_code.txt`), Import (preview, then **Replace** or **Merge**), or
Prune.

```bash
rhcsa-simulator --export-code > my-progress.code            # back up
rhcsa-simulator --import-code "$(cat my-progress.code)"     # restore (default: replace)
cat my-progress.code | rhcsa-simulator --import-code - --import-mode merge
```

The code is uppercase-alphanumeric with a checksum, so a mistyped or truncated
code is rejected rather than importing garbage. Its length grows with your
history (a few KB at most).

**Why it matters during active development.** The code is **version-portable** —
it survives *upgrading the simulator itself*, not just OS reinstalls. It encodes
only your history and per-category SM-2 state (never regenerable task text), is
format-versioned (`RH1` / `v:1`) and checksummed, and imports schema-tolerantly,
so a code from an older build loads cleanly into a newer one. The raw SQLite DB
under `data/` is **not** safe to copy across versions (its schema can change) —
the code is the stable interchange format that insulates your progress. So
before anything that wipes or migrates that DB — `git pull` to a new schema,
`./install.sh`, a Full System Reset, a fresh VM, or deleting `data/` — export a
code first, then import it afterward.

> **Caveat:** SM-2 targeting is keyed by **category name**. If a version renames
> or removes a category, that category's history still imports but its
> spaced-repetition schedule won't re-attach. Task-level history is unaffected.

---

## Practice disks & Setup menu

Exams provision disks automatically. To manage them yourself, use **Setup →
Practice Disks**: create loop devices (three 500 MB virtual disks), point at a
real spare disk, or clean up/reset. Every whole-disk task in an exam gets a
**distinct** device from the pool, so an LVM task and a partitioning task never
collide. Loop images live in `/var/lib/rhcsa-simulator/loops/`.

**Setup** also offers:

- **System Reset** — remove practice artifacts (LVM, swap files, practice repos,
  cron/at jobs, scripts) without touching SSH/network/users.
- **Full System Reset** — strip the box back to a basic RHEL install: all
  third-party DNF repos, Flatpak apps/remotes, lab files, practice users/groups,
  practice disks/swap, scheduled jobs, autofs maps, tuned changes, and remote NFS
  exports — unmounting every non-system mount first. **Preserves** the simulator,
  your GitHub/SSH connectivity (`~/.config/gh`, `~/.ssh`, git config),
  networking, firewall, SELinux, the OS, and all real accounts. Previews
  everything and requires typing `RESET`.
- **Configure remote NFS server** — SSH into a RHEL box you control and provision
  real, seeded NFS exports for the network-storage tasks (refreshed each exam,
  torn down after).
- **Clean lab leftover files** and **Populate Practice Environment** (DNF
  history).

> Practice and Adaptive modes reset the box at session start and set up/tear down
> each task's state per iteration, the same way the Mock Exam does. Adaptive mode
> also lets you choose how many tasks to run.

---

## Task domains & categories

8 EX200 v10 domains, 25 categories:

1. **Software Management** — packages, repos, flatpak
2. **System Setup & Boot** — boot targets, boot recovery, journald
3. **Users, Groups & Permissions** — users/groups, permissions/ACLs, essential tools
4. **Storage & Filesystems** — partitioning, LVM, filesystems, swap, network storage
5. **Network & DNS** — networking, SSH
6. **Systemd, Services & Processes** — services, timers, processes, time services, troubleshooting
7. **Security** — SELinux, firewall
8. **Automation & Scripting** — scheduling (cron/at/timers), shell scripting

Run `rhcsa-simulator --list-categories` for the live list and per-category counts.

---

## How it works

- **Read-only validation.** Work is graded with whitelisted, timeout-protected,
  read-only commands (`id`, `lsblk`, `systemctl is-active`, `getenforce`, …).
  Only the exam's setup/teardown phase changes state, and it reverses what it
  created.
- **Scoring.** Each task has multiple checks with partial credit; default pass
  threshold is 70%. A full exam is 20–25 tasks over a 3-hour timer
  (configurable), followed by a reboot-persistence simulation for tasks that must
  survive a reboot.
- **Progress.** Results and SM-2 state are stored in a local SQLite DB under
  `/opt/rhcsa-simulator/data/` (per-category easiness factor, 1→6→interval×EF).

---

## Disputing a validator result (AI checker disputes)

Think a check graded you wrong? Dispute it and an AI reviewer investigates — and
fixes the checker if you're right.

**File one:** in **Result History** (or after an exam), open a task's detail and
press **`d`**. The simulator captures read-only evidence of the relevant live
system state (category-specific diagnostics like `getfacl` / `lsblk -f`, plus any
command you add) and your written argument, saves a Markdown report under
`data/disputes/`, and opens a labelled GitHub issue (`checker-dispute`) with a
**Checker source** line pointing at the exact task file, class, and `validate()`
line. If the `gh` CLI isn't set up on the box, it prints a pre-filled GitHub "new
issue" URL instead — no token needed locally.

**What happens next:** the `.github/workflows/checker-dispute.yml` Action fires on
the label and runs
[`anthropics/claude-code-action`](https://github.com/anthropics/claude-code-action).
The reviewer opens **only** the named validator, decides strictly from your
evidence whether the checker is genuinely wrong (bad path/grep, inverted
condition, off-by-one, a bad RHEL 10 assumption) or the task simply wasn't done,
posts a **verdict comment**, and — **only if the checker is wrong** — makes the
minimal fix, runs `pytest`, and opens a **fix PR** that closes the issue.

**Enable it on your fork:** under Settings → Secrets and variables → Actions, add
**`CLAUDE_CODE_OAUTH_TOKEN`** (from `claude setup-token`, uses your Claude
subscription) or **`ANTHROPIC_API_KEY`**. The workflow is already scoped
(`id-token: write`) and reads either. Re-run a dispute by removing and re-adding
the `checker-dispute` label (issue-triggered workflows run from the default
branch).

---

## Architecture

```
rhcsa-simulator/
├── rhcsa_simulator.py   # entry point / CLI
├── config/              # settings, exam objectives
├── core/                # exam, practice, learn, adaptive, menu, results_db, reboot
│                        #   dispute, full_reset, nfs_server, lab_cleanup, task_env
├── tasks/               # task definitions by category (+ fault injection/teardown)
├── validators/          # safe read-only validation framework
├── device/              # loop-device / practice-disk management
├── utils/               # helpers, formatting, logging, device pool/allocator
├── .github/workflows/   # checker-dispute.yml — AI reviews disputed validators
└── data/                # SQLite progress DB (+ disputes/ reports)
```

## Extending — adding a task

1. Open the category file (e.g. `tasks/users_groups.py`).
2. Subclass `BaseTask`, decorate with `@TaskRegistry.register("category")`.
3. Implement `generate()` (build the prompt) and `validate()` (return a
   `ValidationResult`).
4. If the task needs a whole disk, set `disk_slots = 1`. If it needs a starting
   state (a process to kill, an LV to extend), add `has_fault_injection = True`
   with `inject_fault()` / `restore_fault()`.

## AI-powered feedback (optional)

Set `ANTHROPIC_API_KEY` to enable line-by-line command analysis. See
[AI_SETUP.md](AI_SETUP.md).

## Troubleshooting

- **"must be run as root"** — launch with `sudo`.
- **Storage tasks fail in a container** — loop devices/SELinux/systemd may be
  limited; use a real RHEL/Rocky/Alma VM.
- **Messy state after a crash** — run **Setup → System Reset** (also restores any
  practice "faults" still active).
- **Want a truly clean box** — run **Setup → Full System Reset** (unmounts every
  non-system mount first, clearing stale mounts/repos/flatpaks/users).
- **Reinstall from scratch** — re-run `./install.sh --yes`.

## License

See [LICENSE](LICENSE).
