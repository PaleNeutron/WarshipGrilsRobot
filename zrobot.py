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

_logger = logging.getLogger(__name__)


class Node(object):
    """docstring for Node"""

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
        self.name = name
        self.node_id = 0

        self.big_broken_protect = big_broken_protect
        self.next_nodes = []
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

    def add_next(self, next_nodes):
        if isinstance(next_nodes, collections.Iterable):
            self.next_nodes.extend(next_nodes)
        else:
            self.next_nodes.append(next_nodes)
        return

    def _node_name(self, node_id):
        return string.ascii_uppercase[int(str(node_id)[-2:]) - 2]

    def spy_filter(self, spy_result):
        target_flag = True
        if self.enemy_target:
            if not self.enemy_target in str(spy_result):
                target_flag = False

        avoid_flag = True
        if self.enemy_avoid:
            if self.enemy_avoid in str(spy_result):
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
        _logger.debug('进入 {} 点'.format(self.name))
        if self.node_type == 'simple':
            spy_result = ze.spy()
            if self.spy_filter(spy_result):
                try:
                    result_before_night = ze.deal(self.formation, big_broken_protect=self.big_broken_protect)
                except zemulator.ZjsnError:
                    return 0
                if self.night_flag:
                    self.night_flag = 1
                    report = result_before_night["warReport"]
                    if not any(report["hpBeforeNightWarEnemy"]):
                        self.night_flag = 0
                else:
                    self.night_flag = 0
                time.sleep(self.battle_length)
                self.battle_result = ze.getWarResult(self.night_flag)
                battle_report = self.battle_result["warResult"]
                result = zip([ship['hp'] for ship in battle_report["selfShipResults"]],
                             [i['hp'] for i in battle_report['enemyShipResults']])
                # todo 增加战斗评价
                _logger.debug('\n' + "\n".join(["{}     {}".format(a, b) for a, b in result]))

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
            ze.deal(1, big_broken_protect=False)

        elif self.node_type == 'skip':
            if not ze.skip():
                return 0

        if self.next_nodes:
            next_node_id = ze.go_next()
            next_node = self._node_name(next_node_id)
            for n_node in self.next_nodes:
                if n_node.name == next_node:
                    return n_node


class Mission(object):
    """docstring for Mission"""

    def __init__(self, mission_name, mission_code, ze: zemulator.ZjsnEmulator):
        super().__init__()
        self.mission_code = mission_code
        self.mission_name = mission_name
        self.state = State(name=self.mission_name, on_enter=self.start)
        self.ze = ze
        self.first_nodes = []
        self.first_nodes.append(self.set_first_nodes())

        self.available = False
        self.count = 0

    def __repr__(self):
        return self.mission_name

    @property
    def trigger(self):
        return {'prepare': self._prepare,
                'dest': self.state.name}

    def condition(self):
        return self.available

    def get_working_fleet(self):
        if len(self.ze.pveExplore) == 4:
            self.available = False
            return False
        fleet_avilable = [int(i) for i in range(1, 5) if str(i) not in [e['fleetId'] for e in self.ze.pveExplore]][0]
        self.ze.working_fleet = fleet_avilable
        return True

    def _prepare(self):
        if not self.get_working_fleet():
            return
        self.available = self.prepare()
        self.ze.go_home()
        if self.available:
            self.ze.auto_explore()
            self.ze.repair_all()
            self.ze.supply()
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
        first_node_name = Node('0')._node_name(self.ze.go_next())
        node = None
        for n in self.first_nodes:
            if n.name == first_node_name:
                node = n

        while node:
            new_node = node.deal(self.ze)
            node = new_node

        self.count += 1

        self.summery()
        self.postprocessing()

    def postprocessing(self):
        self.ze.auto_strengthen()
        self.ze.dismantle()
        self.ze.cleanup_equipment()

    def summery(self):
        pass


class Mission_6_1_A(Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_6_1_A, self).__init__('kill_fish', 601, ze)

    def set_first_nodes(self):
        node_a = Node('A', formation=5, additional_spy_filter=lambda x: x["enemyVO"]["enemyFleet"]["id"] == 60102003)
        return node_a

    def prepare(self):
        # 所有装了声呐的反潜船
        dd_ships = []
        slow_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=False):
            conditions = [100 > ship["level"] > 1,
                          ship.type in ['驱逐', '轻母', '轻巡'],
                          "10008321" in ship["equipment"] or "10008421" in ship[
                              "equipment"] or ship.type == '轻母',  # 带着声呐
                          ]
            if all(conditions):
                if float(ship["battleProps"]["speed"]) > 27:  # 航速高于27
                    dd_ships.append(ship.id)
                else:
                    slow_ships.append(ship.id)
        _logger.debug("dd_ships:{}".format([self.ze.userShip[ship_id].name for ship_id in dd_ships]))
        _logger.debug("slow_ships:{}".format([self.ze.userShip[ship_id].name for ship_id in slow_ships]))

        self.ze.ship_groups[0] = (dd_ships, 1, False)
        for i in range(1, 5):
            self.ze.ship_groups[i] = (dd_ships, 1, False)
        self.ze.ship_groups[5] = (slow_ships, 1, False)

        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

    def summery(self):
        self.ze.strengthen(13664)
        _logger.debug("炸鱼 {} 次, 共有{}船, result:{}".format(self.count, len(self.ze.userShip),
                                                         [(i.name, i.level) for i in self.ze.working_ships]))


