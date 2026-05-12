import datetime
from unittest.mock import Mock

from rich.console import Console

from hackingBuddyGPT.utils.logging import LocalLogger


def test_local_logger_prints_message_content_as_plain_text():
    db = Mock()
    db.create_run.return_value = 1
    logger = LocalLogger(log_db=db, console=Console(record=True))
    logger.start_run("test", "{}")

    content = "binary-looking response with invalid rich markup [/not-open]"

    logger.add_message("assistant", content, 0, 0, datetime.timedelta(0))

    db.add_message.assert_called_once_with(1, 0, None, "assistant", content, 0, 0, datetime.timedelta(0))


def test_local_logger_prints_tool_result_as_plain_text():
    db = Mock()
    db.create_run.return_value = 1
    logger = LocalLogger(log_db=db, console=Console(record=True))
    logger.start_run("test", "{}")

    arguments = '{"path": "/favicon.ico"}'
    result_text = "HTTP/1.1 200 OK\r\n\r\n\x00binary-looking response [/not-open]"
    duration = datetime.timedelta(milliseconds=1)

    logger.add_tool_call(0, "tool-call-0", "http_request", arguments, result_text, duration)

    db.add_tool_call.assert_called_once_with(
        1,
        0,
        "tool-call-0",
        "http_request",
        arguments,
        result_text,
        duration,
    )
