$ cat /home/user/rhcsa-simulator/CLAUDE.md

# RHCSA Exam Simulator

RHCSA EX200 v10 exam simulator for Red Hat Enterprise Linux. Generates tasks, validates system configuration, tracks progress.

## Running the Simulator

```bash
# Must run as root (uses sudo internally)
sudo python3 rhcsa_simulator.py

# Common flags
python3 rhcsa_simulator.py --quick          # 5 random tasks
python3 rhcsa_simulator.py --exam           # Full exam (15-20 tasks)
python3 rhcsa_simulator.py --practice       # Practice by category
python3 rhcsa_simulator.py --learn          # Study mode
```

## Running Tests

```bash
pytest                          # Run all tests
pytest tests/                   # Test suite
pytest test_boot_tasks.py       # Boot/reboot task tests
python3 -m pytest -v            # Verbose output
```

## Project Structure

- `rhcsa_simulator.py` — Main entry point
- `core/` — Engine: task manager, exam loop, SM-2 spaced repetition, ResultsDB
- `tasks/` — Task definitions (198 tasks, 27 categories, 9 domains)
- `validators/` — Safe read-only system validators for each task type
- `utils/` — AI feedback, progress reports, device detection
- `config/` — Settings and constants
- `data/` — SQLite progress DB, bookmarks
- `device/` — Loop device / practice disk setup

## Key Facts

- **Target OS**: RHEL 10 / Rocky Linux 9-10 / AlmaLinux 9-10
- **Requires root** — many validators run real system commands
- **No internet needed** — fully offline; optional Claude AI feedback via `ANTHROPIC_API_KEY`
- **Loop devices** — LVM tasks can use virtual disks (option 13 in menu) when no spare disk exists

## Testing on This VM

This container may lack real systemd, SELinux enforcement, and firewalld. Tests that validate actual system state will fail here. For realistic testing:

1. Use a RHEL/Rocky Linux 9+ VM
2. Run as root
3. Set up a loop device for LVM tasks: `python3 rhcsa_simulator.py` → option 13

## AI Feedback Setup

Set `ANTHROPIC_API_KEY` env var to enable line-by-line command analysis. See `AI_SETUP.md`.

## Branch

Active development: `claude/deploy-vm-rhel-exam-sk7q5b`
