import time
import string
import random
import logging
import threading
import collections
from datetime import datetime

from transitions import State
from transitions import Machine
# from transitions.extensions import GraphMachine as Machine

import zemulator

_logger = logging.getLogger('zjsn.zrobot')


class Node(object):

    """docstring for Node"""
    _node_types = ['simple', 'resource', 'skip']

    def __init__(self, name,
                 node_type='simple',
                 formation=2,
                 night_flag=0,
                 big_broken_protect=True,
                 enemy_target=None,
                 enemy_avoid=None,
                 additional_spy_filter=None):
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

        self.sleep_mu = 30
        self.sleep_sigma = 2
        rd = random.normalvariate(self.sleep_mu, self.sleep_sigma)
        if rd < self.sleep_mu - 3 * self.sleep_sigma or rd > self.sleep_mu + 3 * self.sleep_sigma:
            self.battle_length = self.sleep_mu
        else:
            self.battle_length = rd

        self.additional_spy_filter = additional_spy_filter

        self.boss_hp = -1

    def add_next(self, next_nodes):
        if isinstance(next_nodes, collections.Iterable):
            self.next_nodes.extend(next_nodes)
        else:
            self.next_nodes.append(next_nodes)
        return

    def _node_name(self, node_id):
        return string.ascii_uppercase[int(str(node_id)[-2:]) - 2]

    def spy_filter(self, spy_result):
        if 'enemyVO' not in spy_result:
            return True
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

    def deal(self, ze: zemulator.ZjsnEmulator):
        _logger.info('进入 {} 点'.format(self._node_name(ze.node)))
        if self.node_type == 'simple':
            spy_result = ze.spy()
            if self.spy_filter(spy_result):
                try:
                    result_before_night = ze.deal(
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

                self.battle_result = ze.getWarResult(night_flag)
                if "bossHp" in self.battle_result:
                    self.boss_hp = int(self.battle_result['bossHp'])
                elif 'bossHpLeft' in self.battle_result:
                    self.boss_hp = int(self.battle_result['bossHpLeft'])
                battle_report = self.battle_result["warResult"]
                result = zip([ship['hp'] for ship in battle_report["selfShipResults"]],
                             [i['hp'] for i in battle_report['enemyShipResults']])
                # todo 增加战斗评价
                _logger.debug(
                    '\n' + "\n".join(["{}     {}".format(a, b) for a, b in result]))

                # if 'newShipVO' in self.battle_result:
                #     new_ship = zemulator.ZjsnShip(
                #         self.battle_result['newShipVO'][0])
                #     if new_ship.cid not in ze.unlockShip:
                #         _logger.info('get new ship: {}'.format(new_ship.name))
                #     else:
                #         _logger.debug('get: {}'.format(new_ship.name))
            else:
                return 0

        elif self.node_type == 'resource':
            if ze.working_ships[0].should_be_repair(2):
                return 0
            else:
                self.battle_result = ze.deal(1, big_broken_protect=False)

        elif self.node_type == 'skip':
            self.battle_result = ze.skip()
            if not self.battle_result:
                return 0

        if self.next_nodes:
            next_node_id = ze.go_next()
            next_node = self._node_name(next_node_id)
            for n_node in self.next_nodes:
                if n_node.name == next_node:
                    return n_node
        else:
            return None


class Mission(object):

    """docstring for Mission"""

    def __init__(self, mission_name, mission_code, ze: zemulator.ZjsnEmulator):
        super().__init__()
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

    def __repr__(self):
        return self.mission_name

    @property
    def trigger(self):
        return {'trigger': 'go_out',
                'prepare': self._prepare,
                'source': 'init',
                'dest': self.state.name,
                'conditions': [self.condition],
                'after': 'go_back',
                }

    def condition(self):
        return self.available

    def get_working_fleet(self):
        # if len(self.ze.pveExplore) == 4:
        #     self.available = False
        #     return False
        fleet_avilable = next(filter(lambda x: x['status']==0 and x['ships'], self.ze.fleet), None)
        # [int(i) for i in range(1, 5) if str(
        #     i) not in [e['fleetId'] for e in self.ze.pveExplore]][0]
        if fleet_avilable:
            self.ze.working_fleet = fleet_avilable['id']
            return True

    def _prepare(self):
        if not self.get_working_fleet():
            self.available = False
            return
        self.available = self.prepare()
        self.ze.supply()
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

    def start(self):
        self.success = False
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
            new_node = node.deal(self.ze)
            node = new_node

        if node == None:
            self.success = True
            self.success_count += 1

        if self.current_node.boss_hp != -1:
            self.boss_hp = self.current_node.boss_hp

        self.summery()
        self.postprocessing()

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

class Mission_6_1_A(Mission):

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_6_1_A, self).__init__('kill_fish', 601, ze)

    def set_first_nodes(self):
        node_a = Node('A', formation=5,
                      additional_spy_filter=lambda x: x["enemyVO"]["enemyFleet"]["id"] == 60102003)
        return node_a

    def prepare(self):
        # 所有装了声呐的反潜船
        dd_ships = []
        slow_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=False):
            conditions = [100 > ship["level"],
                          ship.type in ['驱逐', '轻母', '轻巡'],
                          "10008321" in ship["equipment"] or "10008421" in ship[
                              "equipment"] or ship.type == '轻母',  # 带着声呐
                          ]
            if all(conditions):
                if float(ship["battleProps"]["speed"]) > 27:  # 航速高于27
                    dd_ships.append(ship.id)
                else:
                    slow_ships.append(ship.id)
        _logger.debug(
            "dd_ships:{}".format([self.ze.userShip[ship_id].name for ship_id in dd_ships]))

        # boss_ship = [s.id for s in self.ze.userShip if s.type == '重炮' and s.locked]
        # boss_ships = [s.id for s in self.ze.userShip if s.type == '潜艇' and s.level < 50]
        boss_ships = [20936]
        boss_ships.sort(key=lambda x:self.ze.userShip[x].level)
        _logger.debug("boss_ships:{}".format(
            [self.ze.userShip[ship_id].name for ship_id in boss_ships]))

        # self.ze.ship_groups[0] = (dd_ships, 1, False)
        self.ze.ship_groups[0] = (boss_ships, 1, False)

        for i in range(1, 5):
            self.ze.ship_groups[i] = (dd_ships, 1, False)

        if any([self.ze.userShip[s].speed > 27 for s in boss_ships]):
            self.ze.ship_groups[5] = (slow_ships, 1, False)
            _logger.debug("slow_ships:{}".format(
                [self.ze.userShip[ship_id].name for ship_id in slow_ships]))
        else:
            self.ze.ship_groups[5] = (dd_ships, 1, False)

        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

    # def postprocessing(self):
    #     if self.success:
    #         target_ship = 43707
    #         if self.ze.strengthen(target_ship) == -1:
    #             # self.ze.auto_skill(target_ship)
    #             _logger.info('{} 强化好了'.format(self.ze.userShip[target_ship].name))
    #         else:
    #             s = self.ze.userShip[target_ship]
    #             _logger.debug("{} exp remain: {}".format(s.name, s.strength_exp))
    #         super().postprocessing()