class Explore(Mission):
    """docstring for Explore"""

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Explore, self).__init__('explore', 0, ze)
        self.ze = ze
        self.avilable = True
        # 第一项是远征需要用到的船 第二项是远征目标
        self.explore_table = (([35442, 35500, 3846, 7376, 183, 103], '10003'),
                              ([14174, 7367, 10706, 13972, 11497, 8452], '50003'),
                              ([128, 14094, 113, 101, 577, 7373], '40001'),
                              ([123, 13973, 27865, 14138, 498, 104], '20001'))

    def prepare(self):
        pass

    def set_first_nodes(self):
        pass

    def _prepare(self):
        exploring_fleet = [e['fleetId'] for e in self.ze.pveExplore]
        for i, table in enumerate(self.explore_table):
            if str(i + 1) not in exploring_fleet:
                self.ze.working_fleet = str(i + 1)
                self.ze.instant_fleet(table[0])
                self.ze.supply()
                self.ze.explore(self.ze.working_fleet, table[1])

    def start(self):
        explore_over_fleet = None
        while not explore_over_fleet:
            explore_over_fleet = self.ze.get_explore()
            self.ze.relogin()
            self.ze.repair_all(0)
            self.ze.get_award()
            time.sleep(10)
        self.ze.working_fleet = explore_over_fleet


class Challenge(Mission):
    """docstring for Explore"""

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Challenge, self).__init__('challenge', 0, ze)
        self.ze = ze
        self.avilable = True
        self.battle_fleet = [36207, 35373, 35365, 7859, 8579, 7865]
        self.friends = [2593850, 74851, 2827412]
        self.old_fleet = []
        self.challenge_list = {}
        self.friend_available = False
        self.last_challenge_time = datetime.fromtimestamp(0)
        self.last_friend_time = datetime.fromtimestamp(0)

    def prepare(self):
        pass

    def set_first_nodes(self):
        pass

    def _prepare(self):
        if not self.get_working_fleet():
            return

        self.challenge_list = {}
        self.friend_available = False

        now = datetime.today()
        check_points = [now.replace(hour=0, minute=0), now.replace(hour=12, minute=0), now.replace(hour=18, minute=0)]
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

        if not self.challenge_list:
            self.available = False
        else:
            self.ze.instant_fleet(self.battle_fleet)

        self.last_challenge_time = datetime.today()

        r_f = self.ze.get(self.ze.url_server + '/friend/visitorFriend/' + str(self.friends[0]))
        if r_f['challengeNum'] == 0:
            self.friend_available = True

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

    def start(self):
        _logger.debug("challenge fleet:{}".format([(si.name, si.level) for si in self.ze.working_ships]))
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
        n = 0
        _logger.debug(enemy_uid)
        battle_fleet = self.ze.working_ships_id
        ninghai_fleet = [1215]
        self.ze.instant_fleet(ninghai_fleet)
        r1 = self.ze.get(self.ze.url_server + "/{}/spy/{}/{}".format(api, enemy_uid, self.ze.working_fleet))
        r2 = self.ze.get(self.ze.url_server + "/{}/challenge/{}/{}/1/".format(api, enemy_uid, self.ze.working_fleet))

        self.ze.go_home()
        if friend:
            fish_num = 0
        else:
            fish_num = self.challenge_list[enemy_uid]
        if fish_num == 0:
            self.ze.instant_fleet(battle_fleet)
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
            r1 = self.ze.get(self.ze.url_server + "/{}/spy/{}/{}".format(api, enemy_uid, self.ze.working_fleet))
            r2 = self.ze.get(
                self.ze.url_server + "/{}/challenge/{}/{}/{}/".format(api, enemy_uid, self.ze.working_fleet,
                                                                      battle_formation))
            report = r2["warReport"]
            result = zip(report["hpBeforeNightWarSelf"], report["hpBeforeNightWarEnemy"])
            if any(report["hpBeforeNightWarEnemy"]):
                night_flag = 1
            else:
                night_flag = 0
                over = True
            n += 1

            if n > 100:
                if all([report["hpBeforeNightWarEnemy"].count(0) > 3,
                        report["hpBeforeNightWarSelf"].count(0) < 3,
                        report["hpBeforeNightWarEnemy"][0] == 0,
                        ]):
                    over = True
            elif n > 150:
                if report["hpBeforeNightWarEnemy"][0] == 0:
                    over = True
            time.sleep(2)

        time.sleep(30)
        #     for a,b in result:
        #         mlogger.debug(a+" "+b)
        # r3 = e.get(e.url_server + "/pvp/getWarResult/0/")
        r3 = self.ze.get(self.ze.url_server + "/{}/getWarResult/{}/".format(api, night_flag))
        _logger.debug("result level:{}".format(r3["warResult"]["resultLevel"]))


