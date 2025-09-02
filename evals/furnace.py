#!/usr/bin/env python3
"""
Run one coordination container plus N evals (each with arbitrary test/service containers) in isolated Docker networks,
loading settings from a YAML config file. Logs for all containers per eval instance are written to a single logfile, with archiving of old logs.
Supports limiting simultaneous parallel eval runs via `parallel_evals` config, and includes error checking on Docker API calls.

Install dependencies:
    pip install docker pyyaml

Usage:
    ./run_evals_dockerpy.py path/to/config.yaml
"""
import argparse
import sys
import os
import yaml
import docker
import time
import threading
import signal
from datetime import datetime, timezone
from docker.errors import NotFound, APIError, DockerException

interrupt_count = 0  # module-level interrupt counter


def parse_args():
    parser = argparse.ArgumentParser(
        description="Spawn coordination container + parallel eval runs with configured services."
    )
    parser.add_argument('config', help='Path to YAML configuration file')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    return parser.parse_args()


def debug(*msg):
    global output_debug
    if output_debug:
        print(*msg, file=sys.stderr)


def load_config(path):
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config file {path}: {e}", file=sys.stderr)
        sys.exit(1)


def ensure_network(client, name):
    try:
        net = client.networks.get(name)
        debug(f"Using existing network '{name}'")
        debug(f"Equivalent bash: docker network inspect {name}")
        return net
    except NotFound:
        try:
            debug(f"Creating network '{name}'")
            debug(f"Equivalent bash: docker network create --driver bridge {name}")
            return client.networks.create(name, driver="bridge")
        except APIError as e:
            print(f"Failed to create network '{name}': {e}", file=sys.stderr)
            sys.exit(1)
    except APIError as e:
        print(f"Error inspecting network '{name}': {e}", file=sys.stderr)
        sys.exit(1)


def ensure_container(client, name, cfg, network):
    """
    Always creates a new container (removing any existing one), with config:
      - image, hostname, environment, volumes, ports, command
    Prints equivalent bash commands.
    """
    try:
        existing = client.containers.get(name)
        debug(f"Removing existing container '{name}'")
        debug(f"Equivalent bash: docker rm -f {name}")
        existing.remove(force=True)
    except NotFound:
        pass
    except APIError as e:
        print(f"Error removing existing container '{name}': {e}", file=sys.stderr)
        sys.exit(1)

    # Build run kwargs and bash command
    run_kwargs = {'name': name, 'network': network.name, 'detach': True}
    bash_parts = ["docker run -d", f"--name {name}", f"--network {network.name}"]
    if cfg.get('hostname'):
        run_kwargs['hostname'] = cfg['hostname']
        bash_parts.append(f"--hostname {cfg['hostname']}")
    if cfg.get('environment'):
        run_kwargs['environment'] = cfg['environment']
        for k, v in cfg['environment'].items():
            bash_parts.append(f"-e {k}={v}")
    volume_dict = {}
    for vol in cfg.get('volumes', []) or []:
        host_path, container_path, *mode = vol.split(':')
        if not os.path.isabs(host_path):
            host_path = os.path.abspath(host_path)
        m = mode[0] if mode else 'rw'
        volume_dict[host_path] = {'bind': container_path, 'mode': m}
        bash_parts.append(f"-v {host_path}:{container_path}:{m}")
    if volume_dict:
        run_kwargs['volumes'] = volume_dict
    port_map = {}
    for p in cfg.get('ports', []) or []:
        host_p, cont_p = p.split(':')
        port_map[int(cont_p)] = int(host_p)
        bash_parts.append(f"-p {p}")
    if port_map:
        run_kwargs['ports'] = port_map
    if cfg.get('command'):
        run_kwargs['command'] = cfg['command']
        bash_parts.append(' '.join(cfg['command']))
    bash_parts.insert(len(bash_parts)-1, cfg['image'])
    bash_cmd = ' '.join(bash_parts)

    try:
        debug(f"Creating container '{name}' (image={cfg['image']})")
        debug(f"Equivalent bash: {bash_cmd}")
        container = client.containers.run(cfg['image'], **run_kwargs)
        return container
    except APIError as e:
        print(f"Docker API error creating container '{name}': {e}", file=sys.stderr)
        sys.exit(1)
    except DockerException as e:
        print(f"Unexpected Docker error for '{name}': {e}", file=sys.stderr)
        sys.exit(1)


def stream_logs(container, logfile):
    try:
        for line in container.logs(stream=True, follow=True):
            ts = datetime.now(timezone.utc).isoformat()
            with open(logfile, 'a') as f:
                f.write(f"[{ts}] {container.name}: {line.decode(errors='replace')}\n")
    except APIError as e:
        print(f"Error streaming logs for '{container.name}': {e}", file=sys.stderr)


