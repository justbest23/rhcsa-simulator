# RHCSA Simulator — Patch Notes

Generated 2026-06-27 after a verification pass (test suite + driving every CLI mode).
Hand this file to another Claude instance to action. Repo root: `/root/rhcsa-simulator`
(re-cloned from https://github.com/justbest23/rhcsa-simulator on each `reset.sh` run —
**so any fix here must be committed and pushed to GitHub `master`, or it is lost on the next reset**).

## TL;DR

The simulator runs fine in normal use — `--quick`, `--exam`, `--practice`, and `--learn`
(valid domains) all complete without crashing. There is **1 real crash bug**, **1 minor
CLI bug**, **3 failing tests (all stale/incorrect, not product bugs)**, and a pervasive
**"8 vs 9 domains / 194 vs 198 tasks" documentation drift**. Root cause of most items is
that the project is documented as having a 9th "Containers" domain that was never
implemented.

Ground-truth runtime values (from `--list-categories`): **194 tasks, 25 categories, 8 domains.**

---

## 1. BUG (crash) — Learn mode `KeyError: 9` on domain selection

**File:** `core/learn.py`
**Severity:** Medium (uncaught traceback; via `--learn` CLI path there is no try/except, so
the program dies with a stack trace rather than returning to a menu).

`EXAM_OBJECTIVES` (in `config/exam_objectives.py`) defines only keys **1–8**, but the domain
menu prompt and bounds check allow **9**:

- Line ~91: `choice = input("\nSelect domain (1-9 or Q): ")`  ← says 1-9
- Line ~98: `if 1 <= domain_num <= 9:` then `self._show_domain_topics(domain_num, ...)`
- Line ~109: `domain = EXAM_OBJECTIVES[domain_num]`  ← `EXAM_OBJECTIVES[9]` → `KeyError: 9`

**Repro:** `printf '9\n' | python3 rhcsa_simulator.py --learn`  → `KeyError: 9`, exit 1.

**Fix:** Make the bound and the prompt data-driven instead of hard-coded `9`:
- Change the prompt to `f"\nSelect domain (1-{max(EXAM_OBJECTIVES)} or Q): "`.
- Change the bound to `if domain_num in EXAM_OBJECTIVES:` (or `1 <= domain_num <= max(EXAM_OBJECTIVES)`).
This also auto-corrects itself if/when a 9th domain is added (see item 4).

---

## 2. BUG (minor) — `--practice <category>` ignores its argument

**Files:** `rhcsa_simulator.py` (~lines 230-243), `core/practice.py` (`PracticeSession.start`, ~line 38)
**Severity:** Low (UX). The CLI accepts a category but still prompts for one.

`main()` does `session.category = args.practice; session.difficulty = 'exam'; session.start()`,
but `start()` immediately overwrites both:
```python
self.category = self._select_category()      # ignores preset category
self.difficulty = self._select_difficulty()  # ignores preset difficulty
```
**Repro:** `printf 'q\n' | python3 rhcsa_simulator.py --practice lvm` → shows the
"PRACTICE MODE - Select Category" menu instead of going straight to LVM.

**Fix:** In `start()`, only prompt when not already set, e.g.:
```python
if not self.category:
    self.category = self._select_category()
    if not self.category:
        return
if not self.difficulty:
    self.difficulty = self._select_difficulty()
```
(Validate the preset category against `TaskRegistry.get_all_categories()` — `main()` already does this.)

---

## 3. TESTS — 3 failures, all stale/incorrect (production code is correct)

Run: `python3 -m pytest -q` → **3 failed, 143 passed**. None indicate a product defect.

### 3a & 3b. `tests/e2e/test_practice_mode.py`
`TestPracticeTask::test_passed_task_saves_to_db` and `::test_failed_task_offers_retry`.

`PracticeSession.start()` gained two interactive steps the tests don't account for:
`_select_reboot_filter()` and a **task-preview loop** (both call `input()`). The tests only
provide 2–4 `input()` side-effects and don't patch `_select_reboot_filter`, so `input()`
raises `StopIteration` *before* the task is validated/saved → 0/1 saves instead of 1/2.

**Verified the production path is correct:** driving the real `PracticeSession.start()` with
`_select_reboot_filter` patched and enough inputs yields exactly 1 save (pass case) and 2
saves (fail→retry→pass). So fix the **tests**, not the code:
- Add `patch.object(session, "_select_reboot_filter", return_value=False)`.
- Prepend a preview-loop answer (`"s"`) and add the extra task `input()` values.
  - passed case inputs: `["s", "", ""]`, `confirm_action` side_effect `[True]`.
  - fail→retry→pass inputs: `["s", "", "r", "", ""]`, `confirm_action` side_effect `[True]`.

