#!/usr/bin/env python3
import argparse
import collections
import logging
import os
import random
import string
import threading
import time
from datetime import datetime
from itertools import zip_longest
from logging import handlers
from typing import List

from transitions import Machine
from transitions import State
# from transitions import logger as transitions_logger

import zemulator

_logger = logging.getLogger('zjsn.zrobot')


NODE_SIMPLE = 'simple'
NODE_RESOURCE = 'resource'
NODE_SKIP = 'skip'

class Node(object):
    """docstring for Node"""
    _node_types = [NODE_SIMPLE, NODE_RESOURCE, NODE_SKIP]
    DEFAULT_SLEEP_TIME = 30

    def __init__(self, name,
                 node_type=NODE_SIMPLE,
                 formation=2,
                 night_flag=0,
                 big_broken_protect=True,
                 enemy_target=None,
                 enemy_avoid=None,
                 additional_spy_filter=None,
                 sleep_time = None):
        """we have 3 node_types: simple, resource, skip"""
        super(Node, self).__init__()
        self.name = str.upper(name)
        self.node_id = 0

        self.big_broken_protect = big_broken_protect
        self.next_nodes = []
        if node_type not in self._node_types:
            raise ValueError('{} is not a node type'.format(node_type))
        self.node_type = node_type
        self.night_flag = night_flag
        self.battle_result = {}
        self.formation = formation
        self.enemy_target = enemy_target
        self.enemy_avoid = enemy_avoid
        self.skip_rate_limit = 0
        self.skip_rate = 0

        if sleep_time:
            self.sleep_mu = sleep_time
        else:
            self.sleep_mu = Node.DEFAULT_SLEEP_TIME
        self.sleep_sigma = 2
        rd = random.normalvariate(self.sleep_mu, self.sleep_sigma)
        if rd < self.sleep_mu - 3 * self.sleep_sigma or rd > self.sleep_mu + 3 * self.sleep_sigma:
            self.battle_length = self.sleep_mu
        else:
            self.battle_length = rd

        self.additional_spy_filter = additional_spy_filter

        self.boss_hp = -1
        self.ze = None

    def add_next(self, next_nodes):
        if isinstance(next_nodes, collections.Iterable):
            self.next_nodes.extend(next_nodes)
        else:
            self.next_nodes.append(next_nodes)
        return self

    def _node_name(self, node_id):
        return string.ascii_uppercase[int(str(node_id)[-2:]) - 2]

    def spy_filter(self, spy_result):
        if 'enemyVO' not in spy_result:
            return True
        else:
            self.skip_rate = float(spy_result['enemyVO']['successRate'].strip("%")) / 100
        try:
            enemy_ids = [int(i['type']) for i in spy_result['enemyVO']['enemyShips']]
            enemy_ids += [int(spy_result['enemyVO']['enemyFleet']['id'])]
            enemy_keywords = [str(i['title']) for i in spy_result['enemyVO']['enemyShips']]
            enemy_keywords += [spy_result['enemyVO']['enemyFleet']['title']]
            enemy_keywords = ' '.join(enemy_keywords)
        except KeyError:
            enemy_ids = None
            enemy_keywords = None
        target_flag = True
        if self.enemy_target and enemy_keywords:
            if self.enemy_target not in enemy_ids and str(self.enemy_target) not in str(enemy_keywords):
                target_flag = False

        avoid_flag = True
        if self.enemy_avoid and enemy_keywords:
            if self.enemy_avoid in enemy_ids or str(self.enemy_avoid) in str(enemy_keywords):
                avoid_flag = False

        additional_flag = True
        if callable(self.additional_spy_filter):
            if not self.additional_spy_filter(spy_result):
                additional_flag = False

        if all((target_flag, avoid_flag, additional_flag)):
            return True
        else:
            return False

    def deal(self, mission: 'Mission'):
        self.ze = mission.ze
        ze = self.ze
        _logger.info('进入 {} 点'.format(self._node_name(ze.node)))
        if self.node_type == 'resource':
            if ze.working_ships[0].should_be_repair(2):
                return 0
            else:
                self.battle_result = ze.dealto(1, big_broken_protect=False)
        else:
            spy_result = ze.spy()
            if self.spy_filter(spy_result):
                force_battle = False
                if self.node_type == 'skip':
                    _logger.debug("sikp success rate: {:.1%}".format(self.skip_rate))
                    if self.skip_rate > self.skip_rate_limit:
                        skip_result = ze.skip()
                        if not skip_result:
                            if mission.skip_margin > 0:
                                mission.skip_margin -= 1
                                force_battle = True
                            else:
                                return 0
                        else:
                            _logger.debug('skip success')
                    else:
                        return 0

                if self.node_type == 'simple' or force_battle:
                    try:
                        result_before_night = ze.dealto(
                            self.formation, big_broken_protect=self.big_broken_protect)
                    except zemulator.ZjsnError as e:
                        _logger.debug(e)
                        return -1
                    time.sleep(self.battle_length)

                    if self.night_flag:
                        report = result_before_night["warReport"]
                        if not any(report["hpBeforeNightWarEnemy"]):
                            night_flag = 0
                        else:
                            night_flag = 1
                            _logger.debug('night battle')

                    else:
                        night_flag = 0

                    # get War result
                    self.get_result(night_flag)
                    # if 'newShipVO' in self.battle_result:
                    #     new_ship = zemulator.ZjsnShip(
                    #         self.battle_result['newShipVO'][0])
                    #     if new_ship.cid not in ze.unlockShip:
                    #         _logger.info('get new ship: {}'.format(new_ship.name))
                    #     else:
                    #         _logger.debug('get: {}'.format(new_ship.name))
            else:
                return 0

        if self.next_nodes:
            next_node_id = ze.go_next()
            next_node = self._node_name(next_node_id)
            for n_node in self.next_nodes:
                if n_node.name == next_node:
                    return n_node
            return 0
        else:
            return None

    def get_result(self, night_flag):
        self.battle_result = self.ze.getWarResult(night_flag)
        if "bossHp" in self.battle_result:
            self.boss_hp = int(self.battle_result['bossHp'])
        elif 'bossHpLeft' in self.battle_result:
            self.boss_hp = int(self.battle_result['bossHpLeft'])
        battle_report = self.battle_result["warResult"]
        result = zip_longest([ship['hp'] for ship in battle_report["selfShipResults"]],
                        [i['hp'] for i in battle_report['enemyShipResults']])
        _logger.debug(
            '\n' + "\n".join(["{}     {}".format(a, b) for a, b in result]))