def cleanup_instance(client, experiment, idx, services):
    prefix = f"{experiment}_eval_{idx}"
    for svc in services:
        for j in range(1, svc.get('count', 1) + 1):
            cname = f"{prefix}_{svc['name']}_{j}"
            try:
                c = client.containers.get(cname)
                debug(f"Removing container {cname}")
                c.remove(force=True)
            except NotFound:
                pass
            except APIError as e:
                print(f"Error removing container '{cname}': {e}", file=sys.stderr)
    ename = prefix
    try:
        c = client.containers.get(ename)
        debug(f"Removing container {ename}")
        c.remove(force=True)
    except NotFound:
        pass
    except APIError as e:
        print(f"Error removing container '{ename}': {e}", file=sys.stderr)
    netname = f"{experiment}_eval_net_{idx}"
    try:
        net = client.networks.get(netname)
        debug(f"Removing network {netname}")
        net.remove()
    except NotFound:
        pass
    except APIError as e:
        print(f"Error removing network '{netname}': {e}", file=sys.stderr)


def main():
    global output_debug
    args = parse_args()
    output_debug = args.debug

    cfg = load_config(args.config)

    experiment = cfg['experiment_name']
    total = cfg['eval_count']
    parallel = cfg.get('parallel_evals', total)
    coord_cfg = cfg['coord']
    eval_cfg = cfg['eval']
    services = cfg.get('tests', [])

    client = docker.from_env()
    coord_net = ensure_network(client, f"{experiment}_coord_net")
    coord_ctr = ensure_container(client, f"{experiment}_coordination", coord_cfg, coord_net)

    pending = list(range(1, total + 1))
    active = {}
    interrupt_count = 0

    def sigint_handler(signum, frame):
        nonlocal pending, active, interrupt_count
        interrupt_count += 1
        if interrupt_count == 1:
            pending.clear()
            print("\nCtrl+C detected: cleared pending experiments. Next Ctrl+C will stop running ones.")
        elif interrupt_count == 2:
            print("\nSecond Ctrl+C: stopping all running experiments. Next Ctrl+C will exit immediately.")
            for i, info in list(active.items()):
                try:
                    info['ctr'].stop()
                    info['ctr'].remove()
                    print(f"Stopped and removed running eval #{i}")
                except Exception as e:
                    print(f"Error stopping eval #{i}: {e}", file=sys.stderr)
            active.clear()
        else:
            print("\nThird Ctrl+C: exiting program.")
            sys.exit(1)

    signal.signal(signal.SIGINT, sigint_handler)

    def start_instance(i):
        nonlocal pending, active
        net = ensure_network(client, f"{experiment}_eval_net_{i}")
        logdir = ".log"
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        logfile = f"{logdir}/{experiment}_eval_{i}.log"
        if os.path.exists(logfile):
            mtime = os.path.getmtime(logfile)
            ts = datetime.fromtimestamp(mtime).strftime("%Y%m%d_%H%M%S")
            archive = f"{logdir}/{experiment}_eval_{i}_{ts}.log"
            os.rename(logfile, archive)
        open(logfile, 'w').close()
        for svc in services:
            for j in range(1, svc.get('count', 1) + 1):
                cname = f"{experiment}_eval_{i}_{svc['name']}_{j}"
                svc_ctr = ensure_container(client, cname, svc, net)
                threading.Thread(target=stream_logs, args=(svc_ctr, logfile), daemon=True).start()
        name = f"{experiment}_eval_{i}"
        ctr = ensure_container(client, name, eval_cfg, net)
        try:
            coord_net.connect(ctr)
        except APIError as e:
            print(f"Error connecting '{name}' to network: {e}", file=sys.stderr)
        threading.Thread(target=stream_logs, args=(ctr, logfile), daemon=True).start()
        active[i] = {'ctr': ctr, 'start': datetime.now(timezone.utc)}
        print(f"Launched eval #{i}")

    print(f"Starting up to {parallel} evals concurrently...")
    while pending and len(active) < parallel:
        start_instance(pending.pop(0))

    while active:
        to_remove = []
        for i, info in list(active.items()):
            try:
                info['ctr'].reload()
            except APIError as e:
                print(f"Error reloading container '{i}': {e}", file=sys.stderr)
                to_remove.append(i)
                continue
            if info['ctr'].status != 'running':
                duration = datetime.now(timezone.utc) - info['start']
                print(f"Eval #{i} finished in {duration}")
                cleanup_instance(client, experiment, i, services)
                to_remove.append(i)
        for i in to_remove:
            del active[i]
            if pending and interrupt_count < 2:
                start_instance(pending.pop(0))
        time.sleep(1)

    print("All eval instances complete.")
    resp = input("Stop and remove coordination container and network? [y/N]: ")
    if resp.lower().startswith('y'):
        try:
            coord_ctr.stop(); coord_ctr.remove()
        except APIError as e:
            print(f"Error removing coordination container: {e}", file=sys.stderr)
        debug(f"Removing network {experiment}_coord_net")
        try:
            coord_net.remove()
        except APIError as e:
            print(f"Error removing coordination network: {e}", file=sys.stderr)
    else:
        print("Leaving coordination container and network in place.")
        debug(f"Equivalent bash: docker rm -f {experiment}_coordination")
        debug(f"Equivalent bash: docker network rm {experiment}_coord_net")

if __name__ == '__main__':
    try:
        main()
    except APIError as e:
        print(f"Docker API error in main(): {e}", file=sys.stderr)
        sys.exit(1)
    except DockerException as e:
        print(f"Docker exception in main(): {e}", file=sys.stderr)
        sys.exit(1)
