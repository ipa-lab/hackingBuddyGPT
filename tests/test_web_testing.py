from unittest.mock import Mock

from hackingBuddyGPT.capabilities.submit_flag import SubmitFlag
from hackingBuddyGPT.usecases.web.with_explanation import WebTestingWithExplanation


def test_submit_flag_can_accept_any_flag_and_call_success_callback():
    success_callback = Mock()
    submit_flag = SubmitFlag(
        flag_format="any CTF flag",
        valid_flags=set(),
        success_function=success_callback,
        accept_any_flag=True,
    )

    result = submit_flag("CTF{unknown_flag}")

    assert result == "Flag submitted (1)"
    success_callback.assert_called_once_with()


def test_web_testing_stops_after_unknown_flag_submission_by_default():
    agent = WebTestingWithExplanation(llm=Mock(), log=Mock(), flags="known")
    agent.init()

    result = agent._capabilities["SubmitFlag"]("CTF{unknown_flag}")

    assert result == "Flag submitted (1)"
    assert agent._all_flags_found is True
    agent.log.status_message.assert_called_once_with("All flags found! Congratulations!")


def test_submit_flag_can_still_require_configured_flags():
    success_callback = Mock()
    submit_flag = SubmitFlag(
        flag_format="known flags only",
        valid_flags={"FLAG.known.GALF"},
        success_function=success_callback,
        accept_any_flag=False,
    )

    assert submit_flag("CTF{unknown_flag}") == "Not a valid flag"
    success_callback.assert_not_called()

    assert submit_flag("FLAG.known.GALF") == "Flag submitted (1/1)"
    success_callback.assert_called_once_with()
