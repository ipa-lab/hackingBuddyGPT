# GTFOBin: pax

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

The output is a `tar` archive containing the read file as it is, hence this may not be suitable to read arbitrary binary files.

```
LFILE=file_to_read
pax -w "$LFILE"
```