class Mission(object):
    """docstring for Mission"""

    def __init__(self, mission_name, mission_code, ze: zemulator.ZjsnEmulator):
        super().__init__()
        self.enable = False
        self.mission_code = mission_code
        self.mission_name = mission_name
        self.state = State(name=self.mission_name, on_exit=self.start)
        self.ze = ze
        self.first_nodes = []
        f_node = self.set_first_nodes()
        if type(f_node) == Node:
            self.first_nodes.append(f_node)
        elif type(f_node) == list:
            self.first_nodes.extend(f_node)

        self.available = False
        self.count = 0
        self.success_count = 0
        self.success = False

        self.boss_hp = -1
        self.current_node = None

        self.skip_margin = 0

    def __repr__(self):
        return self.mission_name

    def switch(self):
        self.enable = not self.enable

    @property
    def trigger(self):
        return {'trigger': 'go_out',
                'prepare': self._prepare,
                'source': 'init',
                'dest': self.state.name,
                'conditions': [self.condition],
                'after': 'go_back',
                }

    @property
    def back_trigger(self):
        return {'trigger': 'go_back',
                'source': self.state.name,
                'dest': 'init',
                'after': [self.postprocessing],
                }

    def condition(self):
        return self.available

    def get_working_fleet(self):
        if self.ze.version < self.ze.KEY_VERSION:
            fleet_avilable = next(filter(lambda x: x['status'] == 0 and x['ships'], self.ze.fleet), None)
            # [int(i) for i in range(1, 5) if str(
            #     i) not in [e['fleetId'] for e in self.ze.pveExplore]][0]
            if fleet_avilable:
                self.ze.working_fleet = fleet_avilable['id']
                return True
        else:
            if self.ze.drop500:
                return False
            # self.ze.working_fleet = 2
            return True

    def _prepare(self):
        if not (self.get_working_fleet() and self.enable):
            self.available = False
            return
        self.available = self.prepare()
        self.ze.supply_workingfleet()
        if self.available:
            try:
                self.ze.go_out(self.mission_code)
            except zemulator.ZjsnError as e:
                _logger.warning(e)
                self.ze.go_home()
                self.available = False

    def prepare(self):
        raise NotImplementedError()

    def set_first_nodes(self):
        raise NotImplementedError()

    def node_chain(self, nodes: List[Node]):
        last_node = nodes[0]
        for node in nodes[1:]:
            last_node.add_next(node)
            last_node = node
        return nodes[0]

    def start(self):
        self.success = False
        self.skip_margin = 0

        first_node_name = Node('0')._node_name(self.ze.go_next())
        node = 0
        for n in self.first_nodes:
            if n.name == first_node_name:
                node = n
        if node:
            self.count += 1
        else:
            return

        while type(node) == Node:
            self.current_node = node
            new_node = node.deal(self)
            node = new_node

        if node == None:
            self.success = True
            self.success_count += 1

        if self.current_node.boss_hp != -1:
            self.boss_hp = self.current_node.boss_hp

        self.summery()
        # self.postprocessing()

    def postprocessing(self):
        self.ze.auto_strengthen()
        self.ze.dismantle()
        self.ze.cleanup_equipment()

    def summery(self):
        if self.success:
            _logger.info("{} {} 次, 共有{}船, result:{}".format(
                self.mission_name, self.success_count,
                len(self.ze.userShip),
                [(i.name, i.level) for i in self.ze.working_ships]))


