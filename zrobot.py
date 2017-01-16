import collections
import logging
import random
import string
import threading
import time
from datetime import datetime
from typing import List
from itertools import zip_longest

from transitions import Machine
from transitions import State

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
        self.skip_rate_limit = 0
        self.skip_rate = 0

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
        ze = mission.ze
        _logger.info('进入 {} 点'.format(self._node_name(ze.node)))
        if self.node_type == 'resource':
            if ze.working_ships[0].should_be_repair(2):
                return 0
            else:
                self.battle_result = ze.deal(1, big_broken_protect=False)
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
                        return 0

                if self.node_type == 'simple' or force_battle:
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
                    result = zip_longest([ship['hp'] for ship in battle_report["selfShipResults"]],
                                 [i['hp'] for i in battle_report['enemyShipResults']])
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

        if self.next_nodes:
            next_node_id = ze.go_next()
            next_node = self._node_name(next_node_id)
            for n_node in self.next_nodes:
                if n_node.name == next_node:
                    return n_node
            return 0
        else:
            return None


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
        # if len(self.ze.pveExplore) == 4:
        #     self.available = False
        #     return False
        fleet_avilable = next(filter(lambda x: x['status'] == 0 and x['ships'], self.ze.fleet), None)
        # [int(i) for i in range(1, 5) if str(
        #     i) not in [e['fleetId'] for e in self.ze.pveExplore]][0]
        if fleet_avilable:
            self.ze.working_fleet = fleet_avilable['id']
            return True

    def _prepare(self):
        if not (self.get_working_fleet() and self.enable):
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
        self.explore_table = (([0, 0, 0, 0, 0, 0], '10003'),
                              ([0, 0, 0, 0, 0, 0], '50003'),
                              ([0, 0, 0, 0, 0, 0], '40001'),
                              ([0, 0, 0, 0, 0, 0], '20001'))
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
        self.ninghai = None

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
                enemy_ships = [zemulator.ZjsnShip(s) for s in i["shipInfos"]]
                self.challenge_list.update({i['uid']: enemy_ships})

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
        # todo define more simple antisubmarine ships
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
        if self.ninghai:
            ninghai_fleet = [self.ninghai]
            self.ze.instant_fleet(ninghai_fleet)
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
        _logger.debug("result level:{}".format(self.ze.result_list[int(r3["warResult"]["resultLevel"])]))
        _logger.debug("challenge fleet:{}".format(
            [(si.name, si.level) for si in self.ze.working_ships]))


class Dock(State):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__(name='init', on_enter=self.go_home)
        self.ze = ze

    def go_home(self):
        self.ze.go_home()
        self.ze.auto_explore()
        self.ze.repair_all()
        self.ze.supply()


class Mission_1_1(Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_1_1, self).__init__('1-1A', 101, ze)

    def set_first_nodes(self):
        self.node_a = Node('A')
        return self.node_a

    def prepare(self):
        # 所有高级改造DD
        dd_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [100 > ship["level"] > 20,
                          ship.type in ['驱逐'],
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


class Mission_1_5(Mission_1_1):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_1_5, self).__init__(ze)
        self.mission_name = '1-5'
        self.mission_code = 105


class DailyTask(Mission):
    """日常任务"""

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('Task', 0, ze)
        self.task_solution = {2200132: Mission_1_1,
                              2200232: Mission_1_5,
                              2200332: Mission_1_1, }
        for key in self.task_solution:
            self.task_solution[key] = self.task_solution[key](self.ze)
        self.task_mission = None

    def _prepare(self):
        task_id = next(filter(lambda x: x in self.ze.task, self.task_solution), None)
        if task_id:
            self.task_mission = self.task_solution[task_id]
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
    def __init__(self):
        super(Robot, self).__init__()
        self.ze = zemulator.ZjsnEmulator()
        self.thread = None

        self.dock = Dock(self.ze)
        self.explore = Explore(self.ze)
        self.campaign = Campaign(self.ze, 402)
        states = [self.dock] + [m.state for m in [self.explore, self.campaign]]
        self.missions = {}

        self.machine = Machine(model=self, states=states, initial='init', auto_transitions=False)
        self.command = 'run'

        self.add_mission(DailyTask(self.ze))
        self.set_missions()
        self.machine.add_transition(trigger='go_out', prepare=[self.explore._prepare], source='init',
                                    dest=self.explore.mission_name)
        self.machine.add_transition(trigger='go_out', source=self.explore.mission_name, dest=self.explore.mission_name,
                                    conditions=[self.campaign.prepare], after=[self.campaign.start])
        self.machine.add_transition(trigger='go_out', source=self.explore.mission_name, dest='init',
                                    conditions=[self.explore.get_explore])
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
        # self.machine.add_transition(**self.m2_5_mid.trigger)
        # self.machine.add_transition(**self.m5_5_c.trigger)
        # self.machine.add_transition(**self.m2_5_down.trigger)
        # self.machine.add_transition(**self.pants.trigger)
        # self.machine.add_transition(**self.m4_3.trigger)
        # self.machine.add_transition(**self.m2_2.trigger)
        # self.machine.add_transition(**self.m5_5_b.trigger)
        # self.machine.add_transition(**self.m6_4.trigger)
        # self.machine.add_transition(**self.m6_3.trigger)

        # self.machine.add_transition(**self.m1_1a.trigger)
        # self.machine.add_transition(**self.m6_1.trigger)

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
                    self.state = 'init'
                elif zerror.eid in [-9997, -9995]:
                    _logger.info("login on another device, input anything to continue")
                    input()
                    self.ze.login()
                    self.state = 'init'
                else:
                    raise zerror

    def start(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.start()
        return self.thread
