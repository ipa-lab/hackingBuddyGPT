# GTFOBin: vigr

This command allows to edit some designated files (`/etc/passwd`, `/etc/group`, `/etc/shadow` and `/etc/gshadow`) safely by spawning the default editor (falling back to `vim`, other functions may apply). Despite requiring superuser privileges to run, the editor is executed as the unprivileged user when run as SUID or with `sudo`.

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which vigr) .

./vigr
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo vigr
```