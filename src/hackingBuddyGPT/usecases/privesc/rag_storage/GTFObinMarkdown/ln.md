# GTFOBin: ln

This overrides `ln` itself with a symlink to a shell (or any other executable) that is to be executed as root, useful in case a `sudo` rule allows to only run `ln` by path. Warning, this is a destructive action.

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo ln -fs /bin/sh /bin/ln
sudo ln
```