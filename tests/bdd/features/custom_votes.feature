Feature: Custom call votes

  Players can call votes the game does not know: damage through floors, moving a player to the spectators, muting a
  player and readying up everybody. The plugin takes the vote over, starts it as the server and votes yes for the caller.

  Background:
    Given the custom_votes plugin is loaded
    And a game on "campgrounds" is in warmup
    And player "Alice" is connected
    And player "Bob" is connected
    And player "Carol" is connected
    And Alice is on the "red" team
    And Bob is on the "blue" team
    And Carol is on the "red" team

  Scenario: Damage through floors can be switched off
    When Alice calls the vote "thrufloors off"
    Then the vote "g_forceDmgThroughSurface 0" is started as "Turn off damage through floors?"
    And Alice votes yes for it
    And everybody is told "Alice^7 called a vote."
    And the vote is taken over by the plugin

  Scenario: Damage through floors can be switched on
    When Alice calls the vote "thrufloors on"
    Then the vote "g_forceDmgThroughSurface 1" is started as "Turn on damage through floors?"
    And Alice votes yes for it
    And the vote is taken over by the plugin

  Scenario: The thrufloors vote needs on or off
    When Alice calls the vote "thrufloors maybe"
    Then Alice is told "^2/cv thrufloors [on/off]^7 is the usage for this callvote command."
    And no vote is started
    And the vote is taken over by the plugin

  Scenario: A player can be voted into the spectators by name
    When Alice calls the vote "spec Bob"
    Then the vote "put 1 spec" is started as "spec Bob^7?"
    And Alice votes yes for it
    And everybody is told "Alice^7 called a vote."
    And the vote is taken over by the plugin

  Scenario: A player can be voted into the spectators by Steam ID
    When Alice calls the vote "spec 456"
    Then the vote "put 1 spec" is started as "spec Bob^7?"

  Scenario: Players who are already spectators cannot be voted into the spectators
    Given Bob is on the "spectator" team
    When Alice calls the vote "spec Bob"
    Then Alice is told "Player Bob^7 is already in the spectators."
    And no vote is started
    And the vote is taken over by the plugin

  Scenario: Nobody matching the name is reported
    When Alice calls the vote "spec Zoe"
    Then Alice is told "Sorry, but no players matched your tokens: Zoe."
    And no vote is started
    And the vote is taken over by the plugin

  Scenario: Several matching players are listed
    When Alice calls the vote "spec a"
    Then Alice is told "A total of ^62^7 players matched for a:"
    And Alice is told "  0^6:^7 Alice\n  2^6:^7 Carol"
    And no vote is started
    And the vote is taken over by the plugin

  Scenario: A player can be call-voted silent
    When Alice calls the vote "mute Bob"
    Then the vote "qlx !silence 1 10 minutes You were call-voted silent for 10 minutes.;mute 1" is started as "Mute Bob^7 for 10 minutes?"
    And Alice votes yes for it
    And everybody is told "Alice^7 called a vote."

  Scenario: Muting somebody unknown is reported
    When Alice calls the vote "mute Zoe"
    Then Alice is told "Sorry, but no players matched your tokens: Zoe."
    And no vote is started

  Scenario: Everybody can be readied up during the warmup
    When Alice calls the vote "allready"
    Then the vote "qlx !allready" is started as "Ready all players?"
    And Alice votes yes for it
    And the vote is taken over by the plugin

  Scenario: Nobody can be readied up once the match is running
    Given a game on "campgrounds" is in progress
    When Alice calls the vote "allready"
    Then Alice is told "The game is already in progress."
    And no vote is started
    And the vote is taken over by the plugin

  Scenario: Spectators are told when they may not call votes
    Given spectators are not allowed to call votes
    And Alice is on the "spectator" team
    When Alice calls the vote "thrufloors off"
    Then Alice is told "You are not allowed to call a vote as spectator."
    And no vote is started
    And the vote is passed on to the server

  Scenario: Spectators may call votes when the server allows it
    Given Alice is on the "spectator" team
    When Alice calls the vote "thrufloors off"
    Then the vote "g_forceDmgThroughSurface 0" is started as "Turn off damage through floors?"

  Scenario: A running vote is left alone
    Given a vote "kick Bob" is running
    When Alice calls the vote "thrufloors off"
    Then no vote is started
    And the vote is passed on to the server

  Scenario: Votes of the game are left alone
    When Alice calls the vote "map campgrounds"
    Then no vote is started
    And the vote is passed on to the server