class Explore(Mission):
    """docstring for Explore"""

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Explore, self).__init__('explore', 0, ze)
        self.ze = ze
        self.avilable = True
        # 第一项是远征需要用到的船 第二项是远征目标
        self.explore_table = [[[0, 0, 0, 0, 0, 0], '10003'],
                              [[0, 0, 0, 0, 0, 0], '50003'],
                              [[0, 0, 0, 0, 0, 0], '40001'],
                              [[0, 0, 0, 0, 0, 0], '20001']]
        self.state.ignore_invalid_triggers = True

    def init_table(self):
        if self.explore_table[0][0][0] == 0:
            for i in self.ze.pveExplore:
                fleet_index = int(i['fleetId']) - 1
                self.explore_table[fleet_index][0] = self.ze.fleet[fleet_index]['ships']
                self.explore_table[fleet_index][1] = i['exploreId']


    def prepare(self):
        pass

    def set_first_nodes(self):
        pass

    # DeprecationWarning
    def _prepare(self):
        self.init_table()
        exploring_fleet = [e['fleetId'] for e in self.ze.pveExplore]
        if self.ze.version < self.ze.KEY_VERSION:
            self.ze.go_home()
            for i, table in enumerate(self.explore_table):
                if str(i + 1) not in exploring_fleet and 0 not in table[0]:
                    explore_fleet = str(i + 1)
                    if self.ze.fleet_ships_id(explore_fleet) != table[0]:
                        self.ze.instant_fleet(explore_fleet, table[0])
                    self.ze.supply_fleet(explore_fleet)
                    self.ze.explore(explore_fleet, table[1])

    def check_explore(self):
        self.ze.get_all_explore()        
        exploring_fleet = [e['fleetId'] for e in self.ze.pveExplore]
        running_explore = [e['exploreId'] for e in self.ze.pveExplore]
        for i, table in enumerate(self.explore_table):
            fleet_id = i + 5
            if str(fleet_id) not in exploring_fleet and 0 not in table[0] and table[1] not in running_explore:
                if self.ze.fleet_ships_id(fleet_id) != table[0]:
                    self.ze.instant_fleet(fleet_id, table[0])
                self.ze.supplyFleet(fleet_id)
                self.ze.explore(fleet_id, table[1])
                _logger.debug("fleet {} start explore {}".format(fleet_id, table[1]))


    def start(self):
        pass

    def get_explore(self):
        explore_over_fleet = self.ze.get_explore()
        self.ze.relogin()
        self.ze.repair_all(0)
        self.ze.get_award()
        self.ze.auto_build()
        self.ze.auto_build_equipment()
        if explore_over_fleet:
            self.ze.working_fleet = explore_over_fleet
            return True
        else:
            return self.get_working_fleet()


