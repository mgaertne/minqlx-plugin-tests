Feature: Duel arena with three players

  With exactly three players, clan arena turns into a duel: two play, the third waits, and the round loser rotates
  with the waiting player. The mode ends when the group size no longer fits.

  Background:
    Given a game on "campgrounds" is in warmup
    And player "Alice" is connected
    And player "Bob" is connected
    And player "Carol" is connected
    And player "Dave" is connected
    And Alice is on the "red" team
    And Bob is on the "blue" team
    And Carol is on the "spectator" team
    And Dave is on the "spectator" team

  Scenario: The third player activates the duel arena in warmup
    Given the duelarena plugin is loaded
    When Carol tries to join the "red" team
    Then everybody is told "DuelArena activated! Round winner stays in, loser rotates with spectator. Hit 8 rounds first to win!"
    And everybody is told "Ready up for ^6DuelArena^7!"

  Scenario: Two players are no duel arena
    Given the duelarena plugin is loaded
    When Bob tries to join the "blue" team
    Then everybody is not told "Ready up for ^6DuelArena^7!"

  Scenario: The round loser rotates with the waiting player
    Given a duel arena match is running with Alice against Bob and Carol waiting
    And the score is red 1, blue 0
    When the "red" team wins a round
    Then Carol is put on the "blue" team
    And Bob is put on the "spectator" team
    And Bob gets the message "Bob, you've been put back to DuelArena queue. Prepare for your next duel!"

  Scenario: The next duel is announced before the round
    Given a duel arena match is running with Alice against Bob and Carol waiting
    When the next round is about to start
    Then everybody is told "DuelArena: Alice ^2vs^7 Bob"

  Scenario: A leaving duelist is replaced by the waiting player
    Given a duel arena match is running with Alice against Bob and Carol waiting
    When Alice disconnects
    Then Carol is put on the "red" team
    And everybody is told "DuelArena has been deactivated!"

  Scenario: A fourth player ends the duel arena
    Given a duel arena match is running with Alice against Bob and Carol waiting
    When Dave tries to join the "red" team
    Then everybody is told "DuelArena has been deactivated!"
    And the join is allowed

  Scenario: A spectator joins the duel arena queue
    Given a duel arena match is running with Alice against Bob and Carol waiting
    When Dave types "!join"
    Then Dave gets the message "You successfully joined the DuelArena queue. Prepare for your duel!"
    And everybody is told "^7Dave joined DuelArena!"

  Scenario: The results are printed when the match ends
    Given a duel arena match is running with Alice against Bob and Carol waiting
    When the match ends with 5 to 3
    Then everybody is told "DuelArena results:"
    And everybody is told "Place ^31.^7 Alice ^7(Wins:^25^7)"
    And everybody is told "Place ^32.^7 Bob ^7(Wins:^23^7)"
    And everybody is told "Place ^33.^7 Carol ^7(Wins:^20^7)"

  Scenario: An aborted match prints no results
    Given a duel arena match is running with Alice against Bob and Carol waiting
    When the match is aborted
    Then everybody is not told "DuelArena results:"
