Feature: Deciding a clan arena round with a showdown

  If a single player is left alive against a crowd, the plugin strips everybody of their weapons and lets the
  survivors fight with one weapon, until only a few opponents are left. Admins and players with the right permission
  can start a showdown by hand.

  Background:
    Given the showdown plugin is loaded with the random weapons "gl"
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

  Scenario: A crowd against the last standing player triggers a showdown
    Given 2 more living players are on the blue team
    And the dice favour a showdown
    When Bob dies
    Then everybody is told "^7Nade showdown! Weapons will be restored when ^63^7 players are left standing."
    And Alice is stripped of all weapons
    And Carol is stripped of all weapons
    And Bob is left untouched
    And the sound "sound/world/turksquish22.wav" is played

  Scenario Outline: The more players are alive, the more likely the showdown is
    Given <more> more living players are on the blue team
    And the dice roll <roll>
    When Bob dies
    Then <outcome>

    Examples: Five players alive
      | more | roll | outcome                      |
      | 1    | 5    | a showdown is announced      |
      | 1    | 6    | no showdown is announced     |

    Examples: Six to eight players alive
      | more | roll | outcome                      |
      | 2    | 10   | a showdown is announced      |
      | 2    | 11   | no showdown is announced     |
      | 3    | 15   | a showdown is announced      |
      | 3    | 16   | no showdown is announced     |
      | 4    | 20   | a showdown is announced      |
      | 4    | 21   | no showdown is announced     |

    Examples: More players alive
      | more | roll | outcome                      |
      | 5    | 25   | a showdown is announced      |
      | 5    | 26   | no showdown is announced     |

  Scenario: A small group of opponents is no reason for a showdown
    Given the dice favour a showdown
    When Bob dies
    Then no showdown is announced

  Scenario: Two living players on each side are no reason for a showdown
    Given 2 more living players are on the blue team
    And the dice favour a showdown
    When Carol dies
    Then no showdown is announced

  Scenario: A team with a single player is too small for a showdown
    Given Bob is a spectator
    And 2 more living players are on the blue team
    And the dice favour a showdown
    When Carol dies
    Then no showdown is announced

  Scenario: A skipped showdown is not rolled again in the same round
    Given 2 more living players are on the blue team
    And the dice skip the showdown
    And Bob died
    And the dice favour a showdown
    When Carol dies
    Then no showdown is announced

  Scenario: A new round rolls the dice again
    Given 2 more living players are on the blue team
    And the dice skip the showdown
    And Bob died
    And the round ended
    And round 2 has started
    And Bob is alive on the "red" team
    And the dice favour a showdown
    When Bob dies
    Then a showdown is announced

  Scenario: Nothing happens between the rounds
    Given 2 more living players are on the blue team
    And the dice favour a showdown
    And the round ended
    When Bob dies
    Then no showdown is announced

  Scenario: Nothing happens in the warmup
    Given a game on "campgrounds" is in warmup
    And 2 more living players are on the blue team
    And the dice favour a showdown
    When Bob dies
    Then no showdown is announced

  Scenario: Nothing happens in other game types
    Given a "ft" game on "campgrounds" is in progress
    And 2 more living players are on the blue team
    And the dice favour a showdown
    When Bob dies
    Then no showdown is announced

  Scenario: Nothing happens without a game
    Given no game is running
    And 2 more living players are on the blue team
    And the dice favour a showdown
    When Bob dies
    Then no showdown is announced

  Scenario: Nothing happens on match point
    Given the blue team has 8 points
    And 2 more living players are on the blue team
    And the dice favour a showdown
    When Bob dies
    Then no showdown is announced

  Scenario: Leaving to the spectators counts like a death
    Given Eve is dead on the "red" team
    And 3 more living players are on the blue team
    And the dice favour a showdown
    When Bob switches to the "spectator" team
    Then a showdown is announced

  Scenario: Joining a team does not start a showdown
    Given Eve is a spectator
    And Bob is dead on the "red" team
    And 3 more living players are on the blue team
    And the dice favour a showdown
    When Eve joins the "blue" team
    Then no showdown is announced

  Scenario: The countdown announces the weapon and the sides
    Given 2 more living players are on the blue team
    And the dice favour a showdown
    And Bob died
    When the countdown is over
    Then the countdown announces "Lube your nades..."
    And the countdown announces "^21vs5 - Go nading!"

  Scenario: The weapon is handed out when the countdown is over
    Given 2 more living players are on the blue team
    And the dice favour a showdown
    And Bob died
    When the countdown is over
    Then Alice wields the "gl" with haste
    And Carol wields the "gl" with haste
    And the server console runs "g_friendlyfire 1"
    And the sound "sound/vo_evil/go" is played
    And the sound "sound/gaunt_showdown/yakety_sax" is played

  Scenario: No music is played on match point of the other team
    Given the blue team has 7 points
    And 2 more living players are on the blue team
    And the dice favour a showdown
    And Bob died
    When the countdown is over
    Then the sound "sound/gaunt_showdown/yakety_sax" is not played

  Scenario: Players who are dead get no weapon
    Given 2 more living players are on the blue team
    And the dice favour a showdown
    And Bob died
    When the countdown is over
    Then Bob is left untouched

  Scenario: The last standing player may get a kamikaze
    Given 2 more living players are on the blue team
    And the dice favour a showdown
    And the kamikaze roll succeeds
    When Bob dies
    Then Alice holds a kamikaze
    And Carol holds no kamikaze

  Scenario: Every death in the showdown is announced
    Given 2 more living players are on the blue team
    And the dice favour a showdown
    And Bob died
    And the countdown is over
    When Carol dies
    Then everybody is told "^7Nade showdown! Kill ^62^7 more enemies to restore weapons"
    And the countdown announces "4 blues left!"

  Scenario: Deaths during the countdown are not announced
    Given 2 more living players are on the blue team
    And the dice favour a showdown
    And the countdown is held up
    And Bob died
    When Carol dies
    Then everybody is not told "^7Nade showdown! Kill ^62^7 more enemies to restore weapons"

  Scenario: A pummel showdown humiliates the opponents
    Given Alice is an admin
    And Bob is dead on the "red" team
    And 2 more living players are on the blue team
    And Alice typed "!showdown g"
    And the countdown is over
    When Carol dies
    Then the sound "sound/vo/humiliation1" is played

  Scenario: The weapons are restored when few opponents are left
    Given 2 more living players are on the blue team
    And the dice favour a showdown
    And Bob died
    And the countdown is over
    And Carol died
    And Dave died
    When Eve dies
    Then Alice is stripped of all weapons
    And the server console runs "g_guidedRocket 0"
    And the sounds are stopped
    And the countdown announces "^3Restoring weapons in 5"

  Scenario: Everybody gets the weapons back when the restoring countdown is over
    Given 2 more living players are on the blue team
    And the dice favour a showdown
    And Bob died
    And the countdown is over
    And Carol died
    And Dave died
    And Eve died
    When the countdown is over
    Then the countdown announces "^2FIGHT!"
    And Alice gets her weapons back
    And the server console runs "g_friendlyfire 0"
    And the sound "sound/vo_evil/fight" is played

  Scenario: The showdown ends with the round
    Given 2 more living players are on the blue team
    And the dice favour a showdown
    And Bob died
    And the countdown is over
    When the round ends
    Then the server console runs "g_friendlyfire 0"
    And the server console runs "g_guidedRocket 0"
    And the dropped items are removed
    And the sounds are stopped

  Scenario: The music goes on when the last round ends
    Given 2 more living players are on the blue team
    And the dice favour a showdown
    And Bob died
    And the countdown is over
    And the blue team has 8 points
    When the round ends
    Then the sounds are not stopped

  Scenario: The time the last player stood alone is recorded
    Given the clock shows noon on the 15th of June 2025
    And Bob died
    And 40 seconds passed
    When the round ends
    Then the database records that Alice stood alone for 40 seconds when the round ended at 12:00:40

  Scenario: Only the first moment of standing alone counts
    Given the clock shows noon on the 15th of June 2025
    And Bob died
    And 10 seconds passed
    And Carol died
    And 30 seconds passed
    When the round ends
    Then the database records that Alice stood alone for 40 seconds when the round ended at 12:00:40

  Scenario Outline: The record is stored with every version of the Redis driver
    Given the clock shows noon on the 15th of June 2025
    And the Redis driver has the version <version>
    And Bob died
    And 40 seconds passed
    When the round ends
    Then the database records that Alice stood alone for 40 seconds when the round ended at 12:00:40

    Examples:
      | version |
      | 2.10.6  |
      | 3.0.0   |
      | 5.0.0   |

  Scenario: An admin starts a showdown by hand
    Given Alice is an admin
    When Alice types "!showdown rl"
    Then everybody is told "^7Guided Rocket showdown! Weapons will be restored when ^63^7 players are left standing."

  Scenario: A guided rocket showdown allows guided rockets
    Given Alice is an admin
    And Alice typed "!showdown rl"
    When the countdown is over
    Then the server console runs "g_guidedRocket 1"

  Scenario Outline: A weapon is found by its short name, its long name or its alias
    Given Alice is an admin
    When Alice types "!showdown <argument>"
    Then everybody is told "^7<weapon> showdown! Weapons will be restored when ^63^7 players are left standing."

    Examples:
      | argument  | weapon        |
      | g         | Pummel        |
      | gauntlet  | Pummel        |
      | GRENADE   | Nade          |
      | mines     | Mining        |
      | chaingun  | Chain         |
      | random    | Nade          |

  Scenario: An unknown weapon is answered with the available ones
    Given Alice is an admin
    When Alice types "!showdown banana"
    Then Alice is told "Weapon ^5banana^7 not available. Available weapons: ^5bfg^7, ^5cg^7, ^5g^7, ^5gh^7, ^5gl^7, ^5hmg^7, ^5lg^7, ^5mg^7, ^5ng^7, ^5pg^7, ^5pl^7, ^5random^7, ^5rg^7, ^5rl^7, ^5sg"
    And no showdown is announced

  Scenario: A player with the permission level may start a showdown
    Given Bob has the permission level 1
    When Bob types "!showdown rl"
    Then everybody is told "^7Guided Rocket showdown! Weapons will be restored when ^63^7 players are left standing."

  Scenario: Players without the permission cannot start a showdown
    When Bob types "!showdown rl"
    Then no showdown is announced

  Scenario: A showdown by hand needs a running match
    Given Alice is an admin
    And a game on "campgrounds" is in warmup
    When Alice types "!showdown rl"
    Then no showdown is announced

  Scenario: A showdown by hand is not possible between the rounds
    Given Alice is an admin
    And the round ended
    When Alice types "!showdown rl"
    Then no showdown is announced

  Scenario: A running showdown cannot be started a second time
    Given Alice is an admin
    And Alice typed "!showdown rl"
    When Alice types "!showdown gl"
    Then everybody is told "^7Guided Rocket showdown! Weapons will be restored when ^63^7 players are left standing."

  Scenario: A showdown needs living players on both teams
    Given Alice is an admin
    And Carol is dead on the "blue" team
    And Dave is dead on the "blue" team
    And Eve is dead on the "blue" team
    When Alice types "!showdown rl"
    Then no showdown is announced
