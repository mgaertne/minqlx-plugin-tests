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

  Scenario Outline: Another round time limit moves the warning
    Given the round time limit is <limit> seconds
    When a round starts
    And 30 seconds are left in the round
    Then the warning waited <wait> seconds

    Examples:
      | limit | wait |
      | 180   | 150  |
      | 90    | 60   |

  Scenario Outline: The announcer can be chosen and falls back to the standard one
    Given the announcer "<announcer>" is chosen
    When a round starts
    And 30 seconds are left in the round
    Then the announcer plays "<sound>"

    Examples:
      | announcer | sound                                 |
      | female    | sound/vo_female/30_second_warning.ogg |
      | robot     | sound/vo/30_second_warning.ogg        |

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

  Scenario Outline: Only a timeout during the round cancels the warning
    Given <timeout>
    When a round starts
    And 30 seconds are left in the round
    Then <outcome>

    Examples:
      | timeout                                  | outcome                                                |
      | a timeout was called during the round    | nothing is announced                                   |
      | a timeout ended after the round started  | nothing is announced                                   |
      | a timeout ended before the round started | the announcer plays "sound/vo/30_second_warning.ogg"   |

  Scenario: The start of the match cancels a pending warning
    When a round starts
    And the match starts
    And 30 seconds are left in the round
    Then nothing is announced
