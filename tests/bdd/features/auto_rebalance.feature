Feature: Balancing the teams when players join and when a team dominates

  Players joining a running match are placed so that the teams stay as even as possible by rating. When one team
  dominates a round-based match, the balance plugin is asked for a suggestion.

  Background:
    Given the auto_rebalance plugin is loaded
    And a game on "campgrounds" is in progress
    And player "Alice" is connected
    And player "Bob" is connected
    And player "Carol" is connected
    And player "Dave" is connected

  Scenario: The first newcomer joins even teams without interference
    Given Alice is on the "red" team with a rating of 2000
    And Bob is on the "blue" team with a rating of 1000
    And Carol is a spectator with a rating of 2000
    When Carol tries to join the "red" team
    Then the join is allowed

  Scenario: Two newcomers who would unbalance the teams are swapped
    Given Alice is on the "red" team with a rating of 2000
    And Bob is on the "blue" team with a rating of 1000
    And Carol is a spectator with a rating of 2000
    And Dave is a spectator with a rating of 1000
    And Carol joined the "red" team
    When Dave tries to join the "any" team
    Then Carol gets the message "Carol, you have been moved to ^4blue^7 to maintain team balance."
    And Carol is put on the "blue" team
    And Dave is put on the "red" team
    And the join is stopped

  Scenario: The second newcomer asking for the team of the first one keeps it
    Given Alice is on the "red" team with a rating of 2000
    And Bob is on the "blue" team with a rating of 1000
    And Carol is a spectator with a rating of 2000
    And Dave is a spectator with a rating of 1000
    And Carol joined the "red" team
    When Dave tries to join the "red" team
    Then Carol is put on the "blue" team
    And the join is allowed

  Scenario: The second newcomer asking for the other team is moved and told
    Given Alice is on the "red" team with a rating of 2000
    And Bob is on the "blue" team with a rating of 1000
    And Carol is a spectator with a rating of 2000
    And Dave is a spectator with a rating of 1000
    And Carol joined the "red" team
    When Dave tries to join the "blue" team
    Then Dave gets the message "Dave, you have been moved to ^1red^7 to maintain team balance."
    And Dave is put on the "red" team
    And the join is stopped

  Scenario: Newcomers who fit together are left alone
    Given Alice is on the "red" team with a rating of 2000
    And Bob is on the "blue" team with a rating of 1000
    And Carol is a spectator with a rating of 1000
    And Dave is a spectator with a rating of 2000
    And Carol joined the "red" team
    When Dave tries to join the "any" team
    Then the join is allowed

  Scenario: A newcomer who would unbalance the teams is sent to the other team
    Given Alice is on the "red" team with a rating of 2000
    And Bob is on the "blue" team with a rating of 1000
    And Carol is a spectator with a rating of 1000
    And Dave is a spectator with a rating of 2000
    And Carol joined the "red" team
    When Dave tries to join the "red" team
    Then Dave is put on the "blue" team
    And the join is stopped

  Scenario: A newcomer from an earlier round is not rebalanced
    Given Alice is on the "red" team with a rating of 2000
    And Bob is on the "blue" team with a rating of 1000
    And Carol is a spectator with a rating of 2000
    And Dave is a spectator with a rating of 1000
    And Carol joined the "red" team
    And a new round starts
    When Dave tries to join the "any" team
    Then the join is allowed

  Scenario: Nothing is rebalanced during warmup
    Given a game on "campgrounds" is in warmup
    And Alice is on the "red" team with a rating of 2000
    And Bob is on the "blue" team with a rating of 1000
    And Carol is a spectator with a rating of 2000
    And Dave is a spectator with a rating of 1000
    And Carol joined the "red" team
    When Dave tries to join the "any" team
    Then the join is allowed

  Scenario: Without the balance plugin the server is told
    Given the balance plugin is not loaded
    And Alice is on the "red" team with a rating of 2000
    And Carol is a spectator with a rating of 2000
    When Carol tries to join the "red" team
    Then the join is allowed
    And everybody is told "^1balance^7 plugin not loaded, ^1auto rebalance^7 not possible."

  Scenario: A lead of three rounds asks the balance plugin for a suggestion
    Given Alice is on the "red" team with a rating of 2000
    And Bob is on the "blue" team with a rating of 1000
    And the score is red 3, blue 0
    When the "red" team wins a round
    Then the balance plugin is asked to suggest a rebalance

  Scenario: A small lead does not need a suggestion
    Given Alice is on the "red" team with a rating of 2000
    And Bob is on the "blue" team with a rating of 1000
    And the score is red 2, blue 1
    When the "red" team wins a round
    Then the balance plugin is not asked

  Scenario: Three won rounds in a row ask for a suggestion even with a small lead
    Given Alice is on the "red" team with a rating of 2000
    And Bob is on the "blue" team with a rating of 1000
    And the score is red 3, blue 2
    And the "red" team won 2 rounds
    When the "red" team wins a round
    Then the balance plugin is asked to suggest a rebalance

  Scenario: Uneven teams do not get a suggestion
    Given Alice is on the "red" team with a rating of 2000
    And Bob is on the "red" team with a rating of 1000
    And Carol is on the "blue" team with a rating of 1500
    And the score is red 3, blue 0
    When the "red" team wins a round
    Then the balance plugin is not asked

  Scenario: A decided match does not get a suggestion
    Given Alice is on the "red" team with a rating of 2000
    And Bob is on the "blue" team with a rating of 1000
    And the score is red 8, blue 0
    When the "red" team wins a round
    Then the balance plugin is not asked
