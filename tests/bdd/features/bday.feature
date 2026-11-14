Feature: Celebrating birthdays

  Players register their birthday, which an admin can correct. On their birthday they may pick a map once per year and
  get a birthday song when they join a team on it. Everybody can ask for the next birthday.

  Background:
    Given today is the 15th of June 2025 around noon
    And the bday plugin is loaded
    And a game on "campgrounds" is in warmup
    And player "Alice" is connected
    And player "Bob" is connected
    And player "Carol" is connected
    And Alice is the server owner

  Scenario: A player registers a birthday and has to confirm it
    When Bob types "!bday 20.07."
    Then Bob is told "^7We will remember your birthday as ^620.7.^7. Please confirm with ^6!confirmbday^7 within the next 2 minutes."
    And the birthday of Bob is not stored yet

  Scenario: The confirmation stores the birthday
    Given Bob typed "!bday 20.07."
    When Bob types "!confirmbday"
    Then Bob is told "^7Your birthday was stored as ^620.7.^7."
    And the birthday of Bob is stored as "20.7."

  Scenario: A birthday cannot be confirmed without registering it
    When Bob types "!confirmbday"
    Then Bob is told "^7No pending confirmation for your birthday found. Use ^6!bday [dd.mm.]^7 to register your birthday"
    And the birthday of Bob is not stored yet

  Scenario: A registration expires after two minutes
    Given Bob typed "!bday 20.07."
    And the delayed tasks run
    When Bob types "!confirmbday"
    Then Bob is told "^7No pending confirmation for your birthday found. Use ^6!bday [dd.mm.]^7 to register your birthday"
    And the birthday of Bob is not stored yet

  Scenario: A leap day can be registered
    When Bob types "!bday 29.02."
    Then Bob is told "^7We will remember your birthday as ^629.2.^7. Please confirm with ^6!confirmbday^7 within the next 2 minutes."

  Scenario: An invalid date is rejected
    When Bob types "!bday 31.13."
    Then Bob is told "^7Invalid date given"

  Scenario Outline: Commands with missing or unknown arguments show their usage
    When <player> types "<command>"
    Then the channel is told the usage of the command

    Examples:
      | player | command            |
      | Bob    | !bday              |
      | Bob    | !bday 20.07. maybe |
      | Alice  | !bdayedit Bob      |
      | Carol  | !when              |

  Scenario: Confirming in the same command is accepted
    When Bob types "!bday 20.07. confirm"
    Then Bob is told "^7We will remember your birthday as ^620.7.^7. Please confirm with ^6!confirmbday^7 within the next 2 minutes."

  Scenario: A birthday cannot be changed by the player
    Given the birthday of Bob is "20.7."
    When Bob types "!bday 21.07."
    Then Bob is told "^7You already set your birthday to 20.7.. If you need to correct it, please consult an admin."
    And the birthday of Bob is stored as "20.7."

  Scenario: An admin sets the birthday of a player
    When Alice types "!bdayedit Bob 24.12."
    Then Alice is told "^6Bob's birthday stored as ^624.12."
    And the birthday of Bob is stored as "24.12."

  Scenario: An admin sets the birthday of a player who is offline
    Given the database knows "Zoe" with the Steam ID 999
    When Alice types "!bdayedit 999 1.5."
    Then Alice is told "^6Zoe's birthday stored as ^61.5."
    And the birthday of the Steam ID 999 is stored as "1.5."

  Scenario: An admin sets an invalid birthday
    When Alice types "!bdayedit Bob 31.13."
    Then Alice is told "^7Invalid date given"
    And the birthday of Bob is not stored yet

  Scenario Outline: An admin is told when no single player matches
    When Alice types "!bdayedit <target> 1.5."
    Then Alice is told "<message>"

    Examples:
      | target | message                                        |
      | Zoe    | Sorry, but no players matched your tokens: Zoe. |
      | a      | A total of ^62^7 players matched for a:         |

  Scenario: Players without admin rights cannot set birthdays
    When Bob types "!bdayedit Carol 24.12."
    Then the birthday of Carol is not stored yet

  Scenario: Everybody can look up a birthday
    Given the birthday of Bob is "20.7."
    When Carol types "!when Bob"
    Then everybody is told "Bob^7's birthday is on ^620.7.^7."

  Scenario: Players without a birthday are reported
    When Carol types "!when Bob"
    Then everybody is told "Bob did not tell us about her/his birthday."

  Scenario: Looking up a birthday needs a player
    When Carol types "!when"
    Then the channel is told the usage of the command

  Scenario: The next birthday is announced with the remaining days
    Given the birthday of Bob is "20.7."
    And the birthday of Carol is "3.2."
    When Alice types "!nextbday"
    Then the channel is told "Next birthday: Bob^7 (20.7.) in 35 days."

  Scenario Outline: The next birthday is announced depending on how far away it is
    Given the birthday of Bob is "<birthday>"
    When Alice types "!nextbday"
    Then the channel is told "<announcement>"

    Examples: Within the year
      | birthday | announcement                                                               |
      | 16.6.    | Next birthday: Bob^7 (16.6.) will be tomorrow!                             |
      | 15.6.    | Next birthday: Bob^7 has her/his birthday today! (15.6.) Happy Birthday!   |

    Examples: Already passed this year, and a leap day that is celebrated on the 28th in other years
      | birthday | announcement                                   |
      | 14.6.    | Next birthday: Bob^7 (14.6.) in 364 days.      |
      | 29.2.    | Next birthday: Bob^7 (29.2.) in 258 days.      |

  Scenario: Nothing is announced without birthdays
    When Alice types "!nextbday"
    Then the channel is not told anything

  Scenario: Team chats are answered in the main chat
    Given the birthday of Bob is "20.7."
    When Alice types "!nextbday" in the red team chat
    Then the main chat is told "Next birthday: Bob^7 (20.7.) in 35 days."

  Scenario: The birthday child is congratulated on connecting
    Given the birthday of Bob is "15.6."
    When Bob has loaded
    Then everybody is told "It's Bob^7's birthday today! Congratulate her/him!"
    And Bob is told "Happy Birthday! You can pick a birthday map by using ^6!bmap^7 <mapname>!"

  Scenario: Other players are not congratulated on connecting
    Given the birthday of Bob is "20.7."
    When Bob has loaded
    Then Bob is not told anything

  Scenario: Nobody is congratulated who picked all maps already
    Given the birthday of Bob is "15.6."
    And Bob picked 1 birthday map this year
    When Bob has loaded
    Then Bob is not told anything

  Scenario: The birthday child picks a map
    Given the birthday of Bob is "15.6."
    And the maps plugin knows the maps "campgrounds" and "aerowalk"
    When Bob types "!bmap aerowalk"
    Then everybody is told "Bob^7 picked aerowalk^7 for her/his birthday"
    And the server changes to "aerowalk ca" three seconds later

  Scenario: The map can be abbreviated
    Given the birthday of Bob is "15.6."
    And the maps plugin knows the maps "campgrounds" and "aerowalk"
    When Bob types "!bmap aerow"
    Then everybody is told "Bob^7 picked aerowalk^7 for her/his birthday"

  Scenario: The map can be found by its long name
    Given the birthday of Bob is "15.6."
    And the maps plugin knows the maps "campgrounds" and "aerowalk"
    And the database names the map "aerowalk" "Aero Walk Reloaded"
    When Bob types "!bmap reloaded"
    Then everybody is told "Bob^7 picked aerowalk^7 for her/his birthday"

  Scenario: The map is found with the map manager as well
    Given the birthday of Bob is "15.6."
    And the maps_manager plugin knows the maps "campgrounds" and "aerowalk"
    When Bob types "!bmap aerow"
    Then everybody is told "Bob^7 picked aerowalk^7 for her/his birthday"

  Scenario: An ambiguous map is not picked
    Given the birthday of Bob is "15.6."
    And the maps plugin knows the maps "campgrounds" and "campfire"
    When Bob types "!bmap camp"
    Then Bob is told "More than one map matched your criteria:"
    And Bob is told "  ^4campfire^7"
    And Bob is told "  ^4campgrounds^7"
    And the server does not change the map

  Scenario: A map can only be picked with a birthday
    When Bob types "!bmap aerowalk"
    Then Bob is told "^7You did ^1not^7 set your birthday, yet. Please use ^2!bday^7 to set up your birthday"

  Scenario: A map cannot be picked on other days
    Given the birthday of Bob is "20.7."
    When Bob types "!bmap aerowalk"
    Then Bob is told "^7Nice try, but it's not your birthday. You can't pick your birthday map now!"

  Scenario: Only a limited number of maps can be picked each year
    Given the birthday of Bob is "15.6."
    And Bob picked 1 birthday map this year
    When Bob types "!bmap aerowalk"
    Then Bob is told "^7Sorry, you already picked enough maps for your birthday!"

  Scenario: The map needs to be named
    Given the birthday of Bob is "15.6."
    When Bob types "!bmap"
    Then the channel is told the usage of the command

  Scenario: Maps can only be picked in the warmup
    Given the birthday of Bob is "15.6."
    And a game on "campgrounds" is in progress
    When Bob types "!bmap aerowalk"
    Then Bob is told "^7Sorry, you can only pick your birthday map during warmup!"
    And the server does not change the map

  Scenario: A played birthday map counts for the year
    Given the birthday of Bob is "15.6."
    And Bob picked the map "campgrounds"
    When the game ends
    Then Bob picked 1 birthday map this year

  Scenario: A birthday map that is replaced by another map does not count
    Given the birthday of Bob is "15.6."
    And Bob picked the map "campgrounds"
    And the map changes to "aerowalk"
    When the game ends
    Then Bob picked 0 birthday maps this year

  Scenario: Staying on the birthday map keeps the pick
    Given the birthday of Bob is "15.6."
    And Bob picked the map "campgrounds"
    And the map changes to "campgrounds"
    When the game ends
    Then Bob picked 1 birthday map this year

  Scenario: Games without a birthday map count nothing
    Given the birthday of Bob is "15.6."
    When the game ends
    Then Bob picked 0 birthday maps this year

  Scenario: The birthday song is played when the birthday child joins a team
    Given the birthday of Bob is "15.6."
    And Bob picked the map "campgrounds"
    When Bob joins the "red" team
    Then the birthday song is played

  Scenario: The karaoke plugin sings the birthday song when it is loaded
    Given the birthday of Bob is "15.6."
    And Bob picked the map "campgrounds"
    And the karaoke plugin is loaded
    When Bob joins the "blue" team
    Then the karaoke plugin sings "happybirthday"

  Scenario: Other players joining do not start the song
    Given the birthday of Bob is "15.6."
    And Bob picked the map "campgrounds"
    When Carol joins the "red" team
    Then no birthday song is played

  Scenario: Joining the spectators does not start the song
    Given the birthday of Bob is "15.6."
    And Bob picked the map "campgrounds"
    When Bob joins the "spectator" team
    Then no birthday song is played

  Scenario: The song is not played once the match is running
    Given the birthday of Bob is "15.6."
    And Bob picked the map "campgrounds"
    And a game on "campgrounds" is in progress
    When Bob joins the "red" team
    Then no birthday song is played

  Scenario: The song is not played without a birthday map
    Given the birthday of Bob is "15.6."
    When Bob joins the "red" team
    Then no birthday song is played

  Scenario: The song is not played on another map
    Given the birthday of Bob is "15.6."
    And Bob picked the map "campgrounds"
    And a game on "aerowalk" is in warmup
    When Bob joins the "red" team
    Then no birthday song is played
