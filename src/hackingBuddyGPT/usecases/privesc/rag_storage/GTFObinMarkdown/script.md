# GTFOBin: script

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
script -q /dev/null
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

The wrote content is corrupted by debug prints.

```
script -q -c 'echo DATA' file_to_write
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo script -q /dev/null
```