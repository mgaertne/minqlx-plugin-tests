Feature: Starting the match automatically after the warmup

  Once enough players are on the server and in a team, a countdown starts that readies everybody up when it runs
  out. It pauses over a map change, stops when too many players leave, and can forbid readying up by hand.

  Background:
    Given the autoready plugin is loaded with a minimum of 4 players, a delay of 180 seconds and 30 seconds at least
    And a game on "campgrounds" is in warmup
    And player "Alice" is connected
    And player "Bob" is connected
    And player "Carol" is connected
    And player "Dave" is connected

  Scenario: Enough players in teams start the countdown
    When Alice joins the "red" team
    Then a countdown of 180 seconds is running

  Scenario: Too few players do not start a countdown
    Given Dave disconnected
    When Alice joins the "red" team
    Then no countdown is running

  Scenario: Joining the spectators does not start a countdown
    When Alice joins the "spectator" team
    Then no countdown is running

  Scenario: No countdown is started once the match is running
    Given a game on "campgrounds" is in progress
    When Alice joins the "red" team
    Then no countdown is running

  Scenario: A running countdown is not started a second time
    Given Alice joined the "red" team
    When Bob joins the "blue" team
    Then exactly 1 countdown was started

  Scenario: The countdown is cancelled when too many players leave
    Given Alice joined the "red" team
    When Dave disconnects
    Then no countdown is running

  Scenario: The countdown is cleared when the match starts
    Given Alice joined the "red" team
    When the match starts
    Then no countdown is running

  Scenario: The countdown keeps at least 30 seconds when the game is about to start
    Given Alice joined the "red" team
    When the game is about to start
    Then a countdown of 30 seconds is running

  Scenario: A player who is still loading is put back to the spectators when the game is about to start
    Given Alice joined the "red" team
    And Dave is still loading on the "red" team
    When the game is about to start
    Then Dave is put on the "spectator" team

  Scenario: The remaining time is kept over a map change
    Given Alice joined the "red" team
    And the countdown has 100 seconds left
    And the map changes
    When Bob joins the "blue" team
    Then a countdown of 100 seconds is running

  Scenario: Little remaining time is raised to 30 seconds after a map change
    Given Alice joined the "red" team
    And the countdown has 10 seconds left
    And the map changes
    When Bob joins the "blue" team
    Then a countdown of 30 seconds is running

  Scenario: Players can ready up by hand when that is allowed
    When Alice sends the client command "readyup"
    Then the command is passed on

  Scenario: Readying up by hand can be forbidden
    Given readying up by hand is forbidden
    When Alice sends the client command "readyup"
    Then the command is blocked

  Scenario: Other client commands are not blocked when readying up is forbidden
    Given readying up by hand is forbidden
    When Alice sends the client command "team spectator"
    Then the command is passed on

  Scenario: Readying up is allowed while too few players are connected
    Given readying up by hand is forbidden
    And Dave disconnected
    When Alice sends the client command "readyup"
    Then the command is passed on