class Campaign(Mission):
    """docstring for Campaign"""

    def __init__(self, ze: zemulator.ZjsnEmulator, target_mission=None, formation_code=None):
        super().__init__('campaign', target_mission, ze)
        self.ze = ze
        self.avilable = True
        self.state.ignore_invalid_triggers = True
        self.ships_id = []
        self.formation_code = formation_code
        self.target_mission = target_mission

    def prepare(self):
        if self.ze.campaign_num > 0:
            if self.target_mission:
                self.mission_code = self.target_mission
            else:
                mc = ((self.ze.campaign_num + 1)  // 2)
                self.mission_code = min(mc, 4) * 100 + 2
            rsp = self.ze.get(self.ze.api.campaignGetFleet(self.mission_code))
            self.ships_id = [int(i) for i in rsp['campaignLevelFleet'] if i != 0]
            if not any([self.ze.userShip[i].should_be_repair(1) or self.ze.userShip[i].status == 2 for i in
                        self.ships_id]):
                try:
                    self.ze.get(self.ze.api.supplyBoats(self.ships_id))
                    return True
                except zemulator.ZjsnError as zerror:
                    _logger.warning(zerror)
                    return False
            else:
                return False

    def set_first_nodes(self):
        pass

    def _prepare(self):
        pass

    def start(self):

        if not self.formation_code:
            if self.mission_code == 302:
                self.formation_code = 5
            else:
                self.formation_code = 2

        _logger.info('start campaign {}, remain {} times'.format(self.mission_code, self.ze.campaign_num))
        self.ze.get(self.ze.api.campaignSpy(self.mission_code))
        result_before_night = self.ze.get(self.ze.api.campaignDeal(self.mission_code, self.formation_code))
        time.sleep(30)

        report = result_before_night["warReport"]
        if not any(report["hpBeforeNightWarEnemy"]):
            night_flag = 0
        else:
            night_flag = 1
            _logger.debug('night battle')

        self.battle_result = self.ze.get(self.ze.api.campaignResult(night_flag))
        self.ze.userShip.update(self.battle_result["shipVO"])
        battle_report = self.battle_result["warResult"]
        result = zip([ship['hp'] for ship in battle_report["selfShipResults"]],
                     [i['hp'] for i in battle_report['enemyShipResults']])
        _logger.debug(
            '\n' + "\n".join(["{}     {}".format(a, b) for a, b in result]))
        if 'campaignVo' in self.battle_result:
            self.ze.campaign_num = int(self.battle_result['campaignVo']['passInfo']['remainNum'])
        else:
            self.ze.get_campaign_data()


class Challenge(Mission):
    """docstring for Challenge"""

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Challenge, self).__init__('challenge', 0, ze)
        self.ze = ze
        self.available = True
        self.ship_list = []
        self.friends = []
        self.old_fleet = []
        self.challenge_list = {}
        self.friend_available = False
        self.last_challenge_time = datetime.fromtimestamp(0, tz=self.ze.tz)
        self.last_friend_time = datetime.fromtimestamp(0, tz=self.ze.tz)

        self.start_point = 0
        self.ninghai = None

    def prepare(self):
        pass

    def set_first_nodes(self):
        pass

    def init_friends(self):
        if not self.friends:
            r_f = self.ze.get(self.ze.url_server + '/friend/getlist/')
            f_list = r_f['list']
            f_list.sort(key=lambda x: int(x['level']), reverse=True)
            self.friends = [i['uid'] for i in f_list][:3]

    def generate_challenge_ships(self):
        ships = self.ze.userShip.unique
        # sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True)
        return [s.id for s in ships if s.type in ['战列', '战巡', '航母']]

    def _prepare(self):
        if not self.ship_list:
            ship_list = self.generate_challenge_ships()
        else:
            ship_list = self.ship_list
        self.init_friends()
        if not self.get_working_fleet():
            self.available = False
            return

        self.challenge_list = {}
        self.friend_available = False

        check_points = [self.ze.now.replace(hour=0, minute=0), self.ze.now.replace(
            hour=12), self.ze.now.replace(hour=18, minute=0)]
        for p in check_points:
            if self.last_challenge_time < p < self.ze.now:
                self.available = True

        if not self.available:
            return

        self.ze.go_home()
        self.old_fleet = self.ze.working_ships_id.copy()
        r1 = self.ze.get(self.ze.url_server + "/pvp/getChallengeList/")

        for i in r1["list"]:
            if i["resultLevel"] == 0:
                enemy_ships = [zemulator.ZjsnShip(s) for s in i["shipInfos"]]
                self.challenge_list.update({i['uid']: enemy_ships})

        r_f = self.ze.get(
            self.ze.url_server + '/friend/visitorFriend/' + str(self.friends[0]))
        if r_f['challengeNum'] == 0:
            self.friend_available = True

        # 去掉满级船和养殖结束的船
        battle_fleet_full = [s for s in ship_list + self.farm_ships() if self.fleet_filter(s)]
        battle_fleet = []
        evo_cids = []
        for s_id in battle_fleet_full:
            s = self.ze.userShip[s_id]
            if s.evoCid not in evo_cids:
                evo_cids.append(s.evoCid)
                battle_fleet.append(s.id)
        if len(battle_fleet) < 6:
            self.battle_fleet = ship_list[:6]
        else:
            self.battle_fleet = battle_fleet[:6]

        # 按照大炮，小船，航母的顺序编队
        ships_a = []
        ships_b = []
        ships_c = []
        for s_id in self.battle_fleet:
            ship = self.ze.userShip[s_id]
            if ship.type in ['战列', '战巡', '航战']:
                ships_a.append(s_id)
            elif ship.type in ['航母', '装母', '轻母']:
                ships_c.append(s_id)
            else:
                ships_b.append(s_id)

        self.battle_fleet = ships_a + ships_b + ships_c

        if self.challenge_list or self.friend_available:
            self.ze.instant_workingfleet(self.battle_fleet)
            self.available = True
        else:
            self.available = False

        self.last_challenge_time = self.ze.now

    def farm_ships(self):
        farm_ships = [s.id for s in self.ze.userShip.level_order() if all([s.name in ['罗德尼', '纳尔逊'],
                                                                           not s.evolved,
                                                                           s.level < s.evoLevel])]
        return farm_ships

    def formation_for_fish(self, fish_num):
        # 所有装了声呐的反潜船
        as_ships = []
        for ship in self.ze.userShip.unique:
            conditions = [self.ze.max_level > ship.level,
                          ship.type in ['驱逐', '轻母', '轻巡'],
                          "10008321" in ship.equipment or "10008421" in ship.equipment
                          or ship.type == '轻母',  # 带着声呐
                          ]
            if all(conditions):
                as_ships.append(ship.id)
        _logger.debug(
            "as_ships:{}".format([self.ze.userShip[ship_id].name for ship_id in as_ships]))

        new_fleet = self.battle_fleet[:]
        new_fleet[-(int((fish_num + 1)/2)):] = as_ships  # 干死那条鱼
        new_fleet = new_fleet[:6]

        self.ze.instant_workingfleet(new_fleet)
        return new_fleet

    def start(self):
        _logger.debug("challenge fleet:{}".format(
            [(si.name, si.level) for si in self.ze.working_ships]))
        for enemy_uid in self.challenge_list:
            self.fight(enemy_uid)
        if self.friend_available:
            for friend_uid in self.friends:
                self.fight(friend_uid, friend=True)
        _logger.debug("finish")

    def fleet_filter(self, ship_id):
        """"""
        ship = self.ze.userShip[ship_id]
        condition = ship.level < self.ze.max_level and ship.available and ship.fleet_able
        return condition

    def fight(self, enemy_uid, friend=False):
        if friend:
            api = 'friend'
        else:
            api = 'pvp'
        night_flag = 1

        n = self.start_point
        _logger.debug(enemy_uid)
        if self.ninghai:
            ninghai_fleet = [self.ninghai]
            self.ze.instant_workingfleet(ninghai_fleet)
            r1 = self.ze.get(
                self.ze.url_server + "/{}/spy/{}/{}".format(api, enemy_uid, self.ze.working_fleet))
            # _logger.debug('enemy level: {}'.format([s['level'] for s in r1['enemyVO']['enemyShips']]))
            r2 = self.ze.get(
                self.ze.url_server + "/{}/challenge/{}/{}/1/".format(api, enemy_uid, self.ze.working_fleet))

        self.ze.go_home()
        if friend:
            fish_num = 0
        else:
            enemy_ships = self.challenge_list[enemy_uid]
            staff = "\n".join(
                [str([s.name, s.level]) for s in enemy_ships])
            ships_type = [s.type for s in enemy_ships]
            fish_num = ships_type.count('潜艇') + ships_type.count('炮潜')
            if fish_num:
                _logger.debug("****有鱼****")
            _logger.debug("\n" + staff)
        if fish_num == 0:
            self.ze.instant_workingfleet(self.battle_fleet)
        else:
            self.formation_for_fish(fish_num)

        if fish_num < 2:
            battle_formation = 4
        else:
            battle_formation = 5

        over = False
        while not over:
            _logger.debug("SL {} 次".format(n))
            self.ze.go_home()
            r1 = self.ze.get(
                self.ze.url_server + "/{}/spy/{}/{}".format(api, enemy_uid, self.ze.working_fleet))
            r2 = self.ze.get(
                self.ze.url_server + "/{}/challenge/{}/{}/{}/".format(api, enemy_uid, self.ze.working_fleet,
                                                                      battle_formation))
            n += 1

            report = r2["warReport"]
            result = zip(
                report["hpBeforeNightWarSelf"], report["hpBeforeNightWarEnemy"])
            if any(report["hpBeforeNightWarEnemy"]):
                night_flag = 1
            else:
                night_flag = 0
                over = True

            if n > 200:
                over = True
            elif n > 100:
                if report["hpBeforeNightWarEnemy"][0] == 0:
                    over = True
            elif n > 50:
                if all([report["hpBeforeNightWarEnemy"].count(0) > 3,
                        report["hpBeforeNightWarSelf"].count(0) < 3,
                        report["hpBeforeNightWarEnemy"][0] == 0,
                        ]):
                    over = True
            time.sleep(2)

        time.sleep(30)
        #     for a,b in result:
        #         mlogger.debug(a+" "+b)
        # r3 = e.get(e.url_server + "/pvp/getWarResult/0/")
        r3 = self.ze.get(
            self.ze.url_server + "/{}/getWarResult/{}/".format(api, night_flag))
        _logger.debug("result level:{}".format(self.ze.result_list[int(r3["warResult"]["resultLevel"])]))
        _logger.debug("challenge fleet:{}".format(
            [(si.name, si.level) for si in self.ze.working_ships]))