class Explore(Mission):

    """docstring for Explore"""

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Explore, self).__init__('explore', 0, ze)
        self.ze = ze
        self.avilable = True
        # 第一项是远征需要用到的船 第二项是远征目标
        self.explore_table = (([35442, 35500, 3846, 7376, 183, 103], '10003'),
                              ([14174, 7367, 3877, 13972, 11497, 8452],
                               '50003'),
                              ([128, 14094, 113, 101, 577, 7373], '40001'),
                              ([123, 13973, 27865, 14138, 10706, 104], '20001'))
        self.state.ignore_invalid_triggers = True

    def prepare(self):
        pass

    def set_first_nodes(self):
        pass

    def _prepare(self):
        self.ze.go_home()
        self.fleet_is_free = False
        exploring_fleet = [e['fleetId'] for e in self.ze.pveExplore]
        for i, table in enumerate(self.explore_table):
            if str(i + 1) not in exploring_fleet:
                self.ze.working_fleet = str(i + 1)
                if self.ze.working_ships_id != table[0]:
                    self.ze.instant_fleet(table[0])
                self.ze.supply()
                self.ze.explore(self.ze.working_fleet, table[1])

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

class Campaign(Mission):

    """docstring for Campaign"""

    def __init__(self, ze: zemulator.ZjsnEmulator, mission_code=202, formation_code=2):
        super().__init__('campaign', mission_code, ze)
        self.ze = ze
        self.avilable = True
        self.state.ignore_invalid_triggers = True
        self.ships_id = []
        self.formation_code = formation_code

    def prepare(self):
        if self.ze.campaign_num > 0:
            if not self.ships_id:
                rsp = self.ze.get(self.ze.api.campaignGetFleet(self.mission_code))
                self.ships_id = [int(i) for i in rsp['campaignLevelFleet']]
            if not any([self.ze.userShip[i].should_be_repair(1) or self.ze.userShip[i].status == 2 for i in self.ships_id]):
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
            self.ze.campaign_num = self.battle_result['campaignVo']['passInfo']['remainNum']
        else:
            self.ze.get_campaign_data()


