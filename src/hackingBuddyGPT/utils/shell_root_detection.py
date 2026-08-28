import re

# Shared message returned by the *_test_credential capabilities when a candidate login turns out to
# be root, and matched again by the strategy use-cases' success check. Keep producers and consumers
# pointed at this single constant instead of repeating the literal.
LOGIN_AS_ROOT_SUCCESSFUL = "Login as root was successful\n"

# Fallback heuristic: recognise a root shell from the prompt captured in a command's output. This is
# fragile (depends on PS1/TERM/locale and on actually capturing the prompt), so it is only consulted
# after the active `id` probe below.
GOT_ROOT_REGEXPs = [re.compile("^# $"), re.compile("^bash-[0-9]+.[0-9]# $")]

_ANSI_ESCAPE = re.compile(
    r"\x1B\][^\x07\x1B]*(?:\x07|\x1B\\)"  # OSC string (e.g. window-title), BEL- or ST-terminated
    r"|\x1B\[[0-?]*[ -/]*[@-~]"           # CSI sequence (colours, bracketed-paste mode, etc.)
    r"|\x1B[@-Z\\-_]"                     # other two-character escapes
)

# Primary signal: `uid=0(...)` / `euid=0(...)` in the output of `id` (or `sudo id`).
_UID0_RE = re.compile(r"\b(?:e)?uid=0\(")


def strip_ansi(output: str) -> str:
    return _ANSI_ESCAPE.sub("", output or "")


def is_root_from_id(output: str) -> bool:
    """Detect root from an active identity probe: the output of `id -u` (a bare ``0``) or of
    `id` / `sudo id` (contains ``uid=0(`` or ``euid=0(``). Locale-, distro- and prompt-independent,
    which is why this is preferred over the prompt heuristic below."""
    text = strip_ansi(output).strip()
    if text == "0":
        return True
    return bool(_UID0_RE.search(text))


def got_root(hostname: str, output: str) -> bool:
    """Prompt-based fallback: does the last line of ``output`` look like a root shell prompt?"""
    text = strip_ansi(output)
    last_line = text.split("\n")[-1]
    for regexp in GOT_ROOT_REGEXPs:
        if regexp.fullmatch(last_line):
            return True
    return last_line.startswith(f"root@{hostname}:")


def check_command_success(hostname: str, cmd: str, result: str, uid: int = None) -> bool:
    """Single entry point every strategy use-case uses to decide whether a command achieved root.

    Layered, most-robust-first:
      1. credential tests report success through the shared ``LOGIN_AS_ROOT_SUCCESSFUL`` message;
      2. a session-probed effective uid of 0 (from an interactive connector) is authoritative;
      3. otherwise fall back to parsing an `id` probe out of the command output, then
      4. to the prompt heuristic.
    """
    if cmd.startswith("test_credential"):
        return result == LOGIN_AS_ROOT_SUCCESSFUL
    if uid is not None and uid == 0:
        return True
    if is_root_from_id(result):
        return True
    return got_root(hostname, result)
