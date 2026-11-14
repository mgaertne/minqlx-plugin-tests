Feature: Letting a showdown run until the round ends

  A minimum of zero opponents turns the early restoring of the weapons off. The weapons are handed back with the next
  round, and the last opponents are announced one by one.

  Background:
    Given the showdown plugin is loaded with the random weapons "gl" and no early restoring
    And a game on "campgrounds" is in progress
    And player "Alice" is connected
    And player "Bob" is connected
    And player "Carol" is connected
    And player "Dave" is connected
    And player "Eve" is connected
    And round 1 has started
    And Alice is alive on the "red" team
    And Bob is alive on the "red" team
    And Carol is alive on the "blue" team
    And Dave is alive on the "blue" team
    And Eve is alive on the "blue" team
    And 2 more living players are on the blue team
    And the dice favour a showdown

  Scenario: The showdown promises the weapons back with the next round
    When Bob dies
    Then everybody is told "^7Nade showdown! Weapons will be restored next round."

  Scenario: The enemies are counted down to the last one
    Given Bob died
    And the countdown is over
    When Carol dies
    Then everybody is told "^7Nade showdown! Kill ^64^7 more enemies"

  Scenario: The weapons stay while the opponents are killed one by one
    Given Bob died
    And the countdown is over
    And Carol died
    And Dave died
    When Eve dies
    Then the countdown announces "2 blues left!"
    And the weapons are not restored

  Scenario: The last opponent is announced
    Given Bob died
    And the countdown is over
    And Carol died
    And Dave died
    And Eve died
    When one of the extra players dies
    Then the countdown announces "1 blue left!"
    And the weapons are not restored
