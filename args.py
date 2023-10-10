import argparse
import json
import os

from dataclasses import dataclass
from dotenv import load_dotenv
from llms.llm_connection import get_potential_llm_connections

@dataclass
class ConfigTarget:
    ip : str = None
    hostname : str = None
    user : str = None
    password : str = None
    os : str = None
    hint : str = None

@dataclass
class Config:
    enable_explanation : bool = False
    enable_update_state : bool = False
    disable_history : bool = False

    target : ConfigTarget = None

    log : str = ':memory:'
    max_rounds : int = 10
    llm_connection : str = None
    llm_server_base_url : str = None
    model : str = None
    context_size : int = 4096
    tag : str = None
    
def parse_args_and_env(console) -> Config:
    # setup dotenv
    load_dotenv()

    # perform argument parsing
    # for defaults we are using .env but allow overwrite through cli arguments
    parser = argparse.ArgumentParser(description='Run an LLM vs a SSH connection.')
    parser.add_argument('--enable-explanation', help="let the LLM explain each round's result", action="store_true")
    parser.add_argument('--enable-update-state', help='ask the LLM to keep a multi-round state with findings', action="store_true")
    parser.add_argument('--disable-history', help='do not use history of old cmd executions when generating new ones', action="store_true")
    parser.add_argument('--log', type=str, help='sqlite3 db for storing log files', default=os.getenv("LOG_DESTINATION") or ':memory:')
    parser.add_argument('--target-ip', type=str, help='ssh hostname to use to connect to target system', default=os.getenv("TARGET_IP") or '127.0.0.1')
    parser.add_argument('--target-hostname', type=str, help='safety: what hostname to exepct at the target IP', default=os.getenv("TARGET_HOSTNAME") or "debian")
    parser.add_argument('--target-user', type=str, help='ssh username to use to connect to target system', default=os.getenv("TARGET_USER") or 'lowpriv')
    parser.add_argument('--target-password', type=str, help='ssh password to use to connect to target system', default=os.getenv("TARGET_PASSWORD") or 'trustno1')
    parser.add_argument('--max-rounds', type=int, help='how many cmd-rounds to execute at max', default=int(os.getenv("MAX_ROUNDS")) or 10)
    parser.add_argument('--llm-connection', type=str, help='which LLM driver to use', choices=get_potential_llm_connections(), default=os.getenv("LLM_CONNECTION") or "openai_rest")
    parser.add_argument('--target-os', type=str, help='What is the target operating system?', choices=["linux", "windows"], default="linux")
    parser.add_argument('--model', type=str, help='which LLM to use', default=os.getenv("MODEL") or "gpt-3.5-turbo")
    parser.add_argument('--llm-server-base-url', type=str, help='which LLM server to use', default=os.getenv("LLM_SERVER_BASE_URL") or "https://api.openai.com")
    parser.add_argument('--tag', type=str, help='tag run with string', default="")
    parser.add_argument('--context-size', type=int, help='model context size to use', default=int(os.getenv("CONTEXT_SIZE")) or 4096)
    parser.add_argument('--hints', type=argparse.FileType('r', encoding='latin-1'), help='json file with a hint per tested hostname', default=None)

    args = parser.parse_args()
    hint = get_hint(args, console)

    target = ConfigTarget(args.target_ip, args.target_hostname, args.target_user, args.target_password, args.target_os, hint)

    return Config(args.enable_explanation, args.enable_update_state, args.disable_history, target, args.log, args.max_rounds, args.llm_connection, args.llm_server_base_url, args.model, args.context_size, args.tag)

def get_hint(args, console):
    if args.hints:
        try:
            hints = json.load(args.hints)
            if args.target_hostname in hints:
                hint = hints[args.target_hostname]
                console.print(f"[bold green]Using the following hint: '{hint}'")
                return hint
        except:
            console.print("[yellow]Was not able to load hint file")
    return None
