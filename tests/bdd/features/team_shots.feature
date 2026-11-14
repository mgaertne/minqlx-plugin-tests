Feature: Punishing team damage

  Players who hurt their teammates lose health, hear a sound and get warned when they keep doing it.

  Background:
    Given the team_shots plugin is loaded with the punishment of 25 health for means of death 7
    And a game on "campgrounds" is in progress
    And player "Alice" is connected
    And player "Bob" is connected
    And player "Carol" is connected
    And Alice is on the "red" team with 100 health
    And Bob is on the "red" team with 100 health
    And Carol is on the "blue" team with 100 health

  Scenario: Hurting a teammate costs health and plays a sound
    When Alice damages Bob with 50 points by means of death 7
    Then Alice has 75 health
    And Alice hears the team hit sound

  Scenario: A second hit shortly after warns the attacker
    Given Alice damaged Bob with 50 points by means of death 7
    When 1500 milliseconds pass
    And Alice damages Bob with 50 points by means of death 7
    Then Alice sees the warning "^1watch your fire!"

  Scenario: A second hit after a while does not warn
    Given Alice damaged Bob with 50 points by means of death 7
    When 2500 milliseconds pass
    And Alice damages Bob with 50 points by means of death 7
    Then Alice sees no warning

  Scenario: The countdown of a new game forgets earlier hits
    Given Alice damaged Bob with 50 points by means of death 7
    And a new game is counting down
    When 500 milliseconds pass
    And Alice damages Bob with 50 points by means of death 7
    Then Alice sees no warning

  Scenario: Hurting an opponent is fine
    When Alice damages Carol with 50 points by means of death 7
    Then Alice has 100 health
    And Alice hears no team hit sound

  Scenario: Hurting oneself is fine
    When Alice damages Alice with 50 points by means of death 7
    Then Alice has 100 health

  Scenario: Light damage is ignored
    When Alice damages Bob with 10 points by means of death 7
    Then Alice has 100 health

  Scenario: Filtered means of death are ignored
    When Alice damages Bob with 50 points by means of death 18
    Then Alice has 100 health

  Scenario: Means of death without a punishment cost nothing
    When Alice damages Bob with 50 points by means of death 9
    Then Alice has 100 health
    And Alice hears no team hit sound

  Scenario: Splash damage that is flagged is ignored
    When Alice damages Bob with 50 points and the flag 16 by means of death 7
    Then Alice has 100 health

  Scenario: An attacker with the minimum health is not hurt further
    Given Alice has 1 health
    When Alice damages Bob with 50 points by means of death 7
    Then Alice has 1 health
    And Alice hears the team hit sound

  Scenario: Damage to a dead teammate is ignored
    Given Bob has 0 health
    When Alice damages Bob with 50 points by means of death 7
    Then Alice has 100 health

  Scenario: Nothing is punished outside a running match
    Given a game on "campgrounds" is in warmup
    When Alice damages Bob with 50 points by means of death 7
    Then Alice has 100 health
