The following tasks are BAD.

Task 3: (10 points)                                                                                                                        │
Configure persistent systemd journal storage:                                                                                              │
                                                                                                                                           │
  By default, the systemd journal stores logs in volatile memory                                                                           │
  (/run/log/journal) and they are lost on reboot.                                                                                          │
                                                                                                                                           │
  Required configuration:                                                                                                                  │
  1. Create the persistent journal directory: /var/log/journal                                                                             │
  2. Set correct ownership: chown root:systemd-journal /var/log/journal                                                                    │
  3. Set correct permissions: chmod 2755 /var/log/journal                                                                                  │
  4. Edit /etc/systemd/journald.conf:                                                                                                      │
     - Set Storage=auto under the [Journal] section                                                                                        │
     (Use auto mode (persists if /var/log/journal/ directory exists))                                                                      │
  5. Restart the journal service: systemctl restart systemd-journald                                                                       │
                                                                                                                                           │
  After configuration, logs will persist across reboots.                                                                                   │
  Verify with: journalctl --list-boots                                                                                                     │
      Domain 2: System Setup & Boot

Task 5: (15 points)                                                                                                                        │
Boot Troubleshooting Scenario:                                                                                                             │
  Problem: System boots to text mode but must provide a GUI                                                                                │
                                                                                                                                           │
  Required fixes:                                                                                                                          │
  1. Set default target to: graphical.target                                                                                               │
  2. Set GRUB timeout to: 5 seconds                                                                                                        │
  3. Ensure 'rhgb' is in the kernel command line                                                                                           │
  4. Regenerate the GRUB configuration                                                                                                     │
  - All changes must persist across reboots                                                                                                │
      Domain 2: System Setup & Boot                                                                                                        │


=TROUBLESHOOTING: Apache Serving 403 Forbidden                                                                                             │
=TROUBLESHOOTING: Apache Serving 403 Forbidden                                                                                             │
=TROUBLESHOOTING: Apache Serving 403 Forbidden                                                                                             │
=TROUBLESHOOTING: Apache Serving 403 Forbidden                                                                                             │
=TROUBLESHOOTING: Apache Serving 403 Forbidden                                                                                             │
=TROUBLESHOOTING: Apache Serving 403 Forbidden                                                                                             │
=                                                                                                                                          │
                                                                                                                                           │
Symptom: httpd is running but returns 403 Forbidden for all requests.                                                                      │
The web content exists in /var/www/html but cannot be served.                                                                              │
                                                                                                                                           │
