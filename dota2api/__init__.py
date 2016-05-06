#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Dota 2 API wrapper and parser in Python"""

__author__ = "Joshua Duffy, Evaldo Bratti"
__date__ = "29/10/2014"
__version__ = "1.3.1"
__licence__ = "GPL"

import json
import collections
import time
from retrying import retry
from tqdm import tqdm

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

import os
import requests

from .src import urls, exceptions, response, parse


class Initialise(object):
    """When calling this you need to provide the ``api_key``
    You can also specify a ``language``

    :param api_key: (str) string with the ``api key``
    :param logging: (bool, optional) set this to True for logging output
    """

    def __init__(self, api_key=None, executor=None, language=None, logging=None):
        if api_key:
            self.api_key = api_key
        elif 'D2_API_KEY' in os.environ:
            self.api_key = os.environ['D2_API_KEY']
        else:
            raise exceptions.APIAuthenticationError()

        if not language:
            self.language = "en_us"
        else:
            self.language = language

        if not executor:
            self.executor = requests.get
        else:
            self.executor = executor

        if logging:
            self.logger = _setup_logger()
        else:
            self.logger = None

        self.__format = "json"


    def __get_all_match_history_in_batches(self, account_id=None, silently=False, initial_hist=None, **kwargs):
        """Get all matches in batches of 100.
            Retry in case of api errors"""

        match_start_index = 0

        if initial_hist == None:
            hist = self.get_match_history_and_retry_on_failure(start_at_match_id=match_start_index,
                                                           account_id=account_id, **kwargs)

        remaining_matches = hist['total_results']
        matches = []

        while remaining_matches > 0:
            remaining_matches = hist['results_remaining']
            if not silently:
                match_batch_iterable = tqdm(hist['matches'], desc='Loading batch of ' + str(hist['num_results']) + ' matches ')
            else:
                match_batch_iterable = hist['matches']

            for eachMatch in match_batch_iterable:
                time.sleep(1)
                details = self.get_match_details_and_retry_on_failure(match_id=eachMatch['match_id'])
                matches.append(details)

            match_start_index = hist['matches'][-1]['match_id'] - 1
            time.sleep(1)
            hist = self.get_match_history_and_retry_on_failure(start_at_match_id=match_start_index,
                                                               account_id=account_id)
        return matches


    def get_all_matches_for_user(self, account_id, silently=False):
        """Returns a array containing match details for all matches for a user ID.
            Since the valve api will only return 500 results per query,
            the best way to do this is to get the results for each hero if
            an account has more than 500 games played.
            If there are more than 500 games for one hero, we will only be able
            to retrieve the most recent 500 for that hero
        """
        hist = self.get_match_history_and_retry_on_failure(account_id=account_id)
        matches = []

        if hist['total_results'] < 500:
            matches = self.__get_all_match_history_in_batches(account_id=account_id,silently=silently,initial_hist=hist)

        else:
            heroes = self.get_heroes()

            if not silently:
                heroes_iterable = tqdm(heroes['heroes'], desc='Getting matches for each hero ')
            else:
                heroes_iterable = heroes['heroes']
            time.sleep(1)
            for each_hero in heroes_iterable:
                if not silently:
                    print('\n')
                    print('Getting matches for ' + each_hero['localized_name'])
                hero_matches = self.__get_all_match_history_in_batches(account_id=account_id,silently=silently,hero_id=each_hero['id'])
                matches.extend(hero_matches)

        return matches

    @retry(wait_random_min=5000, wait_random_max=60000, stop_max_attempt_number=5)
    def get_match_history_and_retry_on_failure(self, start_at_match_seq=None, account_id=None, **kwargs):
        """Calls get_match_history, but retries a maximum of 5 times on errors.
        This is useful for dealing with 503 errors from Valve's api"""
        return self.get_match_history(start_at_match_seq=start_at_match_seq, account_id=account_id,  **kwargs)

    @retry(wait_random_min=5000, wait_random_max=60000, stop_max_attempt_number=5)
    def get_match_details_and_retry_on_failure(self, match_id=None, **kwargs):
        """Calls get_match_details, but retries a maximum of 5 times on errors.
        This is useful for dealing with 503 errors from Valve's api"""
        return self.get_match_details(match_id=match_id, **kwargs)

    def get_match_history(self, account_id=None, **kwargs):
        """Returns a dictionary containing a list of the most recent Dota matches

        :param account_id: (int, optional)
        :param hero_id: (int, optional)
        :param game_mode: (int, optional) see ``ref/modes.json``
        :param skill: (int, optional) see ``ref/skill.json``
        :param date_min: (int, optional) unix timestamp rounded to the
            nearest day
        :param date_max: (int, optional) unix timestamp rounded to the
            nearest day
        :param min_players: (int, optional) only return matches with minimum
            amount of players
        :param league_id: (int, optional) for ids use ``get_league_listing()``
        :param start_at_match_id: (int, optional) start at matches equal to or
            older than this match id
        :param matches_requested: (int, optional) defaults to ``100``
        :param tournament_games_only: (str, optional) limit results to
            tournament matches only
        :return: dictionary of matches, see :doc:`responses </responses>`
        """
        if 'account_id' not in kwargs:
            kwargs['account_id'] = account_id
        url = self.__build_url(urls.GET_MATCH_HISTORY, **kwargs)
        req = self.executor(url)
        if self.logger:
            self.logger.info('URL: {0}'.format(url))
        if not self.__check_http_err(req.status_code):
            return response.build(req, url)

    def get_match_history_by_seq_num(self, start_at_match_seq_num=None, **kwargs):
        """Returns a dictionary containing a list of Dota matches in the order they were recorded

        :param start_at_match_seq_num: (int, optional) start at matches equal to or
            older than this match id
        :param matches_requested: (int, optional) defaults to ``100``
        :return: dictionary of matches, see :doc:`responses </responses>`
        """
        if 'start_at_match_seq_num' not in kwargs:
            kwargs['start_at_match_seq_num'] = start_at_match_seq_num
        url = self.__build_url(urls.GET_MATCH_HISTORY_BY_SEQ_NUM, **kwargs)
        req = self.executor(url)
        if self.logger:
            self.logger.info('URL: {0}'.format(url))
        if not self.__check_http_err(req.status_code):
            return response.build(req, url)

    def get_match_details(self, match_id=None, **kwargs):
        """Returns a dictionary containing the details for a Dota 2 match

        :param match_id: (int, optional)
        :return: dictionary of matches, see :doc:`responses </responses>`
        """
        if 'match_id' not in kwargs:
            kwargs['match_id'] = match_id
        url = self.__build_url(urls.GET_MATCH_DETAILS, **kwargs)
        req = self.executor(url)
        if self.logger:
            self.logger.info('URL: {0}'.format(url))
        if not self.__check_http_err(req.status_code):
            return response.build(req, url)

    def get_league_listing(self):
        """Returns a dictionary containing a list of all ticketed leagues

        :return: dictionary of ticketed leagues, see :doc:`responses </responses>`
        """
        url = self.__build_url(urls.GET_LEAGUE_LISTING)
        req = self.executor(url)
        if self.logger:
            self.logger.info('URL: {0}'.format(url))
        if not self.__check_http_err(req.status_code):
            return response.build(req, url)

    def get_live_league_games(self):
        """Returns a dictionary containing a list of ticked games in progress

        :return: dictionary of live games, see :doc:`responses </responses>`
        """
        url = self.__build_url(urls.GET_LIVE_LEAGUE_GAMES)
        req = self.executor(url)
        if self.logger:
            self.logger.info('URL: {0}'.format(url))
        if not self.__check_http_err(req.status_code):
            return response.build(req, url)

    def get_team_info_by_team_id(self, start_at_team_id=None, **kwargs):
        """Returns a dictionary containing a in-game teams

        :param start_at_team_id: (int, optional)
        :param teams_requested: (int, optional)
        :return: dictionary of teams, see :doc:`responses </responses>`
        """
        if 'start_at_team_id' not in kwargs:
            kwargs['start_at_team_id'] = start_at_team_id
        url = self.__build_url(urls.GET_TEAM_INFO_BY_TEAM_ID, **kwargs)
        req = self.executor(url)
        if self.logger:
            self.logger.info('URL: {0}'.format(url))
        if not self.__check_http_err(req.status_code):
            return response.build(req, url)

    def get_player_summaries(self, steamids=None, **kwargs):
        """Returns a dictionary containing a player summaries

        :param steamids: (list) list of ``32-bit`` or ``64-bit`` steam ids, notice
                                that api will convert if ``32-bit`` are given
        :return: dictionary of player summaries, see :doc:`responses </responses>`
        """
        if not isinstance(steamids, collections.Iterable):
            steamids = [steamids]

        base64_ids = list(map(convert_to_64_bit, filter(lambda x: x is not None, steamids)))

        if 'steamids' not in kwargs:
            kwargs['steamids'] = base64_ids
        url = self.__build_url(urls.GET_PLAYER_SUMMARIES, **kwargs)
        req = self.executor(url)
        if self.logger:
            self.logger.info('URL: {0}'.format(url))
        if not self.__check_http_err(req.status_code):
            return response.build(req, url)

    def get_heroes(self):
        """Returns a dictionary of in-game heroes, used to parse ids into localised names

        :return: dictionary of heroes, see :doc:`responses </responses>`
        """
        url = self.__build_url(urls.GET_HEROES)
        req = self.executor(url)
        if self.logger:
            self.logger.info('URL: {0}'.format(url))
        if not self.__check_http_err(req.status_code):
            return response.build(req, url)

    def get_game_items(self):
        """Returns a dictionary of in-game items, used to parse ids into localised names

        :return: dictionary of items, see :doc:`responses </responses>`
        """
        url = self.__build_url(urls.GET_GAME_ITEMS)
        req = self.executor(url)
        if self.logger:
            self.logger.info('URL: {0}'.format(url))
        if not self.__check_http_err(req.status_code):
            return response.build(req, url)

    def get_tournament_prize_pool(self, leagueid=None, **kwargs):
        """Returns a dictionary that includes community funded tournament prize pools

        :param leagueid: (int, optional)
        :return: dictionary of prize pools, see :doc:`responses </responses>`
        """
        if 'leagueid' not in kwargs:
            kwargs['leagueid'] = leagueid
        url = self.__build_url(urls.GET_TOURNAMENT_PRIZE_POOL, **kwargs)
        req = self.executor(url)
        if self.logger:
            self.logger.info('URL: {0}'.format(url))
        if not self.__check_http_err(req.status_code):
            return response.build(req, url)

    def update_game_items(self):
        """
        Update the item reference data via the API
        """
        _save_dict_to_file(self.get_game_items(), "items.json")

    def update_heroes(self):
        """
        Update the hero reference data via the API
        """
        _save_dict_to_file(self.get_heroes(), "heroes.json")

    def __build_url(self, api_call, **kwargs):
        """Builds the api query"""
        kwargs['key'] = self.api_key
        if 'language' not in kwargs:
            kwargs['language'] = self.language
        if 'format' not in kwargs:
            kwargs['format'] = self.__format
        api_query = urlencode(kwargs)

        return "{0}{1}?{2}".format(urls.BASE_URL,
                                   api_call,
                                   api_query)

    def __check_http_err(self, status_code):
        """Raises an exception if we get a http error"""
        if status_code == 403:
            raise exceptions.APIAuthenticationError(self.api_key)
        elif status_code == 503:
            raise exceptions.APITimeoutError()
        else:
            return False


def convert_to_64_bit(number):
    min64b = 76561197960265728
    if number < min64b:
        return number + min64b
    return number


def _setup_logger():
    import logging
    logging.basicConfig(level=logging.NOTSET)  # Will log all
    return logging.getLogger(__name__)


def _save_dict_to_file(json_dict, file_name):
    out_file = open(parse.load_json_file(file_name), "w")
    json.dump(json_dict, out_file, indent=4)
    out_file.close()
