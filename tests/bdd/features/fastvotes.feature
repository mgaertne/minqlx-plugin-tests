Feature: Deciding votes before the time is up

  Map and kick votes end as soon as the result is clear, depending on the strategy: either when one side leads by
  enough votes, or when enough connected players have voted and it is not a draw.

  Scenario Outline: Votes are decided by the lead with the threshold strategy
    Given the fastvotes plugin is loaded with the "threshold" strategy
    And player "Alice" is connected
    And a "<vote>" vote is running with <yes> yes and <no> no votes
    When Alice votes <answer>
    Then the vote is <outcome>

    Examples: Passing needs a lead of 6, failing a lead of 5
      | vote     | yes | no | answer | outcome            |
      | map      | 5   | 0  | yes    | passed immediately |
      | kick     | 0   | 4  | no     | failed immediately |

    Examples: Nothing is decided early
      | vote     | yes | no | answer | outcome      |
      | map      | 2   | 1  | yes    | left running |
      | teamsize | 5   | 0  | yes    | left running |

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

  Scenario Outline: Votes are decided by the participation with the participation strategy
    Given the fastvotes plugin is loaded with the "participation" strategy
    And player "Alice" is connected
    And player "Bob" is connected
    And player "Carol" is connected
    And player "Dave" is connected
    And a "<vote>" vote is running with <yes> yes and <no> no votes
    When Alice votes <answer>
    Then the vote is <outcome>

    Examples: Enough players voted and one side leads
      | vote | yes | no | answer | outcome            |
      | map  | 2   | 0  | yes    | passed immediately |
      | kick | 0   | 2  | no     | failed immediately |

    Examples: Too few players voted or it is a draw
      | vote | yes | no | answer | outcome      |
      | map  | 1   | 0  | yes    | left running |
      | map  | 1   | 2  | yes    | left running |
