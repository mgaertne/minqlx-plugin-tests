Feature: Frag statistics between players

  The plugin counts who fragged whom. !mapsoulz and !mapreaperz tell what happened on the current map, !soulz
  compares two players over all maps.

  Background:
    Given the frag_stats plugin is loaded
    And a game on "campgrounds" is in progress
    And player "Alice" is connected
    And player "Bob" is connected
    And player "Carol" is connected

  Scenario: Nobody has fragged anyone yet
    When Alice types "!mapsoulz"
    Then the channel is told "Alice^7 didn't reap any soulz, yet."

  Scenario: The victims are listed by how often they were fragged
    Given Alice fragged Bob
    And Alice fragged Carol
    And Alice fragged Bob
    When Alice types "!mapsoulz"
    Then the channel is told "Top 10 reaped soulz for Alice^7: Bob^7 (2), Carol^7 (1)"

  Scenario: The soulz of another player can be asked for by name
    Given Bob fragged Alice
    When Alice types "!mapsoulz Bob"
    Then the channel is told "Top 10 reaped soulz for Bob^7: Alice^7 (1)"

  Scenario: Reapers of a player are listed by how often they fragged them
    Given Alice fragged Bob
    And Carol fragged Bob
    And Carol fragged Bob
    When Bob types "!mapreaperz"
    Then the channel is told "Top 10 reaperz of Bob^7's soul: Carol^7 (2), Alice^7 (1)"

  Scenario: The environment can reap souls too
    Given Bob fell into the void
    When Bob types "!mapreaperz"
    Then the channel is told "Top 10 reaperz of Bob^7's soul: void^7 (1)"

  Scenario: Suicides are not counted
    Given Alice killed herself
    When Alice types "!mapsoulz"
    Then the channel is told "Alice^7 didn't reap any soulz, yet."

  Scenario: Switching teams is not a frag
    Given Bob switched teams
    When Bob types "!mapreaperz"
    Then the channel is told "Bob^7's soul was not reaped by anyone, yet."

  Scenario: The statistics start over with every game
    Given Alice fragged Bob
    When a new game is counting down
    And Alice types "!mapsoulz"
    Then the channel is told "Alice^7 didn't reap any soulz, yet."

  Scenario: Frags are kept in the database for the overall statistics
    When Alice fragged Bob
    Then the database counted Alice's soul of Bob once

  Scenario Outline: The overall statistics against another player tell who leads
    Given the database says Alice fragged Bob <alice_frags> times and Bob fragged Alice <bob_frags> times
    When Alice types "!soulz Bob"
    Then the channel is told "<message>"

    Examples:
      | alice_frags | bob_frags | message                                    |
      | 5           | 3         | Alice^7 leads by ^22^7 soulz vs. Bob^7 (5/3) |
      | 2           | 4         | Bob^7 leads by ^12^7 soulz vs. Alice^7 (4/2) |
      | 3           | 3         | Alice^7 is even with Bob^7 (3/3)           |
