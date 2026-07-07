"""
Boot-rescue lab: real root-password recovery on the linked lab machine.

The simulator sets a random root password on the second machine over SSH
(keeping its own key-based access), and the candidate must recover it at
that machine's console by interrupting boot — exactly like the real exam.

Both recovery methods are taught and accepted:

  * rd.break — the classic Red Hat method: break into the initramfs before
    switch_root, remount /sysroot rw, chroot, passwd, handle the SELinux
    relabel. On some builds rd.break lands in a password-gated maintenance
    shell instead of a free shell, in which case…
  * init=/bin/bash — always works: the kernel runs bash as PID 1, remount
    / rw, passwd, restorecon /etc/shadow, then reboot WITHOUT systemd
    (sync; echo b > /proc/sysrq-trigger  — or  /usr/sbin/reboot -f).

Validation runs over the retained SSH key: the root hash must differ from
the planted one, the machine must have rebooted into a working system, and
/etc/shadow must carry the right SELinux label (proof the relabel was
handled). Which method was used is detected best-effort from the journal
(rd.break shows in a recovered boot's kernel cmdline; init=/bin/bash leaves
no journal for that boot, so it is reported as inferred) — informational
only, never pass/fail.

Safety: the original root hash is stored locally (root-only, 0600) so
"give up" can reveal the planted password and restore the machine exactly
as it was. The scenario refuses to start unless key-based SSH works, so
the simulator can never lock itself (or the user) out of a bootable box.
"""

import os
import json
import secrets
import string
import time

from core import lab_machine

STATE_PATH = os.path.join(lab_machine.STATE_DIR, 'boot_rescue.json')

# Typable at any console layout: no ambiguous glyphs, no shell metacharacters.
_ALPHABET = ''.join(c for c in string.ascii_lowercase + string.digits
                    if c not in 'l1o0')

_INFO_SCRIPT = r"""
echo "BOOT_ID=$(cat /proc/sys/kernel/random/boot_id 2>/dev/null)"
echo "ROOT_HASH=$(awk -F: '$1=="root"{print $2}' /etc/shadow 2>/dev/null)"
echo "SHADOW_CTX=$(stat -c %C /etc/shadow 2>/dev/null)"
echo "SYS_STATE=$(systemctl is-system-running 2>/dev/null)"
echo "RELABEL_PENDING=$([ -e /.autorelabel ] && echo yes || echo no)"
echo "RDBREAK_BOOTS=$(journalctl -k -g 'Command line' -o cat --no-pager 2>/dev/null | grep -c 'rd\.break')"
"""


# --------------------------------------------------------------------------
# Scenario state
# --------------------------------------------------------------------------

def load_state():
    try:
        with open(STATE_PATH) as fh:
            return json.load(fh)
    except Exception:
        return None


