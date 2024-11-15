# GTFOBin: dos2unix

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
LFILE1=file_to_read
LFILE2=file_to_write
dos2unix -f -n "$LFILE1" "$LFILE2"
```