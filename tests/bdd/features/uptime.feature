Feature: Showing how long the server has been running

  Everybody can ask for the uptime of the machine and of the Quake Live server, together with the versions that run
  there.

  Background:
    Given it is noon on the 15th of June 2025
    And the uptime plugin is loaded
    And player "Alice" is connected
    And the machine runs "Debian GNU/Linux 12" with Python 3.12.1

  Scenario: The uptime of the machine and of the server is announced
    Given the machine booted 3 days and 4 hours ago
    And the Quake Live server started 2 hours and 5 minutes ago
    And the server runs minqlx "0.8.0"
    When Alice types "!uptime"
    Then everybody is told "^6Operating system^7: ^5Debian GNU/Linux 12^7, ^6uptime^7: ^53 days and 4 hours^7"
    And everybody is told "^6Quake Live server^7 running with ^5minqlx 0.8.0^7 (Python 3.12.1) ^6uptime: ^52 hours and 5 minutes^7"

  Scenario: A machine that was just booted is announced with minutes
    Given the machine booted 7 minutes ago
    And the Quake Live server started 7 minutes ago
    And the server runs minqlx "0.8.0"
    When Alice types "!uptime"
    Then everybody is told "^6Operating system^7: ^5Debian GNU/Linux 12^7, ^6uptime^7: ^57 minutes^7"

  Scenario Outline: The version of the server is shown without decoration
    Given the machine booted 1 hour ago
    And the Quake Live server started 1 hour ago
    And the server runs minqlx "<reported>"
    When Alice types "!uptime"
    Then everybody is told "^6Quake Live server^7 running with ^5minqlx <shown>^7 (Python 3.12.1) ^6uptime: ^51 hour^7"

    Examples: Versions as the servers report them
      | reported                 | shown                |
      | 0.8.0-alpha.1            | 0.8.0-alpha.1        |
      | v0.5.3-16-gd5c1b8e-master | 0.5.3-16-gd5c1b8e-master |
