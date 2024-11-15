# GTFOBin: red

Read and write files limited to the current directory.

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
red file_to_write
a
DATA
.
w
q
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
red file_to_read
,p
q
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo red file_to_write
a
DATA
.
w
q
```