Feature: Limiting the application games of low-rated players

  Players below the minimum rating may play a limited number of application games within a period. They are warned
  while games are left, kicked when they used them all, and admins can grant another game.

  Background:
    Given the merciful_elo_limit plugin is loaded with a minimum rating of 800 and 10 application games
    And a game on "campgrounds" is in progress
    And player "Alice" is connected
    And player "Bob" is connected
    And Alice has permission 1
    And Bob has permission 2

  Scenario: A low-rated player who used some application games is warned
    Given the balance plugin rates Alice with 700
    And Alice used 2 application games
    When Alice has loaded
    Then Alice is warned that 8 of 10 application games are left
    And everybody is told "Alice is below 800, but has ^38^7 application matches left."

  Scenario: A low-rated player without a started application game is not warned yet
    Given the balance plugin rates Alice with 700
    When Alice has loaded
    Then Alice is not told anything

  Scenario: A player above the limit is not warned
    Given the balance plugin rates Alice with 1500
    And Alice used 2 application games
    When Alice has loaded
    Then Alice is not told anything

  Scenario: A low-rated player who used all application games is kicked
    Given the balance plugin rates Alice with 700
    And Alice used 10 application games
    And Alice is fully connected
    When Alice has loaded
    Then Alice is kicked for using up the 10 application games

  Scenario: A low-rated player starts an application game with the round
    Given the balance plugin rates Alice with 700
    And Alice plays for the "red" team
    When a round starts
    Then an application game is recorded for Alice

  Scenario: A player above the limit does not use up application games
    Given the balance plugin rates Alice with 1500
    And Alice plays for the "red" team
    When a round starts
    Then no application game is recorded for Alice

  Scenario: Nobody is within the application period
    Given the balance plugin rates Alice with 1500
    When Alice types "!mercis"
    Then the channel is told "There is currently no player within their application period connected."

  Scenario: Players within the application period are listed
    Given the balance plugin rates Alice with 700
    And Alice used 3 application games
    When Alice types "!mercis"
    Then the channel is told "Players currently within their application period:"
    And the channel is told "Alice (elo: 700): ^37^7 application matches left"

  Scenario: An admin grants another application game
    Given Alice used 3 application games
    When Bob types "!merci Alice"
    Then the last application game of Alice is removed
    And the channel is told "Alice^7 has been granted another application game"

  Scenario: Granting a game needs a player to be named
    When Bob types "!merci"
    Then the channel is told the usage of the command

  Scenario: Granting a game to an unknown player tells who could not be found
    When Bob types "!merci Dave"
    Then Bob is told "Sorry, but no players matched your tokens: Dave."

  Scenario: Players below admin level cannot grant games
    Given Alice used 3 application games
    When Alice types "!merci Alice"
    Then the channel is not told anything
