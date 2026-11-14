Feature: Announcing the last 30 seconds of a round

  In clan arena, the announcer warns 30 seconds before the round time limit runs out, unless the round ended earlier
  or a timeout interrupted it.

  Background:
    Given the thirtysecwarn plugin is loaded with a round time limit of 150 seconds
    And a game on "campgrounds" is in progress

  Scenario: The warning comes 30 seconds before the round time limit
    When a round starts
    And 30 seconds are left in the round
    Then the announcer plays "sound/vo/30_second_warning.ogg"
    And the warning waited 120 seconds

  Scenario: A longer round time limit moves the warning
    Given the round time limit is 180 seconds
    When a round starts
    And 30 seconds are left in the round
    Then the warning waited 150 seconds

  Scenario: The female announcer can be chosen
    Given the announcer "female" is chosen
    When a round starts
    And 30 seconds are left in the round
    Then the announcer plays "sound/vo_female/30_second_warning.ogg"

  Scenario: An unknown announcer falls back to the standard one
    Given the announcer "robot" is chosen
    When a round starts
    And 30 seconds are left in the round
    Then the announcer plays "sound/vo/30_second_warning.ogg"

  Scenario: A round that ended early gets no warning
    When a round starts
    And the round ends
    And 30 seconds are left in the round
    Then nothing is announced

  Scenario: Only the round that is running gets a warning
    When a round starts
    And the round ends
    And a round starts
    And 30 seconds are left in the round
    Then the announcer plays "sound/vo/30_second_warning.ogg" once

  Scenario: Other game types get no warning
    Given a game of type "ft" on "campgrounds" is in progress
    When a round starts
    And 30 seconds are left in the round
    Then nothing is announced

  Scenario: A timeout during the round cancels the warning
    Given a timeout was called during the round
    When a round starts
    And 30 seconds are left in the round
    Then nothing is announced

  Scenario: A timeout that ended before the round started does not matter
    Given a timeout ended before the round started
    When a round starts
    And 30 seconds are left in the round
    Then the announcer plays "sound/vo/30_second_warning.ogg"

  Scenario: A timeout that ended after the round started cancels the warning
    Given a timeout ended after the round started
    When a round starts
    And 30 seconds are left in the round
    Then nothing is announced

  Scenario: The start of the match cancels a pending warning
    When a round starts
    And the match starts
    And 30 seconds are left in the round
    Then nothing is announced
