from hackingBuddyGPT.utils.shell_root_detection import got_root


def test_got_root():
    hostname = "i_dont_care"

    assert got_root(hostname, "# ") is True
    assert got_root(hostname, "$ ") is False
