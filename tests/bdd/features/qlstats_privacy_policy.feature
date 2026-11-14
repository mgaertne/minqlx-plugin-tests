Feature: Restricting the server to certain QLStats.net privacy settings

  Players whose QLStats.net privacy setting is not on the whitelist may not join the match. Admins can make
  exceptions or switch the check off.

  Background:
    Given the qlstats_privacy_policy plugin is loaded with the whitelist "public, anonymous" and 2 join attempts
    And nobody but the owner has admin rights
    And a game on "campgrounds" is in progress
    And player "Alice" is connected
    And player "Bob" is connected
    And Bob is the server owner

  Scenario: A player with an allowed privacy setting may join
    Given QLStats.net lists Alice with the privacy setting "public"
    When Alice tries to join the "red" team from spectators
    Then the join is allowed

  Scenario: A player with a private setting is stopped and warned
    Given QLStats.net lists Alice with the privacy setting "private"
    When Alice tries to join the "red" team from spectators
    Then the join is stopped
    And Alice is told "Not allowed to join due to ^6private^7 QLStats.net data. 1 join attempts before automatically kicking you."

  Scenario: A player without ratings yet has to wait
    When Alice tries to join the "red" team from spectators
    Then the join is stopped
    And Alice is told "We couldn't fetch your ratings, yet. You will not be able to join, until we did."

  Scenario: A player who keeps trying is kicked
    Given QLStats.net lists Alice with the privacy setting "private"
    When Alice tries to join the "red" team from spectators 3 times
    Then Alice is kicked

  Scenario: An admin can allow a player to join despite the privacy setting
    Given QLStats.net lists Alice with the privacy setting "private"
    When Bob types "!except Alice"
    Then the channel is told "^7An admin has allowed ^2Alice^7 to temporarily join despite missing or inadequate qlstats privacy information."
    When Alice tries to join the "red" team from spectators
    Then the join is allowed

  Scenario: An admin can switch the check off
    Given QLStats.net lists Alice with the privacy setting "private"
    When Bob types "!privacy"
    Then the channel is told "^7QLStats policy check disabled. Everyone will be able to join."
    When Alice tries to join the "red" team from spectators
    Then the join is allowed

  Scenario: The status of the check can be asked
    When Bob types "!privacy status"
    Then the channel is told "^7QLStats policy check is enabled"

  Scenario: Nobody but admins can switch the check off
    When Alice types "!privacy"
    Then the channel is not told anything
