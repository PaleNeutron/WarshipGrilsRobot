import time
import string
import random
import logging
import threading

from transitions import Machine, State


import zemulator
_logger = logging.getLogger(__name__)


class Node(object):
    """docstring for Node"""

    def __init__(self, name, node_type='simple', formation=2, enemy_target=None, enemy_avoid=None):
        """we have 3 node_types: simple, resource, skip"""
        super(Node, self).__init__()
        self.name = name
        self.node_id = 0

        self.next_nodes = []
        self.node_type = node_type
        self.night_flag = 0
        self.battle_result = {}
        self.formation = formation
        self.enemy_target = enemy_target
        self.enemy_avoid = enemy_avoid

        self.sleep_mu = 30
        self.sleep_sigma = 2
        rd = random.normalvariate(self.sleep_mu, self.sleep_sigma)
        if rd < self.sleep_mu - 3*self.sleep_sigma or rd > self.sleep_mu + 3*self.sleep_sigma:
            self.battle_length = self.sleep_mu
        else:
            self.battle_length = rd


    def add_next(self, next_nodes):
        self.next_nodes.append(next_nodes)
        return

    def _node_name(self, node_id):
        return string.ascii_uppercase[int(str(node_id)[-2:]) - 2]

    def spy_filter(self, spy_result, additional_func=None):
        target_flag = False
        if self.enemy_target:
            if self.enemy_target in str(spy_result):
                target_flag = True

        avoid_flag = False
        if self.enemy_avoid:
            if self.enemy_avoid not in str(spy_result):
                avoid_flag = True

        additional_flag = True
        if callable(additional_func):
            if not additional_func(spy_result):
                additional_flag = False

        if all((target_flag, avoid_flag, additional_flag)):
            return True
        else:
            return False

    def deal(self, ze:zemulator.ZjsnEmulator):
        if self.node_type == 'simple':
            spy_result = ze.spy()
            if self.spy_filter(spy_result):
                result_before_night = ze.deal(self.formation)
                if self.night_flag:
                    report = result_before_night["warReport"]
                    if not any(report["hpBeforeNightWarEnemy"]):
                        self.night_flag = 0
                time.sleep(self.battle_length)
                self.battle_result = ze.getWarResult(self.night_flag)
                if 'newShipVO' in self.battle_result:
                    new_ship = zemulator.ZjsnShip(self.battle_result['newShipVO'][0])
                    if new_ship.cid not in ze.unlockShip:
                        _logger.info('get new ship: {}'.format(new_ship.name))
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


class Mission(State):
    """docstring for Mission"""

    def __init__(self, mission_code, ze:zemulator.ZjsnEmulator):
        super(Mission, self).__init__(mission_code)
        # self.mission_code = mission_code
        self.ze = ze
        self.first_nodes = []
        self.first_nodes.append(self.set_first_nodes())

    def prepare(self):
        raise NotImplementedError()

    def set_first_nodes(self):
        raise NotImplementedError()

    def start(self):
        self.ze.go_home()
        if not self.prepare():
            return 0
        self.ze.go_out(self.name)
        first_node_name = Node('0')._node_name(self.ze.go_next())
        node = None
        for n in self.first_nodes:
            if n.name == first_node_name:
                node = n

        while node:
            new_node = node.deal()
            node = new_node


class Mission_6_1_A(Mission):
    def __init__(self, ze:zemulator.ZjsnEmulator):
        super(Mission_6_1_A, self).__init__(601, ze)

    def set_first_nodes(self):
        node_a = Node('A', formation=5)
        return node_a

    def prepare(self):
        # 所有装了声呐的驱逐舰
        dd_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [100 > ship["level"] > 1,
                          ship.type in ['驱逐', '轻母', '轻巡'],  # 必须是DD
                          ship.fleet_id == 0, # 没在队伍里
                          ship.status != 2, # 没在修理
                          not ship.should_be_repair(1), # 没有中破
                          float(ship["battleProps"]["speed"]) > 27,  # 航速高于27
                          "10008321" in ship["equipment"] or "10008421" in ship["equipment"],  # 带着声呐
                          ]
            if all(conditions):
                dd_ships.append(ship.id)
        # print("dd_ships:{}".format([ship.name for ship in dd_ships]))

        self.ze.ship_groups[0] = ([], 1, False)
        for i in range(1,6):
            self.ze.ship_groups[i] = (dd_ships, 1, False)

        self.ze.go_home()
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return 0
        self.ze.auto_explore()
        self.ze.supply()




class Robot(threading.Thread):
    """docstring for Robot"""

    def __init__(self):
        super(Robot, self).__init__()
        self.ze = zemulator.ZjsnEmulator()
        self.missions = self.set_missions()
        self.stat = 'ready'

    def set_missions(self):
        missions = [Mission_6_1_A(self.ze)]
        return missions

    def run(self):
        self.ze.login()
        while self.stat != 'stop':
            try:
                self.ze.go_home()
                for m in self.missions:
                    m.start()
            except zemulator.ZjsnError as zerror:
                if zerror.eid == 0:
                    pass