class Dock(State):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__(name='init', on_enter=self.go_home)
        self.ze = ze
        self.explore_mod = Explore(self.ze)

    def go_home(self):
        self.ze.go_home()
        self.ze.repair_all(0, avoid_working_flag=True)
        self.check()

    def check(self):
        # todo change auto_explore to more strict method
        if self.ze.version < self.ze.KEY_VERSION:
            self.ze.auto_explore()
            self.ze.supply_workingfleet()
        self.ze.relogin()
        self.ze.get_award()
        self.ze.auto_build()
        self.ze.auto_build_equipment()
        self.explore_mod.check_explore()

    def wait(self):
        self.check()
        self.ze.repair_all(0)
        time.sleep(10)


class Mission_1_1(Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator, mission_name = '1-1A'):
        super(Mission_1_1, self).__init__(mission_name, 101, ze)

    def set_first_nodes(self):
        self.node_a = Node('A')
        return self.node_a

    def prepare(self):
        # 所有高级改造DD
        dd_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [ship["level"] > 20,
                          ship.type in ['驱逐'],
                          ]
            if all(conditions):
                dd_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in dd_ships]
        _logger.debug("dd_ships:{}".format([(s.name, s.level) for s in ships]))

        for i in range(1, 6):
            self.ze.ship_groups[i] = (None, 1, False)
        self.ze.ship_groups[0] = (dd_ships, 1, False)

        return self.ze.change_ships()


class TacticTrain(Mission):
    """docstring for Campaign"""
    def __init__(self, ze):
        super().__init__('TacticTrain', 101, ze)

    def set_first_nodes(self):
        self.node_a = Node('A')
        self.node_a.get_result = lambda x: True
        return self.node_a

    def prepare(self):
        # 所有练后备蛋的船
        t_r = self.ze.get(self.ze.api.getTactics())
        tt_ships = [int(i['boat_id']) for i in t_r['tactics'] if i['tactics_id']==10001774 and i['status']==1]
        if not tt_ships:
            return False
        ships = self.ze.userShip.select(tt_ships)
        _logger.debug("tt_ships:{}".format([(s.name, s.level) for s in ships]))

        self.ze.ship_groups= [(tt_ships, 2, True)] * len(tt_ships)

        return bool(self.ze.change_ships() and self.ze.get(self.ze.api.supplyBoats(tt_ships)))


