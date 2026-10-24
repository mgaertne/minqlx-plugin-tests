from unittest.mock import Mock

import minqlx
from experimental.balancetwo import (
    format_team,
    identify_reply_channel,
    other_team,
    remove_trailing_color_code,
    report_ratings_for_team,
    requests_retry_session,
)


def test_balancetwo_format_helpers():
    assert format_team("red") == "^1red^7"
    assert format_team("blue") == "^4blue^7"
    assert format_team("spec") == "^3spec^7"
    assert other_team("red") == "blue"
    assert other_team("blue") == "red"
    assert remove_trailing_color_code("name^7") == "name"
    assert remove_trailing_color_code("name") == "name"


def test_identify_reply_channel():
    assert identify_reply_channel(minqlx.RED_TEAM_CHAT_CHANNEL) == minqlx.CHAT_CHANNEL
    channel = Mock()
    assert identify_reply_channel(channel) is channel


def test_requests_retry_session_configures_adapters():
    session = requests_retry_session(retries=1)
    assert session.adapters["http://"].max_retries.total == 1


def test_report_ratings_for_empty_team_does_not_reply():
    channel = Mock()
    report_ratings_for_team(channel, [], "ca", Mock(), Mock())
    channel.reply.assert_not_called()