def _save_state(state):
    os.makedirs(lab_machine.STATE_DIR, exist_ok=True)
    fd = os.open(STATE_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as fh:
        json.dump(state, fh, indent=2)


def clear_state():
    try:
        os.remove(STATE_PATH)
        return True
    except FileNotFoundError:
        return False


def is_active():
    return load_state() is not None


def generate_password(length=10):
    return ''.join(secrets.choice(_ALPHABET) for _ in range(length))


# --------------------------------------------------------------------------
# Scenario lifecycle
# --------------------------------------------------------------------------

def start():
    """Scramble root's password on the lab machine. Returns (ok, message).

    Refuses unless key-based SSH works (that key is the only way back in for
    validation and give-up, and must be planted BEFORE we change anything)."""
    cfg = lab_machine.load_config()
    if not cfg:
        return False, "No lab machine linked. Run Setup → Link second lab machine first."
    if is_active():
        return False, ("A rescue scenario is already active. Validate it or give "
                       "up before starting another.")
    if not lab_machine.key_works():
        return False, (f"Key-based SSH to {cfg['host']} is not working. Re-run "
                       "Setup → Link second lab machine (ssh-copy-id) first — "
                       "the key is the only way back in after the scramble.")

    ok, before, out = lab_machine.read_values(_INFO_SCRIPT)
    if not ok or not before.get('ROOT_HASH'):
        return False, f"Could not read the current state of {cfg['host']}:\n{out[-500:]}"

    password = generate_password()
    # The script travels over stdin (never argv), so the secret is not
    # exposed in `ps` on either machine. Alphabet is shell-safe by design.
    script = (f"printf 'root:{password}' | chpasswd || exit 1\n"
              f"awk -F: '$1==\"root\"{{print \"NEW_HASH=\" $2}}' /etc/shadow\n")
    ok, values, out = lab_machine.read_values(script)
    new_hash = values.get('NEW_HASH', '')
    if not ok or not new_hash or new_hash == before['ROOT_HASH']:
        return False, f"Failed to set the scenario password on {cfg['host']}:\n{out[-500:]}"

    _save_state({
        'host': cfg['host'],
        'user': cfg.get('user', 'root'),
        'planted_password': password,
        'planted_hash': new_hash,
        'original_hash': before['ROOT_HASH'],
        'boot_id': before.get('BOOT_ID', ''),
        'planted_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'rdbreak_boots': before.get('RDBREAK_BOOTS', '0'),
    })
    return True, (f"The root password on {cfg['host']} has been changed to a "
                  "random value. Go to that machine's console and recover it.")


def validate():
    """Check the recovery over the retained SSH key.

    Returns (checks, method, error) where checks is a list of
    (name, passed_or_None, message) — None = informational/warning only."""
    state = load_state()
    if not state:
        return None, None, "No rescue scenario is active."

    ok, now, out = lab_machine.read_values(_INFO_SCRIPT, host=state['host'],
                                           user=state.get('user', 'root'))
    if not ok:
        return None, None, (f"Cannot reach {state['host']} over SSH yet — finish "
                            f"the recovery and make sure it boots normally.\n{out[-300:]}")

    checks = []

    cur_hash = now.get('ROOT_HASH', '')
    if cur_hash and cur_hash != state['planted_hash']:
        checks.append(('password_changed', True, 'root password was changed'))
    else:
        checks.append(('password_changed', False,
                       'root password is still the planted one — it was not reset'))

    if now.get('BOOT_ID') and now['BOOT_ID'] != state.get('boot_id'):
        checks.append(('rebooted', True, 'machine was rebooted'))
    else:
        checks.append(('rebooted', False,
                       'machine has not rebooted since the scenario started'))

    ctx = now.get('SHADOW_CTX', '')
    if 'shadow_t' in ctx:
        checks.append(('selinux_context', True,
                       '/etc/shadow has the correct SELinux context (relabel handled)'))
    elif ctx in ('', '?', 'unlabeled'):
        checks.append(('selinux_context', None,
                       f"could not determine /etc/shadow SELinux context ({ctx or 'n/a'})"))
    else:
        checks.append(('selinux_context', False,
                       f"/etc/shadow context is '{ctx}' — the SELinux relabel was not "
                       "handled (touch /.autorelabel or restorecon /etc/shadow)"))

    sys_state = now.get('SYS_STATE', '')
    if sys_state in ('running', 'degraded'):
        checks.append(('system_up', True, f'system is up (state: {sys_state})'))
    else:
        checks.append(('system_up', False,
                       f"system state is '{sys_state or 'unknown'}' — expected a "
                       "normal multi-user boot"))

    if now.get('RELABEL_PENDING') == 'yes':
        checks.append(('relabel_pending', None,
                       '/.autorelabel exists — a full relabel will run on the next '
                       'boot (fine, but the exam expects you to let it finish)'))

    # Informational method detection, never pass/fail.
    try:
        rd_before = int(state.get('rdbreak_boots', '0') or 0)
        rd_now = int(now.get('RDBREAK_BOOTS', '0') or 0)
    except ValueError:
        rd_before = rd_now = 0
    if rd_now > rd_before:
        method = 'rd.break (found in a recovery boot kernel cmdline)'
    else:
        method = 'init=/bin/bash or console method (inferred — no rd.break boot in the journal)'

    return checks, method, None


def verify_password(password):
    """Prove the candidate's new password actually works, by checking it
    against root's hash ON the lab machine (crypt runs there; the password
    travels only over the encrypted SSH stdin). Returns True/False/None."""
    state = load_state() or {}
    script = ("python3 -W ignore - <<'RHCSA_PW_EOF'\n"
              "import crypt\n"
              f"pw = {password!r}\n"
              "h = ''\n"
              "for line in open('/etc/shadow'):\n"
              "    if line.startswith('root:'):\n"
              "        h = line.split(':')[1]\n"
              "        break\n"
              "try:\n"
              "    print('PWOK=' + ('yes' if h and crypt.crypt(pw, h) == h else 'no'))\n"
              "except Exception:\n"
              "    print('PWOK=unknown')\n"
              "RHCSA_PW_EOF\n")
    ok, values, _ = lab_machine.read_values(
        script, host=state.get('host'), user=state.get('user', 'root'))
    answer = values.get('PWOK')
    if not ok or answer not in ('yes', 'no'):
        return None
    return answer == 'yes'


def give_up(restore=True):
    """Reveal the planted password and (optionally) restore the original root
    hash exactly as it was. Returns (ok, message)."""
    state = load_state()
    if not state:
        return False, "No rescue scenario is active."
    password = state['planted_password']
    msg = f"The planted root password on {state['host']} is: {password}"
    if restore:
        # Shadow hashes never contain single quotes, so this embeds safely.
        script = f"usermod -p '{state['original_hash']}' root && echo RESTORED=yes"
        ok, values, out = lab_machine.read_values(
            script, host=state['host'], user=state.get('user', 'root'))
        if ok and values.get('RESTORED') == 'yes':
            msg += "\nThe original root password has been restored."
        else:
            msg += ("\nCould not restore the original password over SSH (machine "
                    "down?) — log in with the planted password above and set it "
                    "yourself.")
    clear_state()
    return True, msg


def reset_for_machine_reset(progress=lambda m: None):
    """full_reset hook: if a scenario is active, put the lab machine's root
    password back and drop the local state."""
    if not is_active():
        return
    progress("  restoring lab machine root password (boot-rescue scenario)")
    ok, msg = give_up(restore=True)
    if not ok:
        progress(f"    {msg}")


# --------------------------------------------------------------------------
# Walkthrough content (both methods)
# --------------------------------------------------------------------------

WALKTHROUGH = """\
GOAL: at the lab machine's console, reset the (unknown) root password by
interrupting the boot process, then let it boot normally.

METHOD A — rd.break (the classic Red Hat way)
  1. Reboot; at the GRUB menu press  e  on the default entry
  2. On the line starting with  linux , append:   rd.break
     (removing  rhgb quiet  makes the console easier to read)
  3. Boot with  Ctrl-x  → you land in a switch_root:/# emergency shell
       If instead you get "Give root password for maintenance", this build
       gates the shell — reboot and use METHOD B.
  4. mount -o remount,rw /sysroot
  5. chroot /sysroot
  6. passwd root
  7. touch /.autorelabel      (SELinux: relabels on next boot; without this
                               the new /etc/shadow is mislabeled and logins
                               can fail. Alternative: load_policy -i then
                               restorecon /etc/shadow)
  8. exit   then   exit       (boot continues; the relabel adds one reboot)

METHOD B — init=/bin/bash (works on every build)
  1. Reboot; at GRUB press  e ; on the  linux  line append:   init=/bin/bash
  2. Boot with  Ctrl-x  → bash IS pid 1 (no systemd is running)
  3. mount -o remount,rw /
  4. passwd root
  5. restorecon /etc/shadow    (or: touch /.autorelabel)
  6. Reboot — systemd is NOT running, so  reboot/systemctl  will fail. Use:
       sync
       echo b > /proc/sysrq-trigger
     (or:  /usr/sbin/reboot -f )

Then log in as root at the console with your new password, and validate
from the simulator."""


# --------------------------------------------------------------------------
# Interactive UI
# --------------------------------------------------------------------------

def interactive():
    """The Boot Rescue Lab menu loop."""
    import getpass
    from utils import formatters as fmt
    from utils.helpers import confirm_action

    while True:
        fmt.clear_screen()
        fmt.print_header("BOOT RESCUE LAB (second machine)")

        cfg = lab_machine.load_config()
        state = load_state()
        if cfg:
            print(f"Lab machine: {fmt.bold(cfg['host'])} "
                  f"(user: {cfg.get('user', 'root')})")
        else:
            print(fmt.warning("No lab machine linked — run Setup → Link second "
                              "lab machine first."))
        if state:
            print(fmt.warning(f"Scenario ACTIVE since {state['planted_at']} — "
                              f"recover root at {state['host']}'s console."))
        else:
            print(fmt.dim("No scenario active."))
        print()
        print("  1. Start scenario (scramble root password on the lab machine)")
        print("  2. Validate my recovery")
        print("  3. Show the recovery walkthrough (both methods)")
        print("  4. Give up (reveal password & restore the machine)")
        print("  0. Back")
        print()
        choice = input("Select option: ").strip()

        if choice == '1':
            print()
            print(fmt.warning("This sets a RANDOM root password on the lab machine."))
            print("You will need CONSOLE access to that machine to recover it")
            print("(virt-manager, VNC, or a physical keyboard — not SSH).")
            print(fmt.dim("The simulator keeps its own SSH key planted, so 'give up' "
                          "can always restore the machine."))
            print()
            if confirm_action("Scramble the root password now?", default=False):
                ok, msg = start()
                print()
                print(fmt.success(msg) if ok else fmt.error(msg))
                if ok:
                    print()
                    print(fmt.dim("Tip: option 3 shows the full walkthrough for both"))
                    print(fmt.dim("rd.break and init=/bin/bash."))
            input("\nPress Enter to continue...")

        elif choice == '2':
            print()
            checks, method, err = validate()
            if err:
                print(fmt.warning(err))
                input("\nPress Enter to continue...")
                continue
            all_ok = True
            for name, passed, message in checks:
                if passed is True:
                    print(f"  {fmt.success('PASS')}  {message}")
                elif passed is False:
                    print(f"  {fmt.error('FAIL')}  {message}")
                    all_ok = False
                else:
                    print(f"  {fmt.warning('NOTE')}  {message}")
            print()
            print(f"  Method detected: {fmt.dim(method)}")
            print()
            if all_ok:
                pw = getpass.getpass(
                    "Optionally type the new root password to prove it works "
                    "(Enter to skip): ")
                if pw:
                    result = verify_password(pw)
                    if result is True:
                        print(fmt.success("  Password verified — it matches root's hash."))
                    elif result is False:
                        print(fmt.error("  That password does NOT match root's current hash."))
                    else:
                        print(fmt.warning("  Could not verify (python3 missing on the "
                                          "lab machine?)."))
                print()
                print(fmt.success("Recovery complete — scenario closed. Nice work."))
                clear_state()
            else:
                print(fmt.warning("Not there yet — the scenario stays active."))
            input("\nPress Enter to continue...")

        elif choice == '3':
            print()
            print(WALKTHROUGH)
            input("\nPress Enter to continue...")

        elif choice == '4':
            if not state:
                print(fmt.dim("No scenario active."))
                input("\nPress Enter to continue...")
                continue
            print()
            if confirm_action("Reveal the password and restore the original one?",
                              default=False):
                ok, msg = give_up(restore=True)
                print()
                print(msg)
            input("\nPress Enter to continue...")

        elif choice == '0' or choice == '':
            return
