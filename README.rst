dota2api
========
.. image:: https://travis-ci.org/joshuaduffy/dota2api.svg
    :target: https://travis-ci.org/joshuaduffy/dota2api
.. image:: https://readthedocs.org/projects/dota2api/badge/?version=latest
    :target: https://readthedocs.org/projects/dota2api/?badge=latest

API wrapper in Python created for interacting and getting data easily from the 
Dota 2 API from Valve.

This libary parses all ids (coming soon) into strings along with turning stuff into python objects
(also coming soon). All of this comes with Python 3.0 support (coming soon), a set of complete tests (coming soon)
and documentation for the API itself(coming soon).
 
Look how easy it is...

.. code-block:: python
    >>> from dota2api import wrapper
    >>> api = wrapper.Initialise("API_KEY")
    >>> hist = api.get_match_history(account_id=41231571)

Information can also be acessed via a dictionary...

.. code-block:: python
    >>> match = api.get_match_details(match_history=1000193456).dict
    >>> match['radiant_win']
    False

Store your API key under the following environment variable to save yourself some finger work.

.. code-block:: bash
    $ set $D2_API_KEY = "806654CB26BD2D2D6F04DBD953AFF918"

Supported API calls
+++++++++++++++++++
- get_match_history
- get_match_details
- get_player_summaries
- get_league_listing
- get_live_league_games
- get_team_info_by_team_id
- get_heroes
- get_tournament_prize_pool
- get_game_items

Unsupported
+++++++++++
- EconomySchema
- GetMatchHistoryBySequenceNum


Documentation
-------------
Documentation is available at http://dota2api.readthedocs.org/

Install
-------

.. code-block:: bash
    $ git clone https://github.com/joshuaduffy/dota2api.git
    $ cd dota2api
    $ python setup.py install