class TacticTrain_Campaign(Mission):
    """docstring for Campaign"""

    def __init__(self, ze: zemulator.ZjsnEmulator, target_mission=201, formation_code=None):
        super().__init__('TacticTrain_Campaign', target_mission, ze)
        self.ze = ze
        self.ships_id = []
        self.formation_code = formation_code
        self.target_mission = target_mission

    def prepare(self):
        if self.ze.campaign_num > 0:
            t_r = self.ze.get(self.ze.api.getTactics())
            tt_ships = [[int(i['boat_id']), i['level'], i['exp']] for i in t_r['tactics'] if i['tactics_id']==10000974 and i['status']==1]
            if not tt_ships:
                return False
            self.ships_id = list(list(zip(*tt_ships))[0])
            ships_count = len(self.ships_id)
            if ships_count > 6:
                self.ships_id = self.ships_id[:6]
            elif ships_count < 6:
                self.ships_id.extend([0]*(6-ships_count))
            _logger.debug("tt_ships:{}".format([(self.ze.userShip[s].name, l, e) for s,l,e in tt_ships]))
            if self.target_mission:
                self.mission_code = self.target_mission
            else:
                mc = ((self.ze.campaign_num + 1)  // 2)
                self.mission_code = min(mc, 4) * 100 + 2
            rsp = self.ze.get(self.ze.api.campaignGetFleet(self.mission_code))
            cur_ships_id = [int(i) for i in rsp['campaignLevelFleet']]
            cur_ships_id.extend([0]*(6-len(cur_ships_id)))
            for i in range(6):                
                if cur_ships_id[i] != self.ships_id[i]:
                    self.ze.get(self.ze.api.campaignChangeFleet(self.mission_code, self.ships_id[i], i))
            broken_ships = [s.id for s in self.ze.userShip.select(self.ships_id) if s.should_be_repair(2)]
            if not self.ze.repair_ships_instant(broken_ships):
                return False

            try:
                self.ze.get(self.ze.api.supplyBoats([i for i in self.ships_id if i != 0]))
                return True
            except zemulator.ZjsnError as zerror:
                _logger.warning(zerror)
                return False

    def set_first_nodes(self):
        pass

    def _prepare(self):
        if self.enable:
            self.available = self.prepare()

    def start(self):

        if not self.formation_code:
            if self.mission_code == 302:
                self.formation_code = 5
            else:
                self.formation_code = 2

        _logger.info('start campaign {}, remain {} times'.format(self.mission_code, self.ze.campaign_num))
        self.ze.get(self.ze.api.campaignSpy(self.mission_code))
        result_before_night = self.ze.get(self.ze.api.campaignDeal(self.mission_code, self.formation_code))
        self.ze.userShip.update(result_before_night["shipVO"])
        time.sleep(30)
        self.success = True
        self.success_count += 1
        self.summery()

    def summery(self):
        if self.success:
            _logger.info("{} {} 次, 共有{}船, result:{}".format(
                self.mission_name, self.success_count,
                len(self.ze.userShip),
                [(i.name, i.level) for i in self.ze.userShip.select(self.ships_id)]))

class Mission_1_5(Mission_1_1):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_1_5, self).__init__(ze, mission_name = '1-5')
        self.mission_code = 105

    def prepare(self):
        # 所有高级改造DD
        dd_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [self.ze.max_level > ship["level"] > 20,
                          ship.type in ['驱逐'],
                          ]
            if all(conditions):
                dd_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in dd_ships]
        _logger.debug("dd_ships:{}".format([(s.name, s.level) for s in ships]))

        for i in range(1, 6):
            self.ze.ship_groups[i] = (None, 1, False)
        self.ze.ship_groups[0] = (dd_ships, 1, False)
        self.ze.ship_groups[0] = (dd_ships, 1, False)

        return self.ze.change_ships()
class Mission_2_1(Mission):

    def __init__(self, ze: zemulator.ZjsnEmulator):
        self._target_type = None
        super().__init__('type_task', 201, ze)

    @property
    def target_type(self):
        return self._target_type

    @target_type.setter
    def target_type(self, value):
        self._target_type = value
        self.node_f.enemy_target = zemulator.ZjsnShip.type_id(self._target_type)

    def set_first_nodes(self):
        self.node_b = Node('B', node_type='resource')
        self.node_d = Node('D', node_type='resource')
        self.node_f = Node('F', night_flag=1, enemy_target=self.target_type)
        self.node_b.add_next(self.node_d)
        self.node_d.add_next(self.node_f)

        return self.node_b

    def prepare(self):
        # 所有高级改造DD
        dd_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=False):
            conditions = [ship["level"] > 80,
                          ship.type in ['驱逐'],
                          ship.evolved == 1,
                          ]
            if all(conditions):
                dd_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in dd_ships]
        _logger.debug("dd_ships:{}".format([(s.name, s.level) for s in ships]))

        # 所有高级改造CV
        cv_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=False):
            conditions = [ship["level"] > 80,
                          ship.type in ['航母', '装母'],
                          ]
            if all(conditions):
                cv_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in cv_ships]
        _logger.debug("dd_ships:{}".format([(s.name, s.level) for s in ships]))

        for i in range(0, 2):
            self.ze.ship_groups[i] = (dd_ships, 1, False)
        for i in range(2, 4):
            self.ze.ship_groups[i] = (cv_ships, 1, False)
        self.ze.ship_groups[4] = self.ze.ship_groups[5] = (None, 1, False)

        return self.ze.change_ships()


