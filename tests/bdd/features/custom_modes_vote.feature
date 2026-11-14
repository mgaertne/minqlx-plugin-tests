Feature: Switching the game mode between PQL and VQL

  The server runs with one set of game settings at a time. Admins switch it with !mode, players by calling a
  vote, and every new map starts in the default mode again.

  Background:
    Given the custom_modes_vote plugin is loaded with "vql" as the default mode
    And nobody but the owner has admin rights
    And player "Alice" is connected
    And player "Bob" is connected
    And Bob is the server owner

  Scenario: The owner switches the mode
    When Bob types "!mode pql"
    Then the server console is set to "dmflags 60"
    And everybody is told "PQL settings loaded!"

  Scenario: An unknown mode only shows the usage
    When Bob types "!mode turbo"
    Then the channel is told the usage of the command
    And the server console is not changed

  Scenario: Players cannot switch the mode themselves
    When Alice types "!mode pql"
    Then the server console is not changed

  Scenario: A new map starts in the default mode again
    Given the server runs in "pql" mode
    When a new map is loaded
    Then the server console is set to "dmflags 28"
    And everybody is told "VQL settings loaded!"

  Scenario: A player calls a vote for another mode
    When Alice calls the vote "mode pql"
    Then the vote is taken over by the plugin
    And Alice votes yes for it
    And everybody is told "Alice^7 called a vote."

  Scenario: Voting for the mode that is already running is stopped
    When Alice calls the vote "mode vql"
    Then the vote is taken over by the plugin
    And no vote is started

  Scenario: Votes for other things are left alone
    When Alice calls the vote "map campgrounds ca"
    Then the vote is passed on to the server
    And no vote is started

  Scenario: A passed mode vote switches the mode
    Given a vote "mode pql" is running
    When the vote passes
    Then the server console is set to "dmflags 60"

  Scenario: A failed mode vote changes nothing
    Given a vote "mode pql" is running
    When the vote fails
    Then the server console is not changed
