# GTFOBin: file

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

Each input line is treated as a filename for the `file` command and the output is corrupted by a suffix `:` followed by the result or the error of the operation, so this may not be suitable for binary files.

```
LFILE=file_to_read
file -f $LFILE
```

Each line is corrupted by a prefix string and wrapped inside quotes, so this may not be suitable for binary files.

If a line in the target file begins with a `#`, it will not be printed as these lines are parsed as comments.

It can also be provided with a directory and will read each file in the directory.

```
LFILE=file_to_read
file -m $LFILE
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

Each input line is treated as a filename for the `file` command and the output is corrupted by a suffix `:` followed by the result or the error of the operation, so this may not be suitable for binary files.

```
sudo install -m =xs $(which file) .

LFILE=file_to_read
./file -f $LFILE
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

Each input line is treated as a filename for the `file` command and the output is corrupted by a suffix `:` followed by the result or the error of the operation, so this may not be suitable for binary files.

```
LFILE=file_to_read
sudo file -f $LFILE
```