class Mission_6_1_A(Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_6_1_A, self).__init__('kill_fish', 601, ze)
        self.boss_ships = []

    def set_first_nodes(self):
        node_a = Node('A', formation=5,
                      additional_spy_filter=lambda x: x["enemyVO"]["enemyFleet"]["id"] == 60102003)
        return node_a

    def auto_boss_ships(self):
        return [s.id for s in self.ze.userShip.unique if s.level < self.ze.max_level]

    def prepare(self):
        # 所有装了声呐的反潜船
        dd_ships = []
        slow_ships = []
        for ship in self.ze.userShip.unique:
            conditions = [self.ze.max_level > ship.level,
                          ship.type in ['驱逐', '轻母', '轻巡'],
                          ship.locked,
                          "10008321" in ship.equipment or "10008421" in ship.equipment
                          or ship.type == '轻母',  # 带着声呐
                          ]
            if all(conditions):
                if float(ship["battleProps"]["speed"]) > 27:  # 航速高于27
                    dd_ships.append(ship.id)
                else:
                    slow_ships.append(ship.id)
        _logger.debug(
            "dd_ships:{}".format([self.ze.userShip[ship_id].name for ship_id in dd_ships]))

        # boss_ships = [s.id for s in self.ze.userShip if s.type == '重炮' and s.locked]
        if self.boss_ships:
            if type(self.boss_ships) == list:
                boss_ships = [self.ze.userShip.name(boss_ship) for boss_ship in self.boss_ships]
            elif type(self.boss_ships) == str:
                boss_ships = [self.ze.userShip.name(self.boss_ships)]
            else:
                raise ValueError("boss_ships should be list or str")
            boss_ships = [bs.id for bs in boss_ships if self.ze.userShip[bs].level < self.ze.max_level]
        else:
            boss_ships = []

        if boss_ships:
            self.ze.ship_groups[0] = (boss_ships, 2, True)
        else:
            boss_ships = self.auto_boss_ships()
            self.ze.ship_groups[0] = (boss_ships, 1, False)
        # boss_ships = [self.ze.userShip.name('赤城').id]
        boss_ships.sort(key=lambda x: self.ze.userShip[x].level)
        _logger.debug("boss_ships:{:.60}".format(
            str([self.ze.userShip[ship_id].name for ship_id in boss_ships])))

        for i in range(1, 5):
            self.ze.ship_groups[i] = (dd_ships, 1, False)

        if any([self.ze.userShip[s].speed > 27 for s in boss_ships]):
            self.ze.ship_groups[5] = (slow_ships, 1, False)
            _logger.debug("slow_ships:{}".format(
                [self.ze.userShip[ship_id].name for ship_id in slow_ships]))
        else:
            self.ze.ship_groups[5] = (dd_ships, 1, False)

        return self.ze.change_ships()


class Mission_6_1_A_CV(Mission_6_1_A):
    def set_first_nodes(self):
        node_a = Node('A', formation=5, enemy_target=zemulator.ZjsnShip.type_id("航母"))
        return node_a

    def prepare(self):
        pass


class DailyTask(Mission):
    """日常任务"""

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('Task', 0, ze)
        self.enable = True
        self.task_solution = {2200132: Mission_1_1,
                              2200232: Mission_2_1,
                              2200332: Mission_1_1,
                              2201932: Mission_6_1_A,  # 日常潜艇
                              }
        for key in self.task_solution:
            self.task_solution[key] = self.task_solution[key](self.ze)

        self.type_mission_1 = Mission_2_1(self.ze)

        self.type_task = {
            2201232:"驱逐",
            2201332:"轻巡",
            2201432:"重巡",
            2201532:"战列",
            2201632:"轻母",
            # 2201732:"航母",
            2201832:"战巡",
            # 2201932:"潜艇",
            2200432:"驱逐",
            2200532:"轻巡",
            2200632:"重巡",
            2200732:"战列",
            2200832:"轻母",
            # 2200932:"航母",
            2201132:"战巡",
        }
        self.task_mission = None

    def _prepare(self):
        if not self.enable:
            self.available = False
            return
        # first check build tasks
        if 5200432 in self.ze.task:
            etc = self.ze.task["5200432"]["condition"][0]            
            self.ze.build_boat_remain = max(self.ze.build_boat_remain, 
                                                 etc["totalAmount"] - etc[
                                                     "finishedAmount"])
        if 5200332 in self.ze.task:
            # euqipment_task_condition
            etc = self.ze.task["5200332"]["condition"][0]
            self.ze.build_equipment_remain = max(self.ze.build_equipment_remain,
                                                 etc["totalAmount"] - etc[
                                                     "finishedAmount"])
        task_id = next(filter(lambda x: x in self.ze.task, self.task_solution), None)
        type_task_id = next(filter(lambda x: x in self.ze.task, self.type_task), None)
        if task_id or type_task_id:
            if task_id:
                self.task_mission = self.task_solution[task_id]
            elif type_task_id:
                self.task_mission = self.type_mission_1
                self.type_mission_1.target_type = self.type_task[type_task_id]
            self.task_mission.enable = True
            self.task_mission._prepare()
            self.available = self.task_mission.available
        else:
            self.available = False
        return

    def prepare(self):
        pass

    def set_first_nodes(self):
        pass

    def start(self):
        self.task_mission.start()


