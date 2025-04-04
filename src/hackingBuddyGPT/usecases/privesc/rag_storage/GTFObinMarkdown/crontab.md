# GTFOBin: crontab

## Command

It can be used to break out from restricted environments by running non-interactive system commands.

The commands are executed according to the crontab file edited via the `crontab` utility.

```
crontab -e
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

The commands are executed according to the crontab file edited via the `crontab` utility.

```
sudo crontab -e
```