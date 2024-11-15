# GTFOBin: bconsole

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
bconsole
@exec /bin/sh
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

The file is actually parsed and the first wrong line is returned in an error message, thus it may not be suitable for reading arbitrary files.

```
bconsole -c /etc/shadow
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo bconsole
@exec /bin/sh
```