class Challenge(Mission):

    """docstring for Challenge"""

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Challenge, self).__init__('challenge', 0, ze)
        self.ze = ze
        self.available = True
        self.battle_fleet = [7860, 50367, 42093, 13708, 927, 13598]
        self.friends = [2593850, 74851, 2827412]
        self.old_fleet = []
        self.challenge_list = {}
        self.friend_available = False
        self.last_challenge_time = datetime.fromtimestamp(0)
        self.last_friend_time = datetime.fromtimestamp(0)

        self.start_point = 0
        self.ninghai = 1215

    def prepare(self):
        pass

    def set_first_nodes(self):
        pass

    def _prepare(self):
        if not self.get_working_fleet():
            self.available = False
            return

        self.challenge_list = {}
        self.friend_available = False

        now = datetime.now()
        check_points = [now.replace(hour=0, minute=0), now.replace(
            hour=12, minute=0), now.replace(hour=18, minute=0)]
        for p in check_points:
            if self.last_challenge_time < p < now:
                self.available = True

        if not self.available:
            return

        self.ze.go_home()
        self.old_fleet = self.ze.working_ships_id.copy()
        r1 = self.ze.get(self.ze.url_server + "/pvp/getChallengeList/")

        for i in r1["list"]:
            if i["resultLevel"] == 0:
                _logger.debug(i["uid"])
                enemy_ships = [zemulator.ZjsnShip(s) for s in i["shipInfos"]]
                staff = "\n".join(
                    [str([s.name, s.level]) for s in enemy_ships])
                ships_type = [s.type for s in enemy_ships]
                fish_num = ships_type.count('潜艇') + ships_type.count('炮潜')
                if fish_num:
                    _logger.debug("****有鱼****")
                self.challenge_list.update({i['uid']: fish_num})

                _logger.debug("\n" + staff)

        r_f = self.ze.get(
            self.ze.url_server + '/friend/visitorFriend/' + str(self.friends[0]))
        if r_f['challengeNum'] == 0:
            self.friend_available = True


        if self.challenge_list or self.friend_available:
            self.ze.instant_fleet(self.battle_fleet)
            self.available = True
        else:
            self.available = False

        self.last_challenge_time = datetime.today()


    def formation_for_fish(self, fish_num):
        fish_fleet = self.battle_fleet[:]
        if fish_num == 1:
            fish_fleet[1] = 367  # 干死那条鱼
        if fish_num == 2:
            fish_fleet[-1] = 1215  # 干死那2条鱼
        if fish_num == 3:
            fish_fleet[-2:] = [367, 1215]  # 干死那3条鱼
        if fish_num == 4:
            fish_fleet[-2:] = [11063, 1215]  # 干死那4条鱼
        if fish_num > 4:
            fish_fleet[-3:] = [32549, 11063, 1215]
        self.ze.instant_fleet(fish_fleet)
        return fish_fleet

    def start(self):
        _logger.debug("challenge fleet:{}".format(
            [(si.name, si.level) for si in self.ze.working_ships]))
        for enemy_uid in self.challenge_list:
            self.fight(enemy_uid)
        if self.friend_available:
            for friend_uid in self.friends:
                self.fight(friend_uid, friend=True)
        _logger.debug("finish")

    def fight(self, enemy_uid, friend=False):
        if friend:
            api = 'friend'
        else:
            api = 'pvp'
        night_flag = 1
        n = self.start_point
        _logger.debug(enemy_uid)
        ninghai_fleet = [self.ninghai]
        self.ze.instant_fleet(ninghai_fleet)
        r1 = self.ze.get(
            self.ze.url_server + "/{}/spy/{}/{}".format(api, enemy_uid, self.ze.working_fleet))
        _logger.debug('enemy level: {}'.format([s['level'] for s in r1['enemyVO']['enemyShips']]))
        r2 = self.ze.get(
            self.ze.url_server + "/{}/challenge/{}/{}/1/".format(api, enemy_uid, self.ze.working_fleet))

        self.ze.go_home()
        if friend:
            fish_num = 0
        else:
            fish_num = self.challenge_list[enemy_uid]
        if fish_num == 0:
            self.ze.instant_fleet(self.battle_fleet)
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
        _logger.debug("result level:{}".format(r3["warResult"]["resultLevel"]))