class Mission_5_2_C(Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_5_2_C, self).__init__('5-2C', 502, ze)
        self.count = 0

    def set_first_nodes(self):
        self.node_c = Node('C', enemy_target='轻母')
        self.node_f = Node('F')
        self.node_h = Node('H')
        self.node_i = Node('I')
        self.node_j = Node('J', formation=4, night_flag=1, big_broken_protect=False)
        self.node_c.add_next(self.node_f)
        self.node_f.add_next([self.node_i, self.node_h])
        self.node_i.add_next(self.node_j)
        self.node_h.add_next(self.node_j)
        return self.node_c

    def prepare(self):
        # 所有水下船只
        ss_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [100 > ship["level"] > 1,
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
        except zemulator.ZjsnError:
            return False
        return True

    def summery(self):
        _logger.debug("5-2 {} 次, 共有{}船, result:{}".format(self.count, len(self.ze.userShip),
                                                          [(self.ze.userShip[i].name, self.ze.userShip[i].level) for i
                                                           in self.ze.working_ships_id]))


class Mission_2_5_mid(Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_2_5_mid, self).__init__('2-5mid', 205, ze)
        self.count = 0

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
                          ]
            if all(conditions):
                cv_ships.append(ship.id)
        _logger.debug("ss_ships:{}".format(
            [(self.ze.userShip[ship_id].name, self.ze.userShip[ship_id].level) for ship_id in cv_ships]))

        self.ze.ship_groups[0] = ([16523], 1, False)
        self.ze.ship_groups[1] = self.ze.ship_groups[2] = (ss_ships, 1, False)
        self.ze.ship_groups[3] = self.ze.ship_groups[5] = (cv_ships, 1, False)
        self.ze.ship_groups[4] = (taitai, 1, False)

        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

    def summery(self):
        _logger.debug("2-5 中路 {} 次, 共有{}船, result:{}".format(self.count, len(self.ze.userShip),
                                                             [(i.name, i.level) for i in self.ze.working_ships]))


class Robot(threading.Thread):
    """docstring for Robot"""

    def __init__(self):
        super(Robot, self).__init__()
        self.ze = zemulator.ZjsnEmulator()
        self.m6_1 = Mission_6_1_A(self.ze)
        self.explore = Explore(self.ze)
        self.m5_2 = Mission_5_2_C(self.ze)
        self.m2_5_mid = Mission_2_5_mid(self.ze)
        self.challenge = Challenge(self.ze)
        self.missions = [self.m5_2, self.m6_1, self.explore, self.m2_5_mid, self.challenge]

        self.machine = Machine(model=self, states=self.states, initial='init')
        self.command = 'run'
        self.add_transitions()

    def add_transitions(self):
        self.machine.add_transition(trigger='go_out', source='init', conditions=[self.challenge.condition],
                                    after='go_back', **self.challenge.trigger)
        # self.machine.add_transition(trigger='go_out', source='init', conditions=[self.m5_2.condition], after='go_back', **self.m5_2.trigger)
        self.machine.add_transition(trigger='go_out', source='init', conditions=[self.m6_1.condition], after='go_back',
                                    **self.m6_1.trigger)
        self.machine.add_transition(trigger='go_out', source='init', after='go_back', **self.explore.trigger)
        self.machine.add_transition(trigger='go_back', source='*', dest='init')

    @property
    def states(self):
        return ['init'] + [m.state for m in self.missions]

    def run(self):
        self.ze.login()
        self.ze.repair_all()
        while self.command != 'stop':
            self.go_out()
            time.sleep(2)


if __name__ == '__main__':
    from transitions import logger as transitions_logger

    transitions_logger.setLevel(logging.DEBUG)
    log_formatter = logging.Formatter('%(asctime)s: %(levelname)s: %(message)s', datefmt='%H:%M:%S')
    root = logging.getLogger()
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    root.addHandler(stream_handler)

    _logger.setLevel(logging.DEBUG)
    zemulator.zlogger.setLevel(logging.DEBUG)
    r = Robot()
    r.run()
