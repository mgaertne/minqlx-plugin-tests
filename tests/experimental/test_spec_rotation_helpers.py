from experimental.spec_rotation import color_format_team, damage_this_round, other_team


def test_spec_rotation_helpers():
    assert other_team("red") == "blue"
    assert other_team("blue") == "red"
    assert color_format_team("red") == "^1red^7"
    assert color_format_team("blue") == "^4blue^7"
    assert damage_this_round({1: 42}, 1) == 42
    assert damage_this_round({}, 1) == 0