class Mission_5_2_C(Mission):

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_5_2_C, self).__init__('5-2C', 502, ze)

    def set_first_nodes(self):
        self.node_c = Node('C', enemy_target='轻母')
        self.node_f = Node('F')
        self.node_h = Node('H')
        self.node_i = Node('I')
        self.node_j = Node(
            'J', formation=4, night_flag=1, big_broken_protect=False)
        self.node_c.add_next(self.node_f)
        self.node_f.add_next([self.node_i, self.node_h])
        self.node_i.add_next(self.node_j)
        self.node_h.add_next(self.node_j)
        return self.node_c

    def prepare(self):
        # 所有水下船只
        if 10018811 in self.ze.unlockShip:
            self.available = False
            _logger.info('有北京风了，2-5已经毕业')
            return
        ss_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [ship["level"] > 1,
                          ship.type in ['潜艇', '炮潜'],
                          ]
            if all(conditions):
                ss_ships.append(ship.id)
        _logger.debug("ss_ships:{}".format(
            [(self.ze.userShip[ship_id].name, self.ze.userShip[ship_id].level) for ship_id in ss_ships]))

        for i in range(0, 6):
            self.ze.ship_groups[i] = (ss_ships, 1, False)
        self.ze.ship_groups[0][0].insert(0, 6744)  # 尽可能狼群U47旗舰
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError as zerror:
            _logger.critical(zerror)
            return False
        return True


