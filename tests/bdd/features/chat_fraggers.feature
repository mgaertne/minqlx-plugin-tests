Feature: Protecting players who are chatting

  Shooting an opponent who has the chat open is warned. Once a player has dealt enough damage to the same chatting
  opponent, the shooter is stripped of armor, health and weapons.

  Background:
    Given the chat_fraggers plugin is loaded with a threshold of 100 damage
    And a game on "campgrounds" is in progress
    And player "Alice" is connected
    And player "Bob" is connected
    And player "Carol" is connected
    And Alice is on the "red" team
    And Bob is on the "blue" team and is chatting
    And Carol is on the "red" team

  Scenario: Hurting a chatting opponent warns the attacker
    When Alice damages Bob with 40 points
    Then Alice sees "^1Shoot Chatters = Insta-Ban"
    And Alice is not punished

  Scenario: Hurting a chatting opponent beyond the threshold punishes the attacker
    When Alice damages Bob with 120 points
    Then Alice sees "^1You have been warned!"
    And Alice is punished

  Scenario: The damage to the same opponent adds up
    Given Alice damaged Bob with 60 points
    When Alice damages Bob with 60 points
    Then Alice is punished

  Scenario: The damage to different opponents does not add up
    Given Carol is on the "blue" team and is chatting
    And Alice damaged Bob with 60 points
    When Alice damages Carol with 60 points
    Then Alice is not punished

  Scenario: The damage of different attackers does not add up
    Given Carol is on the "red" team
    And Alice damaged Bob with 60 points
    When Carol damages Bob with 60 points
    Then Carol is not punished

  Scenario: A new round forgets the damage
    Given Alice damaged Bob with 60 points
    And a new round is counting down
    When Alice damages Bob with 60 points
    Then Alice is not punished

  Scenario: Hurting an opponent who is not chatting is fine
    Given Bob is on the "blue" team
    When Alice damages Bob with 120 points
    Then Alice sees no message
    And Alice is not punished

  Scenario: Hurting a chatting teammate is not this plugin's business
    Given Bob is on the "red" team and is chatting
    When Alice damages Bob with 120 points
    Then Alice sees no message

  Scenario: Hurting oneself is fine
    Given Alice is on the "red" team and is chatting
    When Alice damages Alice with 120 points
    Then Alice sees no message

  Scenario: Hurting a dead opponent is fine
    Given Bob is dead
    When Alice damages Bob with 120 points
    Then Alice sees no message

  Scenario: Hurting an opponent without health is fine
    Given Bob has 0 health
    When Alice damages Bob with 120 points
    Then Alice sees no message

  Scenario: Nothing is watched outside a running match
    Given a game on "campgrounds" is in warmup
    When Alice damages Bob with 120 points
    Then Alice sees no message

  Scenario: Killing a chatting opponent after little damage warns the killer
    Given Alice damaged Bob with 40 points
    And Alice starts over
    When Alice kills Bob
    Then Alice sees "^1Shoot Chatters = Insta-Ban"
    And Alice is not punished

  Scenario: Killing a chatting opponent after much damage punishes the killer
    Given Alice damaged Bob with 120 points
    And Alice starts over
    When Alice kills Bob
    Then Alice sees "^1You have been warned!"
    And Alice is punished

  Scenario: Killing a chatting opponent without earlier damage is fine
    When Alice kills Bob
    Then Alice sees no message

  Scenario: Killing an opponent who stopped chatting is fine
    Given Alice damaged Bob with 120 points
    And Bob is on the "blue" team
    And Alice starts over
    When Alice kills Bob
    Then Alice sees no message
    And Alice is not punished

  Scenario: Dying without a killer is fine
    When Bob dies without a killer
    Then Alice sees no message

  Scenario: Kills are not watched outside a running match
    Given Alice damaged Bob with 120 points
    And Alice starts over
    And a game on "campgrounds" is in warmup
    When Alice kills Bob
    Then Alice sees no message
    And Alice is not punished
