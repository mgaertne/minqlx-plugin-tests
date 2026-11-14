Feature: Deciding votes before the time is up

  Map and kick votes end as soon as the result is clear, depending on the strategy: either when one side leads by
  enough votes, or when enough connected players have voted and it is not a draw.

  Scenario: A vote passes as soon as the yes votes lead by 6
    Given the fastvotes plugin is loaded with the "threshold" strategy
    And player "Alice" is connected
    And a "map" vote is running with 5 yes and 0 no votes
    When Alice votes yes
    Then the vote is passed immediately

  Scenario: A vote fails as soon as the no votes lead by 5
    Given the fastvotes plugin is loaded with the "threshold" strategy
    And player "Alice" is connected
    And a "kick" vote is running with 0 yes and 4 no votes
    When Alice votes no
    Then the vote is failed immediately

  Scenario: A vote without a clear lead is left running
    Given the fastvotes plugin is loaded with the "threshold" strategy
    And player "Alice" is connected
    And a "map" vote is running with 2 yes and 1 no votes
    When Alice votes yes
    Then the vote is left running

  Scenario: Other kinds of votes are not decided early
    Given the fastvotes plugin is loaded with the "threshold" strategy
    And player "Alice" is connected
    And a "teamsize" vote is running with 5 yes and 0 no votes
    When Alice votes yes
    Then the vote is left running

  Scenario: Votes arriving before the server ends a decided vote do not decide it again
    Given the fastvotes plugin is loaded with the "threshold" strategy
    And player "Alice" is connected
    And player "Bob" is connected
    And a "map" vote is running with 5 yes and 0 no votes
    When Alice votes yes
    And Bob votes yes
    Then the vote is passed immediately once

  Scenario: Votes are ignored once the vote is no longer active
    Given the fastvotes plugin is loaded with the "threshold" strategy
    And player "Alice" is connected
    And a "map" vote is running with 5 yes and 0 no votes
    And the vote is over
    When Alice votes yes
    Then the vote is left running

  Scenario: A vote passes when enough players voted and yes leads
    Given the fastvotes plugin is loaded with the "participation" strategy
    And player "Alice" is connected
    And player "Bob" is connected
    And player "Carol" is connected
    And player "Dave" is connected
    And a "map" vote is running with 2 yes and 0 no votes
    When Alice votes yes
    Then the vote is passed immediately

  Scenario: A vote fails when enough players voted and no leads
    Given the fastvotes plugin is loaded with the "participation" strategy
    And player "Alice" is connected
    And player "Bob" is connected
    And player "Carol" is connected
    And player "Dave" is connected
    And a "kick" vote is running with 0 yes and 2 no votes
    When Alice votes no
    Then the vote is failed immediately

  Scenario: A vote waits while too few players voted
    Given the fastvotes plugin is loaded with the "participation" strategy
    And player "Alice" is connected
    And player "Bob" is connected
    And player "Carol" is connected
    And player "Dave" is connected
    And a "map" vote is running with 1 yes and 0 no votes
    When Alice votes yes
    Then the vote is left running

  Scenario: A draw is not decided even if everybody voted
    Given the fastvotes plugin is loaded with the "participation" strategy
    And player "Alice" is connected
    And player "Bob" is connected
    And player "Carol" is connected
    And player "Dave" is connected
    And a "map" vote is running with 1 yes and 2 no votes
    When Alice votes yes
    Then the vote is left running