class Mission_2_5_mid(Mission):

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_2_5_mid, self).__init__('2-5mid', 205, ze)

    def set_first_nodes(self):
        self.node_a = Node('A')
        self.node_b = Node('B')
        self.node_d = Node('D', node_type='skip')
        self.node_h = Node('H', node_type='skip')
        self.node_k = Node('K', node_type='skip')
        self.node_o = Node('O', night_flag=1)

        self.node_a.add_next(self.node_b)
        self.node_b.add_next(self.node_d)
        self.node_d.add_next(self.node_h)
        self.node_h.add_next(self.node_k)
        self.node_k.add_next(self.node_o)
        return self.node_a

    def prepare(self):
        # 所有高级潜艇
        if 10026711 in self.ze.unlockShip:
            self.available = False
            _logger.info('有岛风了，2-5中路已经毕业')
            return
        ss_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [ship["level"] > 60,
                          ship.type in ['潜艇'],
                          ]
            if all(conditions):
                ss_ships.append(ship.id)
        _logger.debug("ss_ships:{}".format(
            [(self.ze.userShip[ship_id].name, self.ze.userShip[ship_id].level) for ship_id in ss_ships]))

        taitai = [566, 115]

        cv_ships = []
        # 所有高速，高级航母
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [ship["level"] > 75,
                          ship.type in ['航母', '装母'],
                          ship.speed > 30,
                          ship.id not in taitai,
                          ]
            if all(conditions):
                cv_ships.append(ship.id)
        cv_ships.extend(taitai)
        _logger.debug("cv_ships:{}".format(
            [(self.ze.userShip[ship_id].name, self.ze.userShip[ship_id].level) for ship_id in cv_ships]))

        self.ze.ship_groups[0] = ([16523], 0.7, True)  # 飙车胡德
        self.ze.ship_groups[1] = self.ze.ship_groups[2] = (ss_ships, 0, False)
        self.ze.ship_groups[3] = self.ze.ship_groups[5] = (cv_ships, 0.7, False)
        self.ze.ship_groups[4] = (taitai, 0.7, True)
        # self.ze.ship_groups[3][0].insert(0,13664)  # 大凤优先4号位置
        self.ze.ship_groups[3] = ([13664], 0.7, True)  # 大凤
        self.ze.ship_groups[4] = ([115], 0.7, True)  # 太太
        self.ze.ship_groups[5] = ([43707], 0.7, True)  # 加加

        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True


class Mission_5_5_C(Mission):

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_5_5_C, self).__init__('5-5C', 505, ze)

    def set_first_nodes(self):
        self.node_c = Node('C', formation=4,
                           additional_spy_filter=lambda sr: '战巡' in str(sr) or '航母'in str(sr))
        self.node_f = Node('F')
        self.node_i = Node('I', formation=4, night_flag=1)
        self.node_c.add_next(self.node_f)
        self.node_f.add_next(self.node_i)
        return self.node_c

    def prepare(self):
        # 所有90级以上水下船只
        ss_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [ship["level"] > 90,
                          ship.type in ['潜艇', '炮潜'],
                          ]
            if all(conditions):
                ss_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in ss_ships]
        _logger.debug("ss_ships:{}".format([(s.name, s.level) for s in ships]))

        for i in range(0, 6):
            self.ze.ship_groups[i] = (ss_ships, 1, False)
        self.ze.ship_groups[0][0].insert(0, 6744)  # 尽可能狼群U47旗舰
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True


class Mission_5_5_B(Mission):

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_5_5_B, self).__init__('5-5B', 505, ze)

    def set_first_nodes(self):
        self.node_b = Node('B', additional_spy_filter=lambda sr: '战巡' in str(sr) or '雷巡'in str(sr))
        return self.node_b

    def prepare(self):
        boss_ships = [9210, 5324] # 牛仔级
        cv_ship = [43707]
        # 所有改造后的ca, 等级从低到高
        ca_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=False):
            conditions = [ship["level"] < 100,
                          ship.type in ['重巡'],
                          ship.evolved,
                          ]
            if all(conditions):
                ca_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in ca_ships]
        _logger.debug("ca_ships:{}".format([(s.name, s.level) for s in ships]))

        for i in range(1, 5):
            self.ze.ship_groups[i] = (ca_ships, 1, False)

        self.ze.ship_groups[0] = (boss_ships, 1, True)
        self.ze.ship_groups[5] = (cv_ship, 1, True)
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