### 3c. `tests/unit/test_content.py::test_all_9_domains_have_categories`
Asserts every domain in `range(1, 10)` (i.e. 1–9) has ≥1 category, but only 8 domains
exist → "Domain 9 has no categories".

**Fix options:** either (a) change the test to iterate the actual domain keys
(`range(1, len(EXAM_OBJECTIVES)+1)` or the registry's known domains), or (b) if a 9th
"Containers" domain is intended, implement it (item 4) and keep the test. Pick based on the
decision in item 4.

---

## 4. DOC/CONTENT DRIFT — "9 domains / 27 categories / 198 tasks" claimed, 8 / 25 / 194 real

The 9th domain is **"Manage Containers"** — a real RHCSA v9/v10 exam objective that is
**not implemented** (no `containers` task category; `podman` appears only in the
safe-command whitelist). This single gap is the root cause of items 1, 3a-c, and the
wrong counts in docs.

Claimed-vs-actual mismatches to reconcile:
- `rhcsa_simulator.py` module docstring: "198 tasks across 27 categories, 9 EX200 v10 domains".
- `CLAUDE.md`: "198 tasks, 27 categories, 9 domains".
- `README.md`: check for the same numbers.
- Actual: **194 tasks, 25 categories, 8 domains** (`config/settings.py` `EXAM_DOMAINS` has 1–8;
  `TASK_CATEGORIES` lists 25; `config/exam_objectives.py` `EXAM_OBJECTIVES` has 1–8).

**Decision needed (pick one):**
- **(A) Implement the 9th domain (Containers).** Add an `EXAM_DOMAINS[9] = "Containers"`,
  add `EXAM_OBJECTIVES[9]`, create a `containers` task category + tasks, map it in
  `CATEGORY_TO_DOMAIN`. Then items 1 and 3c resolve naturally and the docs become true.
  This is the most faithful to the real exam.
- **(B) Drop the 9th domain everywhere.** Fix all docs/docstrings to say 8 domains / 25
  categories / 194 tasks, change `test_content.py` to 8 domains, and fix item 1's bounds.

Either way, also fix item 1 (make the learn-mode bound data-driven so it can't `KeyError`).

---

## 5. DONE (in this PR)

- `install.sh`: added `-y/--yes/--force` and `--populate/--no-populate` flags plus
  **non-TTY autodetection**, so it no longer stalls on `read` prompts when run unattended.
  This is the code change shipped in this PR.

Not committed (intentional): `reset.sh` is the maintainer's **local-only** convenience
wrapper (wipes + re-clones + runs `./install.sh --yes`). It lives outside the repo and is
deliberately not tracked in git.

---

## Suggested order of work
1. Decide item 4 (A or B) — it drives 1 and 3c.
2. Fix item 1 (learn-mode bound) — quick, prevents a crash.
3. Fix item 2 (`--practice` arg) — quick UX win.
4. Update the tests in item 3 to match current behavior.
5. Commit + push items in section 5 so `reset.sh` is durable.
6. `python3 -m pytest -q` should be all-green afterward.

---
---

# PART 2 — Findings from taking the exam hands-on (2026-06-27)

Method: established a clean baseline (only `/dev/sda` bare + the nvme OS disk), created 3
loop devices via the Setup script, then performed real exam tasks as a candidate (run the
commands, then call the task's own `validate()`), with special attention to disk
mount/unmount and the user-lifecycle (apache) tasks. Severity tags: 🔴 high, 🟡 medium, 🟢 low.

## P2-0 Unifying fix: provision the exam VM at generation time, from a managed device pool
Almost every P2 finding is one missing capability: **an exam-generation step that prepares
the VM for exactly the tasks that were drawn, then tears it down afterward.** Build this once
and most items below close:
1. **Device pool** (P2-1, P2-7): ensure ≥3 practice disks (auto-create loop devices; add any
   spare non-system disk like `/dev/sda`). Hand each disk-consuming task a *distinct* device
   via an allocator instead of everyone grabbing `get_practice_device()[0]`.
2. **Per-task setup** (P2-3, P2-4, P2-5): for every drawn task, create its precondition on an
   allocated device — start the process to kill, create the LV to remove/extend/reduce, mount
   the FS to unmount — using distinct VG names so fault tasks don't collide.
3. **Teardown** (P2-6, P2-8, P2-9): reverse all of the above, including `userdel` for users
   that setup created, and sweep orphaned loop/dm artifacts.
4. **Respect device limits** (P2-2): size XFS targets > 320 MB.

## P2-1 🔴 Disk-allocation conflict: different tasks fight over the same disk  (USER-REPORTED)
**Symptom (user):** "questions use /dev/sda to create a vg/lv but then later tasks ask me to
partition /dev/sda — which you can't, because it's already an LVM PV."

**Root cause (confirmed):**
- `tasks/partitioning.py::_random_device()` → `utils.helpers.get_practice_device()`.
- `tasks/lvm.py` (full workflow, pv/vg create) and `tasks/filesystems.py` also call
  `get_practice_device()`.
- `get_practice_device()` returns a *single* device — `loop_devices[0]` in loop mode, or
  `cfg['devices'][0]` (e.g. `/dev/sda`) in real-disk mode. So an LVM/VG task and a
  partitioning task in the same exam both resolve to the **same disk**.
- `exclusive_resource = 'physical_disk'` is declared on only 6 task classes (4 in
  filesystems, `swap_partition_001`, and `lvm_full_workflow_001`). It is **NOT** on any
  partitioning task and **NOT** on the other LVM tasks (`pv_create`, `vg_create`,
  `lv_create`, `extend`, `vg_extend`, `lv_remove`, `lv_reduce`, `verify`). The registry
  mutex (`tasks/registry.py` ~225-278) therefore cannot stop the collision.
- The mutex is also too coarse where it *does* apply: it blocks any second `physical_disk`
  task even when multiple spare disks are free, keyed on the string `'physical_disk'` rather
  than on actual device identity.

**Recommended fix (matches the user's suggestion — see P2-7):**
1. Guarantee a device pool of **≥3** disks: auto-create loop devices at startup when fewer
   than 3 practice devices exist; additionally include a spare **non-system** `/dev/sda`
   (or any non-system HDD) in the pool when present.
2. Replace the "everyone grabs `get_practice_device()[0]`" pattern with a real **allocator**
   that hands each disk-consuming task a *distinct* device (reserve/round-robin) at exam-
   generation time, and stamps the chosen device into the task so description + validator +
   any fault injection all agree.
3. Have the exam generator stop scheduling additional disk tasks once the pool is exhausted,
   instead of letting two tasks share one disk.

## P2-2 🔴 `mkfs.xfs` minimum-size makes some tasks impossible on RHEL 10
RHEL 10 `mkfs.xfs` refuses to format anything ≤ ~300 MB ("Filesystem must be larger than
300MB."). But `lvm_full_workflow_001.generate()` picks `size ∈ [200, 300, 400]` with
`fstype='xfs'`. **200 MB and 300 MB + XFS → `mkfs.xfs` fails → the task cannot be completed
as written** (confirmed live: 200 MB XFS failed; 450 MB XFS succeeded and validated 20/20).
- Applies anywhere an XFS filesystem is made on a ≤300 MB LV/partition (also
  `fs_extend_001` if run with `fstype='xfs'`; its default is ext4 so it's usually safe).
**Fix:** for XFS targets enforce a size > 320 MB (e.g. min 512 MB), or fall back to ext4 for
small sizes. The 500 MB loop disks are fine — it's the LV/partition *sizing* that's wrong.

## P2-3 🟡 Tasks are trivially satisfiable because the precondition is never set up
**User direction:** a trivial *validator* is fine — the fix is that **the VM must be set up
during exam generation** so the precondition exists and the task is no longer trivial. Do
NOT change these validators; add environment provisioning instead.

Confirmed from the clean baseline, candidate took **no action**, full marks:
- `proc_kill_001` (kill httpd/nginx) → **8/8 PASS** (nothing starts the target process).
- `lvm_lv_remove_001` (remove `vg_test24/lv_remove2`) → **8/8 PASS** (LV never created).
- `fs_unmount_001` (unmount `/mnt/dataNN`) → **6/6 PASS** (mountpoint never mounted).

**Fix (provision at generation time, leave validators alone):** when one of these tasks is
selected for an exam, the generation step must set up the matching state on the VM:
- `proc_kill_*` → start the named process (e.g. an `httpd`/`nginx`/`sleep` instance) so there
  is something real to kill.
- `lvm_lv_remove_*` → actually create `vg_test24/lv_remove2` (on an allocated device) so the
  candidate must remove a real LV.
- `fs_unmount_*` → create+mount a filesystem at the target mountpoint so there is something
  to unmount.
This is the same mechanism as the existing `inject_fault()`/`restore_fault()` hooks — extend
it to every task whose precondition is currently assumed rather than created (ties into P2-4,
P2-5, and the unifying note below).

## P2-4 🟡 Impossible-from-clean tasks — depend on state nothing creates
`lvm_extend_001`, `lvm_lv_create_001`, `lvm_lv_reduce_001` assume `vg_practice/lv_practice`
already exist, but **no fault injection creates them** (`fault=False`). From a clean baseline
they can't be completed as written (confirmed: `lvm_extend_001` → 0/12, "LV not found").
They only work by luck if another task (e.g. `fs_extend_001`) injected `vg_practice` earlier
in the same session and it hasn't been restored yet — fragile coupling via
`get_practice_lv()`.
**Fix:** give each of these its own `inject_fault()` to build the prerequisite VG/LV (as
`fs_extend_001` does), or make the description self-contained.

## P2-5 🟡 Multiple fault tasks collide on the shared `vg_practice`/`loops[0]`
`fs_extend_001` and `lvm_vg_extend_001` both build `vg_practice` on `loops[0]` in their
`inject_fault()`. If both are picked for one exam, the second injection fails/clobbers, and
either one's `restore_fault()` tears down the `vg_practice` the other still needs.
**Fix:** give each fault task a distinct VG name and a distinct device from the allocator
(P2-1), and make restore idempotent/scoped.

## P2-6 🟡 apache pkill task leaves the user behind (also see item 0/earlier)
`tasks/processes.py::FindProcessByUserTask` (`proc_find_user_001`, the apache kill task):
`inject_fault()` does `useradd -r apache` + 3 `sleep` procs; `restore_fault()` runs
`pkill -u apache` but **never `userdel apache`** — confirmed the `apache` user (uid 984)
survives after restore. Exam mode does call inject/restore (`core/exam.py` 88-117), so this
leaks in real exams too.
**Fix:** in `restore_fault()`, `userdel -r` the user — but only if `inject_fault()` actually
created it (record that; `useradd -r` silently no-ops if `apache` already exists from httpd,
and you must not delete a pre-existing real account).

## P2-7 🟡 Device pool / auto-provisioning (user's requested design)
Per the user: *always have ≥3 devices; auto-create loop devices; also use `/dev/sda` if a
spare HDD exists.* This is the backbone of the P2-1 fix:
- On startup (or exam start), if `get_loop_devices()` < 3, auto-run
  `create_practice_devices()` to reach 3.
- Detect a spare non-system disk (e.g. `/dev/sda` here is bare 20 GB; nvme is the OS) via
  `list_all_block_devices()` filtering `is_system`, and add it to the pool.
- Feed that pool to the allocator in P2-1.
- Current state for reference: baseline is `/dev/sda` (bare, 20 GB) + `nvme0n1` (OS). Setup
  script created `/dev/loop0,1,2` (500 MB each, `loop2` reserved for swap/partition).

## P2-8 🟢 Loop setup not robust to a pre-existing orphaned loop
`create_practice_devices()` uses `losetup -f --show <img>` with a **10 s timeout**. With a
leftover orphaned loop (backing file deleted) on the system, `losetup` ran >10 s, the code
treated it as failure and skipped that disk **even though the loop actually attached** →
`practice_devices.conf` listed only 2 of 3 devices, and the 3rd became an orphan that the
config-driven cleanup would never remove. From a truly clean state it worked perfectly (3/3).
**Fix:** after a timeout, reconcile with `losetup -j <img>`; raise the timeout; and have
cleanup enumerate `losetup -a` for our `loop_dir` rather than trusting the saved config.

## P2-9 🟢 Stale teardown left orphaned dm devices last session
At the start of this pass, `lsblk` showed `vg_exam79-lv_data42` (on `/dev/sda`) and
`vg_practice-lv_practice` as **orphaned device-mapper maps** (absent from `vgs/pvs/lvs`;
loop backing file deleted). Neither System Reset nor the loop cleanup had removed them; I
cleared them manually (`dmsetup remove`, `losetup -d`). Make System Reset also sweep orphaned
dm maps / loops whose backing images are gone.

## P2-10 🟢 `lvm_full_workflow` persistence check is too loose
The `persistent_mount` check only greps the mount-point string in `/etc/fstab`. During the
failed 200 MB attempt my fstab line was `UUID= /mnt/lvmtest ...` (empty UUID, `mount -a`
errored) yet the check still passed. Consider validating the fstab entry actually resolves
(non-empty UUID/device, and `findmnt --verify` / `mount -a` clean).

## What worked well
- `lvm_full_workflow_001` at a valid XFS size (450 MB): full PV→VG→LV→mkfs→mount→fstab(UUID)
  validated **20/20**; mount and unmount lifecycle both validate correctly.
- The apache kill task's detection/validation logic is correct (12/12 after `pkill -u`); only
  the user cleanup is missing.
- `lvm_vg_extend_001` and `fs_extend_001` fault injection build real LVM state correctly in
  isolation.
- Exam engine itself (20 tasks + reboot simulation + scoring) runs without crashing.
