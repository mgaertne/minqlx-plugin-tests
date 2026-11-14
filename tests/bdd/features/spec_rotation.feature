Feature: Rotating spectators into a running match

  A match with more players than places lets the spectators wait in a rotation. After every round the player with the
  least damage on the losing team swaps places with the next player of the rotation.

  Background:
    Given the spec_rotation plugin is loaded
    And a game on "campgrounds" is in progress
    And player "Alice" is connected
    And player "Bob" is connected
    And player "Carol" is connected
    And player "Dave" is connected
    And player "Eve" is connected
    And Alice is on the "red" team
    And Bob is on the "blue" team

  Scenario Outline: A spectator who wants into a full match joins the rotation instead
    When Carol tries to join the "<team>" team
    Then Carol is told "Carol^7, we added you to the spec rotation and you will automatically rotate with the weakest player on the losing team."
    And the team switch is stopped
    And the spec rotation holds Carol

    Examples:
      | team |
      | red  |
      | blue |
      | any  |

  Scenario: A player in the rotation cannot join before their turn
    Given Carol tried to join the "red" team
    When Carol tries to join the "blue" team
    Then the team switch is stopped
    And Carol is told "Carol^7, we added you to the spec rotation and you will automatically rotate with the weakest player on the losing team."

  Scenario: Further spectators may join while somebody is in the rotation
    Given Carol tried to join the "red" team
    When Dave tries to join the "red" team
    Then the team switch is allowed
    And the spec rotation holds Carol

  Scenario: Teams with uneven sizes can be joined freely
    Given Dave is on the "red" team
    When Carol tries to join the "blue" team
    Then the team switch is allowed
    And the spec rotation is empty

  Scenario: Going to the spectators is never stopped
    When Dave tries to join the "spectator" team
    Then the team switch is allowed
    And the spec rotation is empty

  Scenario: The warmup is left alone
    Given a game on "campgrounds" is in warmup
    When Carol tries to join the "red" team
    Then the team switch is allowed
    And the spec rotation is empty

  Scenario Outline: The rotation steps aside when the balance plugin ignores the situation
    Given the plugin "<plugin>" ignores the situation
    When Carol tries to join the "red" team
    Then the team switch is allowed
    And the spec rotation is empty

    Examples:
      | plugin     |
      | balancetwo |
      | mybalance  |

  Scenario: Leaving to the spectators by command removes a player from the rotation
    Given Carol waits in the spec rotation
    When Carol sends the client command "team s"
    Then Carol is told "You have been removed from the spec rotation."
    And the spec rotation is empty

  Scenario: Other client commands keep the rotation
    Given Carol waits in the spec rotation
    When Carol sends the client command "score"
    Then Carol is not told anything
    And the spec rotation holds Carol

  Scenario: Players outside the rotation are not told anything when they leave
    When Dave sends the client command "team s"
    Then Dave is not told anything

  Scenario: The command is ignored while the balance plugin ignores the situation
    Given Carol waits in the spec rotation
    And the plugin "balancetwo" ignores the situation
    When Carol sends the client command "team s"
    Then Carol is not told anything
    And the spec rotation holds Carol

  Scenario: Uneven teams at the countdown put every player into the rotation
    Given Dave is on the "red" team
    And a game on "campgrounds" is counting down
    When the countdown runs
    Then the spec rotation holds Alice, Dave and Bob

  Scenario: Even teams at the countdown start without a rotation
    Given a game on "campgrounds" is counting down
    When the countdown runs
    Then the spec rotation is empty

  Scenario: Players who start the match leave the rotation
    Given Dave is on the "red" team
    And a game on "campgrounds" is counting down
    And the countdown ran
    When the game starts
    Then the spec rotation is empty

  Scenario: A player who goes to the spectators during the countdown rotates next round
    Given a game on "campgrounds" is counting down
    And the countdown ran
    When Alice switches to the "spectator" team from the "red" team
    Then Alice is told "Alice^7, you will automatically rotate with the weakest player on the losing team next round."
    And the spec rotation holds Alice

  Scenario: A new player pulls the rotation player to the other team
    Given Carol waits in the spec rotation
    When Dave switches to the "red" team from the "spectator" team
    Then Carol is put on the "blue" team
    And everybody is told "Disabling spec rotation since there are enough players now."
    And the spec rotation is empty

  Scenario: A leaving player is replaced by the first of the rotation
    Given Dave is on the "red" team
    And Eve is on the "blue" team
    And Carol waits in the spec rotation
    When Dave switches to the "spectator" team from the "red" team
    Then Carol is put on the "red" team
    And the spec rotation is empty

  Scenario: Switches are ignored once the round limit is reached
    Given Carol waits in the spec rotation
    And the red team has 8 points
    When Dave switches to the "red" team from the "spectator" team
    Then Carol is not put on any team

  Scenario: Switches are ignored while the balance plugin ignores the situation
    Given Carol waits in the spec rotation
    And the plugin "balancetwo" ignores the situation
    When Dave switches to the "red" team from the "spectator" team
    Then Carol is not put on any team

  Scenario: A switch that leaves the teams even changes nothing
    Given Dave is on the "red" team
    And Eve is on the "blue" team
    And Carol waits in the spec rotation
    When Dave switches to the "red" team from the "spectator" team
    Then Carol is not put on any team

  Scenario: Switches are ignored without a rotation
    Given Dave is on the "red" team
    When Dave switches to the "red" team from the "spectator" team
    Then Carol is not put on any team

  Scenario: Switches are ignored during the warmup
    Given a game on "campgrounds" is in warmup
    And Carol waits in the spec rotation
    When Dave switches to the "red" team from the "spectator" team
    Then Carol is not put on any team

  Scenario: The switch the plugin made itself does not pull the next player
    Given Carol waits in the spec rotation
    And Eve waits in the spec rotation
    And Dave switched to the "red" team from the "spectator" team
    When Carol switches to the "blue" team from the "spectator" team
    Then Eve is not put on any team
    And the spec rotation holds Eve

  Scenario: A returning player brings back the team score
    Given Dave is on the "red" team
    And Carol waits in the spec rotation
    And the red team has 3 points
    And round 1 ended in a draw
    And the red team has 1 points
    When Dave switches to the "red" team from the "spectator" team
    Then the red team gained 2 points

  Scenario: A team score that fell back is restored when a round ends
    Given the red team has 3 points
    And round 1 ended in a draw
    And the red team has 1 points
    When round 2 ends in a draw
    Then the red team gained 2 points

  Scenario: A returning player gets the score back
    Given Carol is on the "blue" team
    And Carol has a score of 5
    And Alice is on the "red" team
    And round 1 ended in a draw
    And Carol is on the "spectator" team
    And Carol has a score of 0
    And Carol waits in the spec rotation
    And Dave is on the "red" team
    When round 2 counts down
    Then Carol is put on the "blue" team
    And Carol has a score of 5

  Scenario: A rotation entry of a player who left is skipped
    Given Dave is on the "red" team
    And the Steam ID 999 waits in the spec rotation
    When round 2 counts down
    Then the spec rotation is empty

  Scenario: The countdown leaves the rotation empty while the balance plugin ignores the situation
    Given Dave is on the "red" team
    And a game on "campgrounds" is counting down
    And the plugin "balancetwo" ignores the situation
    When the countdown runs
    Then the spec rotation is empty

  Scenario: Rounds that end without a game are ignored
    Given Eve waits in the spec rotation
    And no game is running
    When round 2 ends with a win for red
    Then Eve is not put on any team

  Scenario: The results are printed when a duel is over
    Given the red team has 1 points
    And round 1 ended in a draw
    And Bob is on the "spectator" team
    And Carol is on the "blue" team
    And the blue team has 2 points
    And round 2 ended in a draw
    And the red team has 8 points
    When round 8 ends with a win for red
    Then everybody is told "DuelArena results:"
    And everybody is told "Place ^31.^7 Alice ^7(Wins:^28^7)"
    And everybody is told "Place ^32.^7 Carol ^7(Wins:^22^7)"
    And everybody is told "Place ^33.^7 Bob ^7(Wins:^20^7)"

  Scenario: A disconnecting player leaves the rotation
    Given Carol waits in the spec rotation
    When Carol disconnects
    Then the spec rotation is empty
    And Eve is not put on any team

  Scenario: A disconnecting player of a team is replaced by the first of the rotation
    Given Carol waits in the spec rotation
    When Alice disconnects
    Then Carol is put on the "red" team
    And the spec rotation is empty

  Scenario: Nobody is replaced when nobody waits
    When Alice disconnects
    Then Carol is not put on any team

  Scenario: Nobody is replaced outside a running match
    Given a game on "campgrounds" is in warmup
    And Carol waits in the spec rotation
    When Alice disconnects
    Then Carol is not put on any team

  Scenario: Nobody is replaced once the round limit is reached
    Given Carol waits in the spec rotation
    And the blue team has 8 points
    When Alice disconnects
    Then Carol is not put on any team

  Scenario: Nobody is replaced while the balance plugin ignores the situation
    Given Carol waits in the spec rotation
    And the plugin "mybalance" ignores the situation
    When Alice disconnects
    Then Carol is not put on any team

  Scenario: A new player in a full match is invited to join the rotation
    When Dave has loaded
    Then Dave is told "Dave, join to activate spec rotation! Player with fewest damage on losing team will be rotated with you."

  Scenario: Nobody is invited while the rotation is active
    Given Carol waits in the spec rotation
    When Dave has loaded
    Then Dave is not told anything

  Scenario: Nobody is invited when the teams are uneven
    Given Carol is on the "red" team
    When Dave has loaded
    Then Dave is not told anything

  Scenario: Nobody is invited outside a running match
    Given a game on "campgrounds" is in warmup
    When Dave has loaded
    Then Dave is not told anything

  Scenario: Nobody is invited while the balance plugin ignores the situation
    Given the plugin "balancetwo" ignores the situation
    When Dave has loaded
    Then Dave is not told anything

  Scenario: The player with the fewest games is added to the rotation when a round starts uneven
    Given Dave is on the "red" team
    And Alice has 10 games completed
    And Dave has 3 games completed
    When round 2 counts down
    Then Dave is told "Dave^7, we added you to the spec rotation and you will automatically rotate with the weakest player on the losing team."
    And the spec rotation holds Dave

  Scenario: A player without recorded games counts as new
    Given Dave is on the "red" team
    And Alice has 10 games completed
    When round 2 counts down
    Then the spec rotation holds Dave

  Scenario Outline: The first of the rotation joins the smaller team when a round starts uneven
    Given Dave is on the "<bigger>" team
    And Carol waits in the spec rotation
    When round 2 counts down
    Then Carol is put on the "<smaller>" team
    And the spec rotation is empty

    Examples:
      | bigger | smaller |
      | red    | blue    |
      | blue   | red     |

  Scenario: Even teams need no rotation at the start of a round
    Given Carol waits in the spec rotation
    When round 2 counts down
    Then Carol is not put on any team
    And the spec rotation holds Carol

  Scenario: The rotation is not touched while the balance plugin ignores the situation
    Given Dave is on the "red" team
    And Carol waits in the spec rotation
    And the plugin "balancetwo" ignores the situation
    When round 2 counts down
    Then Carol is not put on any team

  Scenario: The weakest player of the losing team swaps with the next in the rotation
    Given Dave is on the "red" team
    And Carol is on the "blue" team
    And Eve waits in the spec rotation
    And everybody has dealt 0 damage
    And round 2 started
    And Bob has dealt 100 damage
    And Carol has dealt 20 damage
    When round 2 ends with a win for red
    Then Eve is put on the "blue" team
    And Carol is put on the "spectator" team
    And everybody is told "Replacing player with fewest round damage on team ^4blue^7 Carol^7 with the next player from the rotation Eve^7."
    And Carol is told "Carol^7, you will automatically rotate with the weakest player on the losing team next round."
    And the spec rotation holds Carol

  Scenario: Blue can lose as well
    Given Dave is on the "red" team
    And Carol is on the "blue" team
    And Eve waits in the spec rotation
    And everybody has dealt 0 damage
    And round 2 started
    And Alice has dealt 5 damage
    And Dave has dealt 80 damage
    When round 2 ends with a win for blue
    Then Eve is put on the "red" team
    And Alice is put on the "spectator" team

  Scenario: A drawn round swaps nobody
    Given Eve waits in the spec rotation
    When round 1 ends in a draw
    Then Eve is not put on any team
    And the spec rotation holds Eve

  Scenario: Nobody is swapped without a rotation
    When round 1 ends with a win for red
    Then Bob is not put on any team

  Scenario: Nobody is swapped when a team is empty
    Given Bob is on the "spectator" team
    And Eve waits in the spec rotation
    When round 1 ends with a win for red
    Then Eve is not put on any team

  Scenario: Nobody is swapped without damage statistics after the first round
    Given Eve waits in the spec rotation
    When round 2 ends with a win for red
    Then Eve is not put on any team

  Scenario: A rotation player who already plays again is dropped without a swap
    Given Eve waits in the spec rotation
    And Eve is on the "red" team
    And Dave is on the "red" team
    When round 1 ends with a win for blue
    Then Alice is not put on any team
    And the spec rotation is empty

  Scenario: In a duel the new player starts with a clean team score
    Given Eve waits in the spec rotation
    And the blue team has 2 points
    When round 1 ends with a win for red
    Then Eve is put on the "blue" team
    And Bob is put on the "spectator" team
    And the blue team lost 2 points

  Scenario: Nothing is swapped once the round limit is reached
    Given Eve waits in the spec rotation
    And the red team has 8 points
    When round 8 ends with a win for red
    Then Eve is not put on any team

  Scenario: Nothing is swapped while the balance plugin ignores the situation
    Given Eve waits in the spec rotation
    And the plugin "balancetwo" ignores the situation
    When round 1 ends with a win for red
    Then Eve is not put on any team

  Scenario: A new map clears the rotation
    Given Eve waits in the spec rotation
    When the map changes
    Then the spec rotation is empty