class Mission_2_5_down(Mission):

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_2_5_down, self).__init__('2-5down', 205, ze)

    def set_first_nodes(self):
        self.node_a = Node('A', additional_spy_filter=lambda sr: len(sr['enemyVO']['enemyShips'])==5)
        # self.node_a = Node('A', node_type='skip')
        self.node_b = Node('B')
        self.node_e = Node('E', node_type='resource')
        self.node_i = Node('I')
        self.node_l = Node('L', night_flag=1, formation=4)
        self.node_m = Node('M', night_flag=1, formation=4)
        self.node_n = Node('N', night_flag=1, formation=4)

        self.node_a.add_next(self.node_b)
        self.node_b.add_next(self.node_e)
        self.node_e.add_next(self.node_i)
        # self.node_i.add_next(self.node_l) # 不用去了，苍龙有了
        # self.node_i.add_next(self.node_m) # 不用去了，比睿有了
        self.node_i.add_next(self.node_n)
        return self.node_a

    def prepare(self):
        # 所有能开幕的水下船只
        ss_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [ship["level"] > 11,
                          ship.type in ['潜艇', '炮潜'],
                          ]
            if all(conditions):
                ss_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in ss_ships]
        _logger.debug("ss_ships:{}".format([(s.name, s.level) for s in ships]))

        for i in range(0, 6):
            self.ze.ship_groups[i] = (ss_ships, 0, False)
        self.ze.ship_groups[0][0].insert(0, 6744)  # 尽可能狼群U47旗舰
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

class Mission_6_3(Mission):

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_6_3, self).__init__('6-3', 603, ze)

    def set_first_nodes(self):
        self.node_b = Node('B', enemy_target=zemulator.ZjsnShip.type_id('重巡'), formation=4)
        # self.node_a = Node('A', node_type='skip')
        self.node_e = Node('E', formation=4)
        self.node_h = Node('H', formation=4)
        self.node_j = Node('J', formation=4, night_flag=1)

        self.node_b.add_next(self.node_e)
        self.node_e.add_next(self.node_h)
        self.node_h.add_next(self.node_j)
        return self.node_b

    def prepare(self):
        if 10010413 in self.ze.unlockShip:
            _logger.info('有厌战了')
            return False
        # 所有能开幕的水下船只
        ss_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [ship["level"] > 11,
                          ship.type in ['潜艇', '炮潜'],
                          ]
            if all(conditions):
                ss_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in ss_ships]
        _logger.debug("ss_ships:{}".format([(s.name, s.level) for s in ships]))

        for i in range(0, 6):
            self.ze.ship_groups[i] = (ss_ships, 0, False)
        self.ze.ship_groups[0][0].insert(0, 6744)  # 尽可能狼群U47旗舰
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True


class MissionPants(Mission):

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(MissionPants, self).__init__('pants', 201, ze)
        self.pants_num = 0
        self.pants_yesterday = 56

    def set_first_nodes(self):
        self.node_b = Node('B', node_type='resource')
        self.node_d = Node('D', node_type='resource')
        self.node_f = Node('F', night_flag=1, enemy_target='运输')
        self.node_b.add_next(self.node_d)
        self.node_d.add_next(self.node_f)

        return self.node_b

    def prepare(self):
        if self.ze.spoils - self.pants_yesterday >= 50:
            self.available  = False
            return

        if self.count > 100:
            _logger.warning('pants {}, SL {}'.format(self.ze.spoils - self.pants_yesterday, self.count))
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

        for i in range(0, 4):
            self.ze.ship_groups[i] = (dd_ships, 1, False)
        self.ze.ship_groups[4] = self.ze.ship_groups[5] = (None, 1, False)

        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

    def summery(self):
        if self.success:
            _logger.info("{} SL {} 次, 共捞{}胖次, result:{}".format(
                self.mission_name, self.count,
                self.ze.spoils - self.pants_yesterday,
                [(i.name, i.level) for i in self.ze.working_ships]))
            self.count = 0


