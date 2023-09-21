import argparse
import json
import os

from dotenv import load_dotenv
from llms.llm_connection import get_potential_llm_connections

def parse_args_and_env():
    # setup dotenv
    load_dotenv()

    # perform argument parsing
    # for defaults we are using .env but allow overwrite through cli arguments
    parser = argparse.ArgumentParser(description='Run an LLM vs a SSH connection.')
    parser.add_argument('--enable-explanation', help="let the LLM explain each round's result", action="store_true")
    parser.add_argument('--enable-update-state', help='ask the LLM to keep a multi-round state with findings', action="store_true")
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

    return parser.parse_args()


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