class Robot(object):
    """docstring for Robot"""

    # todo 把thread变成一个属性 每次start重新实例化一个thread
    def __init__(self, username, password, japan_server=False):
        super(Robot, self).__init__()
        parser = argparse.ArgumentParser("config")
        parser.add_argument("--debug", help="enable debug model", action="store_true")
        args = parser.parse_args()
        self.DEBUG = args.debug
        self.set_logger(username, japan_server)
        self.ze = zemulator.ZjsnEmulator()
        self.ze.username = username
        self.ze.password = password
        if japan_server:
            self.ze.api.location = self.ze.api.JAPAN
        self.ze.login()
        self.thread = None

        self.dock = Dock(self.ze)
        self.explore = self.dock.explore_mod

        self.campaign = Campaign(self.ze)
        states = [self.dock] + [m.state for m in [self.explore, self.campaign]]
        self.missions = {}

        self.machine = Machine(model=self, states=states, initial='init', auto_transitions=False)
        self.command = 'run'

        self.add_mission(DailyTask(self.ze))
        #kill_fish
        self.kill_fish = Mission_6_1_A(self.ze)
        self.add_mission(self.kill_fish)
        if self.ze.version < self.ze.KEY_VERSION:
            self.set_missions()
            self.machine.add_transition(trigger='go_out', prepare=[self.explore._prepare], source='init',
                                        dest=self.explore.mission_name)
            self.machine.add_transition(trigger='go_out', source=self.explore.mission_name,
                                        dest=self.explore.mission_name,
                                        conditions=[self.campaign.prepare], after=[self.campaign.start])
            self.machine.add_transition(trigger='go_out', source=self.explore.mission_name, dest='init',
                                        conditions=[self.explore.get_explore])
        else:
            self.machine.add_transition(trigger='go_out', source="init", dest="init",
                                        conditions=[self.campaign.prepare], after=[self.campaign.start])

            self.set_missions()
            self.machine.add_transition(trigger='go_out', conditions=[self.dock.wait], source='init',
                                        dest="init")
        # self.machine.add_transition(trigger='go_back', source='*', dest='init')

    def add_mission(self, mission: Mission):
        if mission.mission_name not in self.missions:
            self.missions[mission.mission_name] = mission
        else:
            raise ValueError("mission name {} is already used".format(mission.mission_name))
        self.machine.add_states(mission.state)
        self.machine.add_transition(**mission.trigger)
        self.machine.add_transition(**mission.back_trigger)

    def set_missions(self):
        pass

    def go_out(self):
        # dummy trigger method, implemented by transitions module
        pass

    def set_logger(self, username, is_japan):
        if is_japan:
            suffix = "_japan"
        else:
            suffix = ""
        log_formatter = logging.Formatter(
            '%(asctime)s: %(levelname)s: %(name)s: %(message)s')
        if os.name == 'nt' or self.DEBUG:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(log_formatter)
            logging.getLogger('transitions').addHandler(stream_handler)
            logging.getLogger('transitions').setLevel(logging.INFO)
            _logger.addHandler(stream_handler)

        file_handler = handlers.TimedRotatingFileHandler(
            '{}.log'.format(username + suffix), when='midnight', backupCount=3, encoding='utf8')
        file_handler.setFormatter(log_formatter)
        _logger.addHandler(file_handler)
        
        _logger.setLevel(logging.DEBUG)



    def working_loop(self):
        while self.command != 'stop':
            try:
                if not self.is_sleep():
                    self.go_out()
                    time.sleep(2)
                else:
                    time.sleep(600)
            except zemulator.ZjsnError as zerror:
                if zerror.eid == -101:
                    self.ze.login()
                    self.state = 'init'
                elif zerror.eid in [-9997, -9995, -9994]:
                    _logger.info("login on another device, input anything to continue")
                    wait_thread = threading.Thread(target=input)
                    wait_thread.start()
                    wait_thread.join(timeout=7200)
                    self.ze.login()
                    self.state = 'init'
                else:
                    raise zerror
            except ConnectionError:
                while self.command != 'stop':
                    _logger.error("Connection error")
                    time.sleep(600)
                    try:
                        self.ze.login()
                        self.state = 'init'
                        break
                    except ConnectionError:
                        pass

    def is_sleep(self) -> bool:
        # sleep in 0:00 to 6:00

        if os.name == 'nt':
            return False

        if self.ze.now.replace(hour=0, minute=0) < self.ze.now < self.ze.now.replace(hour=6):
            return True
        else:
            return False

    def run(self):
        last_error_time = 0
        error_count = 0
        while 1:
            try:
                # check dock, equipment, tasks before any transitions
                self.dock.check()
                self.working_loop()
            except Exception as e:
                # reset error count everyday
                if last_error_time - time.time() > 24 * 60 * 60:
                    error_count = 0
                last_error_time = time.time()
                error_count += 1
                _logger.exception(e)
                if self.DEBUG or error_count > 3:
                    raise e
                else:
                    self.ze.login()
                # disable mission where this error occurs
                if self.state in self.missions:
                    current_mission = self.missions[self.state]
                    current_mission.enable = False
                    _logger.error("{} is disabled".format(current_mission))
                    # init state
                    self.state = 'init'
                time.sleep(10)


    def start(self):
        if os.name == 'nt' or self.DEBUG:
            self.run()
        else:
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            import signal
            signal.signal(signal.SIGTSTP, lambda x,y: exit())            
            return self.thread
