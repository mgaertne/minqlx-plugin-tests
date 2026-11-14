from unittest.mock import Mock

from requests.adapters import HTTPAdapter

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
    adapter = session.get_adapter("https://")
    assert isinstance(adapter, HTTPAdapter)
    assert adapter.max_retries.total == 2
