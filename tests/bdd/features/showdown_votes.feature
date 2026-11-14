Feature: Letting the team decide on a showdown

  With votes enabled, the dead team mates of the last standing player decide whether he or she has to fight a random
  weapon showdown or is slapped to hurry up. The votes are cast with !showdown and !hurry.

  Background:
    Given the showdown plugin is loaded with showdown votes
    And a game on "campgrounds" is in progress
    And player "Alice" is connected
    And player "Bob" is connected
    And player "Carol" is connected
    And player "Dave" is connected
    And player "Eve" is connected
    And round 1 has started
    And Alice is alive on the "red" team
    And Bob is alive on the "red" team
    And Carol is alive on the "red" team
    And Dave is alive on the "blue" team
    And Eve is alive on the "blue" team
    And Bob died

  Scenario: The dead team mates are asked what to do with the last standing player
    When Carol dies
    Then Bob is asked to vote on the fate of Alice
    And Carol is asked to vote on the fate of Alice
    And Alice is not told anything
    And the sound "sound/vo/vote_now" is played to Bob

  Scenario: A last standing player who is hurt is not put to the vote
    Given Alice has 50 health
    When Carol dies
    Then Bob is not told anything

  Scenario: A single opponent is not worth a vote
    Given Eve is dead on the "blue" team
    When Carol dies
    Then Bob is not told anything

  Scenario: Another death does not start a second vote
    Given Carol died
    When Carol dies
    Then Bob is asked to vote on the fate of Alice

  Scenario: A vote for the showdown is counted
    Given Carol died
    When Bob types "!showdown"
    Then everybody is told "Bob^7 voted for showdown. ^51^7/^52^7 voted for showdown, ^50^7/^52^7 voted to punish Alice^7."

  Scenario: Enough votes for the showdown start it
    Given Carol died
    And Bob typed "!showdown"
    When Carol types "!showdown"
    Then everybody is told "^7Nade showdown! Weapons will be restored next round."
    And Alice is stripped of all weapons

  Scenario: Enough votes to hurry up punish the last standing player
    Given Carol died
    And Bob typed "!hurry"
    When Carol types "!hurry"
    Then Alice is slapped for 50 damage
    And Alice is told "Your team mates voted to punish you to hurry up!"
    And Alice sees "Hurry up!" in the middle of the screen

  Scenario: A vote can be changed
    Given Carol died
    And Bob typed "!showdown"
    When Bob types "!hurry"
    Then Bob is told "Changing your vote from ^5random weapon showdown^7 to ^5hurry^7"

  Scenario: A vote can be changed back
    Given Carol died
    And Bob typed "!hurry"
    When Bob types "!showdown"
    Then Bob is told "Changing your vote from ^5hurry up^7 to ^5showdown^7"

  Scenario Outline: The same vote is not counted twice
    Given Carol died
    And Bob typed "!<vote>"
    When Bob types "!<vote>"
    Then Bob is told "You already voted for <description>!"

    Examples:
      | vote     | description                          |
      | showdown | ^5random weapon showdown^7           |
      | hurry    | ^5hurry up^7                         |

  Scenario: An admin who repeats the vote forces the showdown
    Given Bob is an admin
    And Carol died
    And Bob typed "!showdown"
    When Bob types "!showdown"
    Then everybody is told "^7Nade showdown! Weapons will be restored next round."

  Scenario: The last standing player cannot vote
    Given Carol died
    When Alice types "!hurry"
    Then no vote is counted

  Scenario: The opponents cannot vote
    Given Carol died
    When Dave types "!hurry"
    Then Dave is told "Nice try, but you're not on the last standing player's team!"

  Scenario: Votes without a vote running are ignored
    When Carol types "!hurry"
    Then Carol is not told anything

  Scenario: Votes are too late when the opponents are gone
    Given Carol died
    And Eve died
    When Bob types "!showdown"
    Then everybody is told "Too late for showdown votes!"

  Scenario: The weapons stay until the round ends and the last opponent is announced
    Given Carol died
    And Bob typed "!showdown"
    And Carol typed "!showdown"
    And the countdown is over
    When Dave dies
    Then the countdown announces "1 blue left!"
    And the weapons are not restored

  Scenario: The last opponent of a blue player is announced as well
    Given Alice is alive on the "blue" team
    And Bob is dead on the "blue" team
    And Carol is alive on the "blue" team
    And Dave is alive on the "red" team
    And Eve is alive on the "red" team
    And Carol died
    And Bob typed "!showdown"
    And Carol typed "!showdown"
    And the countdown is over
    When Dave dies
    Then the countdown announces "1 red left!"
    And the weapons are not restored
