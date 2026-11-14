Feature: Asking when a map was last played

  Players type !lastplayed to find out how long ago a map was on the server.

  Background:
    Given the last_played plugin is loaded
    And player "Alice" is connected
    And a game on "campgrounds" is in progress

  Scenario: The server has never seen the map
    When Alice types "!lastplayed thunderstruck"
    Then the channel is told "I don't know when map ^3thunderstruck^7 was played the last time."

  Scenario: The map was played, but Alice never played on it
    Given the map "thunderstruck" was last played 2 hours ago
    When Alice types "!lastplayed thunderstruck"
    Then the channel is told "Map ^3thunderstruck^7 was last played 2 hours ago here."

  Scenario: Without a map name the current map is meant
    Given the map "campgrounds" was last played 3 hours ago
    When Alice types "!lastplayed"
    Then the channel is told "Map ^3campgrounds^7 was last played 3 hours ago here."

  Scenario: Alice was there when the map was last played
    Given the map "thunderstruck" was last played 2 hours ago
    And Alice played "thunderstruck" 2 hours ago
    When Alice types "!lastplayed thunderstruck"
    Then the channel is told "Map ^3thunderstruck^7 was last played 2 hours ago here. So did you."

  Scenario: Alice played on the map before somebody else did
    Given the map "thunderstruck" was last played 2 hours ago
    And Alice played "thunderstruck" 3 days ago
    When Alice types "!lastplayed thunderstruck"
    Then the channel is told "Map ^3thunderstruck^7 was last played 2 hours ago here. You played on it 3 days ago."

  Scenario: Nothing is said without a running game
    Given no game is running
    When Alice types "!lastplayed thunderstruck"
    Then the channel is not told anything