class Mission_4_3(Mission):
    """一次45铝，一小时2700铝，再见了，远征铝"""
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('偷铝', 403, ze)

    def set_first_nodes(self):
        self.node_b = Node('B')
        self.node_d = Node('D', node_type='resource')

        self.node_b.add_next(self.node_d)
        self.aluminum = 0

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

        self.ze.ship_groups[0] = (dd_ships, 0, False) # 旗舰必须是完好的防止大破
        for i in range(1, 4):
            self.ze.ship_groups[i] = (dd_ships, 1, False)
        self.ze.ship_groups[4] = self.ze.ship_groups[5] = (None, 1, False)

        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

    def summery(self):
        super().summery()
        if self.success:
            if 'userResVo' in self.node_d.battle_result:
                _logger.info("资源： 油:{0[oil]:<7} 弹:{0[ammo]:<7} 钢:{0[steel]:<7} 铝:{0[aluminium]:<7}".format(self.node_d.battle_result['userResVo']))


class Mission_2_2(Mission):
    """一次17油，一小时1000油，效率高于远征，大有可为"""
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('偷油', 202, ze)

    def set_first_nodes(self):
        self.node_a = Node('A')
        self.node_c = Node('C', node_type='resource')

        self.node_a.add_next(self.node_c)

        return self.node_a

    def prepare(self):
        # 单DD偷油，擦伤就修，防止大破劝退
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

        for i in range(1, 6):
            self.ze.ship_groups[i] = (None, 1, False)
        self.ze.ship_groups[0] = (dd_ships, 0, False)

        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True


class Mission_1_1(Mission):

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_1_1, self).__init__('1-1A', 101, ze)

    def set_first_nodes(self):
        self.node_a = Node('A')
        return self.node_a

    def prepare(self):
        # 所有高级改造DD
        dd_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=False):
            conditions = [100 > ship["level"] > 80,
                          ship.type in ['驱逐'],
                          ship.evolved == 1,
                          ]
            if all(conditions):
                dd_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in dd_ships]
        _logger.debug("dd_ships:{}".format([(s.name, s.level) for s in ships]))

        for i in range(1, 6):
            self.ze.ship_groups[i] = (None, 1, False)
        self.ze.ship_groups[0] = (dd_ships, 1, False)

        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

class Mission_6_4(Mission):

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_6_4, self).__init__('6-4 两点', 604, ze)
        self.pants_num = 0

    def set_first_nodes(self):
        # self.node_a = Node('A', additional_spy_filter=lambda sr: '战巡' in str(sr) or '航母'in str(sr))
        self.node_a = Node('A', enemy_avoid='战巡')
        self.node_b = Node('B', night_flag=True)

        self.node_a.add_next(self.node_b)
        return self.node_a

    def prepare(self):
        if 10023712 in self.ze.unlockShip:
            _logger.debug('有昆特了')
            return False
        boss_ships = [44420, 9210, 5324] # 密苏里, 牛仔级
        cv_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [1 < ship["level"] < 99,
                          ship.type in ['航母'],
                          ]
            if all(conditions):
                cv_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in cv_ships]
        _logger.debug("cv_ships:{}".format([(s.name, s.level) for s in ships]))

        # 所有改造后的ca, 等级从低到高
        ca_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=False):
            conditions = [ship["level"] < 100,
                          ship.type in ['重巡'],
                          ship.evolved,
                          ]
            if all(conditions):
                ca_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in ca_ships]
        _logger.debug("ca_ships:{}".format([(s.name, s.level) for s in ships]))

        for i in range(1, 3):
            self.ze.ship_groups[i] = (ca_ships, 1, False)
        boss_ships = cv_ships
        self.ze.ship_groups[0] = (boss_ships, 1, True)
        self.ze.ship_groups[3] = self.ze.ship_groups[4] = self.ze.ship_groups[5] = (cv_ships, 1, True)
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

class Dock(State):
    def __init__(self, ze:zemulator.ZjsnEmulator):
        super().__init__(name='init', on_enter=self.go_home)
        self.ze = ze
    def go_home(self):
        self.ze.go_home()
        self.ze.auto_explore()
        self.ze.repair_all()
        self.ze.supply()


