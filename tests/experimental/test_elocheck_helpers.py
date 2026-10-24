from unittest.mock import Mock

import minqlx
from experimental.elocheck import (
    identify_reply_channel,
    remove_trailing_color_code,
    requests_retry_session,
)


def test_elocheck_helpers():
    assert identify_reply_channel(minqlx.BLUE_TEAM_CHAT_CHANNEL) == minqlx.CHAT_CHANNEL
    channel = Mock()
    assert identify_reply_channel(channel) is channel
    assert remove_trailing_color_code("x^7^7") == "x"
    assert remove_trailing_color_code("x") == "x"


def test_elocheck_retry_session():
    session = requests_retry_session(retries=2)
    assert session.adapters["https://"].max_retries.total == 2
