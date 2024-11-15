# GTFOBin: run-mailcap

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

This invokes the default pager, which is likely to be `less`, other functions may apply.

```
run-mailcap --action=view /etc/hosts
!/bin/sh
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

The file must exist and be not empty.

This invokes the default editor, which is likely to be `vi`, other functions may apply.

```
run-mailcap --action=edit file_to_read
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

This invokes the default pager, which is likely to be `less`, other functions may apply.

```
run-mailcap --action=view file_to_read
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

This invokes the default pager, which is likely to be `less`, other functions may apply.

```
sudo run-mailcap --action=view /etc/hosts
!/bin/sh
```