class Robot(object):

    """docstring for Robot"""
    # todo 把thread变成一个属性 每次start重新实例化一个thread
    def __init__(self):
        super(Robot, self).__init__()
        self.ze = zemulator.ZjsnEmulator()
        self.thread = None

        self.dock = Dock(self.ze)
        self.explore = Explore(self.ze)
        self.campaign = Campaign(self.ze, 402)
        self.challenge = Challenge(self.ze)
        self.m6_1 = Mission_6_1_A(self.ze)
        self.m5_2 = Mission_5_2_C(self.ze)
        self.m2_5_mid = Mission_2_5_mid(self.ze)
        self.m2_5_down = Mission_2_5_down(self.ze)
        self.m5_5_c = Mission_5_5_C(self.ze)
        self.pants = MissionPants(self.ze)
        self.m1_1a = Mission_1_1(self.ze)
        self.m4_3 = Mission_4_3(self.ze)
        self.m2_2 = Mission_2_2(self.ze)
        self.m5_5_b = Mission_5_5_B(self.ze)
        self.m6_4 = Mission_6_4(self.ze)
        self.m6_3 = Mission_6_3(self.ze)

        self.missions = [
            self.explore, self.campaign, self.challenge,
            self.m5_2, self.m6_1, self.m2_5_mid, self.m2_5_down, self.m5_5_c,
            self.pants, self.m1_1a, self.m4_3, self.m2_2, self.m5_5_b,
            self.m6_4, self.m6_3,
        ]


        self.machine = Machine(model=self, states=self.states, initial='init')
        self.command = 'run'

        self.add_transitions()
        self.machine.add_transition(trigger='go_out', prepare=[self.explore._prepare], source='init',
                                    dest=self.explore.mission_name)
        self.machine.add_transition(trigger='go_out', source=self.explore.mission_name, dest=self.explore.mission_name,
                                    conditions=[self.campaign.prepare], after=[self.campaign.start])
        self.machine.add_transition(trigger='go_out', source=self.explore.mission_name, dest='init',
                                    conditions=[self.explore.get_explore])
        self.machine.add_transition(trigger='go_back', source='*', dest='init')

    def add_transitions(self):
        self.machine.add_transition(**self.challenge.trigger)
        # self.machine.add_transition(**self.m2_5_mid.trigger)
        # self.machine.add_transition(**self.m5_5_c.trigger)
        # self.machine.add_transition(**self.m2_5_down.trigger)
        # self.machine.add_transition(**self.pants.trigger)
        # self.machine.add_transition(**self.m4_3.trigger)
        # self.machine.add_transition(**self.m2_2.trigger)
        # self.machine.add_transition(**self.m5_5_b.trigger)
        # self.machine.add_transition(**self.m6_4.trigger)
        self.machine.add_transition(**self.m6_3.trigger)

        # self.machine.add_transition(**self.m1_1a.trigger)
        # self.machine.add_transition(**self.m6_1.trigger)


    @property
    def states(self):
        return [self.dock] + [m.state for m in self.missions]

    def run(self):
        self.ze.login()
        self.ze.repair_all()
        while self.command != 'stop':
            try:
                self.go_out()
                time.sleep(2)
            except zemulator.ZjsnError as zerror:
                if zerror.eid == -101:
                    self.ze.login()
                else:
                    raise zerror

    def start(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.start()
        return self.thread


if __name__ == '__main__':
    from transitions import logger as transitions_logger
    from logging import handlers

    log_formatter = logging.Formatter(
        '%(asctime)s: %(levelname)s: %(message)s', datefmt='%H:%M:%S')
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)

    f_handler = handlers.TimedRotatingFileHandler('zrobot.log', when='midnight', backupCount=3, encoding='utf8')
    f_handler.setFormatter(log_formatter)

    _logger.addHandler(stream_handler)
    _logger.addHandler(f_handler)
    _logger.setLevel(logging.DEBUG)
    f_handler.setLevel(logging.INFO)

    transitions_logger.addHandler(stream_handler)
    transitions_logger.setLevel(logging.INFO)
    r = Robot()
    t = r.run()