Tasks:                                                                                                                                     │
  1. Identify why httpd cannot read /var/www/html                                                                                          │
  2. Fix the SELinux issue                                                                                                                 │
  3. Verify httpd can serve content (curl http://localhost)                                                                                │
  4. Ensure the fix survives a relabel (restorecon)                                                                                        │
      Domain 7: Security - SELinux & Firewall      

      Why do you give me all the answers? Don't do that










Task 8: (20 points)                                                                                                                        │
Perform a COMPLETE network configuration:                                                                                                  │
  1. Set hostname to: node1.lab.example.com                                                                                                │
  2. Configure connection 'ens160' on ens160:                                                                                              │
     - IP Address: 192.168.153.247/24                                                                                                      │
     - Gateway: 192.168.153.1                                                                                                              │
     - DNS Servers: 8.8.8.8, 8.8.4.4                                                                                                       │
     - IPv4 method: manual                                                                                                                 │
  3. Activate the connection                                                                                                               │
  ALL settings must persist across reboots.                                                                                                │
      Domain 5: Network & DNS                                                                                                              │

     this (ens160) is my actual connection. I cannot modify it. You need to create a new, fake network connection.



Task 11: (10 points)                                                                                                                       │
Create a script using command substitution:                                                                                                │
  - Script path: /usr/local/bin/current_date.sh                                                                                            │
  - Task: Get current date and include in a filename                                                                                       │
  - Use $(command) or `command` syntax                                                                                                     │
  - Store command output in a variable                                                                                                     │
      Domain 8: Automation & Scripting   
this is also telling me the answer? Would the rhcsav10 ask this in this way? Or would there be less hints?





Task 12: (10 points)                                                                                                                       │
Extend a volume group:                                                                                                                     │
  - Volume group: vg_practice                                                                                                              │
  - Add new device: /dev/loop2                                                                                                             │
  - Create PV on the new device first                                                                                                      │
  - Verify VG has increased in size                                                                                                        │
      Domain 4: Storage & Filesystems

there is no vg or pv or anything created. my lsblk has no volumes created anywhere.





OUBLESHOOTING: Web Service Not Running at Boot                                                                                          │
=TROUBLESHOOTING: Web Service Not Running at Boot                                                                                          │
=TROUBLESHOOTING: Web Service Not Running at Boot                                                                                          │
=TROUBLESHOOTING: Web Service Not Running at Boot                                                                                          │
=TROUBLESHOOTING: Web Service Not Running at Boot                                                                                          │
=TROUBLESHOOTING: Web Service Not Running at Boot                                                                                          │
=TROUBLESHOOTING: Web Service Not Running at Boot                                                                                          │
=TROUBLESHOOTING: Web Service Not Running at Boot                                                                                          │
=TROUBLESHOOTING: Web Service Not Running at Boot                                                                                          │
=TROUBLESHOOTING: Web Service Not Running at Boot                                                                                          │
=TROUBLESHOOTING: Web Service Not Running at Boot                                                                                          │
=TROUBLESHOOTING: Web Service Not Running at Boot                                                                                          │
=TROUBLESHOOTING: Web Service Not Running at Boot                                                                                          │
=TROUBLESHOOTING: Web Service Not Running at Boot                                                                                          │
=TROUBLESHOOTING: Web Service Not Running at Boot                                                                                          │
=TROUBLESHOOTING: Web Service Not Running at Boot                                                                                          │
=                                                                                                                                          │
                                                                                                                                           │
Symptom: After a reboot, httpd is not running. The service was                                                                             │
previously configured but is now stopped and disabled.                                                                                     │
                                                                                                                                           │
Tasks:                                                                                                                                     │
  1. Start the httpd service                                                                                                               │
  2. Enable it to start automatically at boot                                                                                              │
  3. Verify both states                                                                                                                    │
      Domain 4: Storage & Filesystem


why does that say troublshooting so many times? That's not a log and it looks shit




Task 20: (10 points)                                                                                                                       │
Extend a filesystem:                                                                                                                       │
  - Device: /dev/mapper/vg_practice-lv_practice                                                                                            │
  - Filesystem type: ext4                                                                                                                  │
  - Resize to approximately 350MB                                                                                                          │
  - Filesystem must remain mounted (if applicable)                                                                                         │
  - Data must not be lost                                                                                                                  │
  - Note: if this LV does not exist yet, set up practice disks first (Setup → 1) 


the LV does not exist. This is in the SAME session. I ran set up practice disks and all it did was create 3 loop devices.

Also, I want loop devices AND I want to use /dev/sda. So let me use both in the settings or at least let the tasks SEE that I have both.


Task 21: (12 points)                                                                                                                       │
Configure a DNF repository with GPG key verification:                                                                                      │
  - Repository ID: vendorrepo                                                                                                              │
  - Repository name: Vendor Software Repository                                                                                            │
  - Base URL: https://packages.vendor.example.com/rhel9/x86_64                                                                             │
  - GPG key URL: https://packages.vendor.example.com/RPM-GPG-KEY-vendor                                                                    │
  - GPG checking must be enabled (gpgcheck=1)                                                                                              │
  - The repository must be enabled                                                                                                         │
  - Create the file: /etc/yum.repos.d/vendorrepo.repo                                                                                      │
      Domain 1: Software Management                                                                                                        │


    that's not a real repo. Use real repos so that it doesn't break dnf


Deploy an agent to go look for questions with answers in them.














