# GTFOBin: yelp

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

This spawns a graphical window containing the file content somehow corrupted by word wrapping, it might not be suitable to read arbitrary files. The path must be absolute.

```
LFILE=file_to_read
yelp "man:$LFILE"
```