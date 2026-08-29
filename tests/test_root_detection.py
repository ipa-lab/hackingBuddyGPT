from hackingBuddyGPT.utils.shell_root_detection import (
    LOGIN_AS_ROOT_SUCCESSFUL,
    check_command_success,
    got_root,
    is_root_from_id,
    strip_ansi,
)


def test_got_root():
    hostname = "i_dont_care"

    assert got_root(hostname, "# ") is True
    assert got_root(hostname, "$ ") is False


def test_got_root_variants():
    assert got_root("box", "bash-5.1# ") is True
    assert got_root("box", "root@box:~# some output here") is True
    assert got_root("box", "alice@box:~$ ") is False
    # only the last line is considered, and ANSI escapes are stripped first
    assert got_root("box", "some output\n\x1b[01;31m# ") is True
    assert got_root("box", "root@other:~#") is False  # different hostname, not a bare-prompt regex


def test_is_root_from_id():
    assert is_root_from_id("uid=0(root) gid=0(root) groups=0(root)") is True
    assert is_root_from_id("0\n") is True  # `id -u` as root
    assert is_root_from_id("uid=1000(alice) gid=1000(alice) euid=0(root)") is True  # setuid-root
    assert is_root_from_id("uid=1000(alice) gid=1000(alice) groups=1000(alice)") is False
    assert is_root_from_id("1000\n") is False  # `id -u` as low-priv user
    assert is_root_from_id("this mentions root but is not id output") is False


def test_strip_ansi():
    assert strip_ansi("\x1b[01;31mred\x1b[0m") == "red"
    assert strip_ansi(None) == ""


def test_check_command_success_credential_path():
    assert check_command_success("box", "test_credential alice hunter2", LOGIN_AS_ROOT_SUCCESSFUL) is True
    assert check_command_success("box", "test_credential alice hunter2", "wrong\n") is False


def test_check_command_success_layers():
    # session-probed uid is authoritative
    assert check_command_success("box", "id", "irrelevant", uid=0) is True
    assert check_command_success("box", "id", "uid=1000(alice)", uid=1000) is False
    # falls back to parsing id output when no probed uid is available
    assert check_command_success("box", "id", "uid=0(root) gid=0(root)") is True
    # falls back to the prompt heuristic last
    assert check_command_success("box", "sudo su", "root@box:~# ") is True
    assert check_command_success("box", "whoami", "alice") is False


def test_is_admin_from_whoami():
    from hackingBuddyGPT.utils.shell_root_detection import is_admin_from_whoami

    # running as SYSTEM
    assert is_admin_from_whoami("nt authority\\system") is True
    assert is_admin_from_whoami("NT AUTHORITY\\SYSTEM") is True
    # enabled Administrators-group membership (SID S-1-5-32-544)
    assert is_admin_from_whoami(
        "BUILTIN\\Administrators S-1-5-32-544 Enabled group, Group owner"
    ) is True
    # filtered token: Administrators present but "deny only" -> not elevated
    assert is_admin_from_whoami(
        "BUILTIN\\Administrators S-1-5-32-544 Group used for deny only"
    ) is False
    # a plain low-priv user
    assert is_admin_from_whoami("myhost\\alice S-1-5-21-1000 Mandatory group, Enabled") is False


def test_check_windows_admin_success():
    from hackingBuddyGPT.utils.shell_root_detection import (
        LOGIN_AS_ROOT_SUCCESSFUL,
        check_windows_admin_success,
    )

    # credential-test path reuses the shared success message
    assert check_windows_admin_success("test_credential admin hunter2", LOGIN_AS_ROOT_SUCCESSFUL) is True
    assert check_windows_admin_success("test_credential admin wrong", "Authentication error\n") is False
    # command path: whoami output showing SYSTEM / Administrators
    assert check_windows_admin_success("whoami", "nt authority\\system") is True
    assert check_windows_admin_success(
        "whoami /groups", "BUILTIN\\Administrators S-1-5-32-544 Enabled group"
    ) is True
    assert check_windows_admin_success("whoami", "myhost\\alice") is False
