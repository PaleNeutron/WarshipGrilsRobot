import china_server
import zemulator
import zrobot


class JapanPants(china_server.MissionPants):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__(ze)
        self.pants_yesterday = -50

        # def prepare(self):
        #     if not self.pants_available:
        #         self.available = False
        #         return
        #
        #     if self.count > 100:
        #         zrobot._logger.warning('pants {}, SL {}'.format(self.ze.spoils - self.pants_yesterday, self.count))
        #     # 所有DD
        #     dd_ships = []
        #     for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=False):
        #         conditions = [ship.type in ['驱逐'],
        #                       ship.level > 1,
        #                       ship.evolved == 1 or ship.can_evo,
        #                       ]
        #         if all(conditions):
        #             dd_ships.append(ship.id)
        #     ships = [self.ze.userShip[ship_id] for ship_id in dd_ships]
        #     zrobot._logger.debug("dd_ships:{}".format([(s.name, s.level) for s in ships]))
        #
        #     for i in range(0, 2):
        #         self.ze.ship_groups[i] = (dd_ships, 1, False)
        #     self.ze.ship_groups[2] = ([422], 1, False)
        #     self.ze.ship_groups[3] = ([118], 1, False)
        #     self.ze.ship_groups[4] = self.ze.ship_groups[5] = (None, 1, False)
        #
        #     try:
        #         self.ze.change_ships()
        #     except zemulator.ZjsnError:
        #         return False
        #     return True


class Mission1_4(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('1-4A', 104, ze)

    def set_first_nodes(self):
        self.node_a = zrobot.Node('A')
        return self.node_a

    def prepare(self):
        # 所有高级改造DD
        dd_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [ship.locked,
                          ship.type in ['驱逐'],
                          ]
            if all(conditions):
                dd_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in dd_ships]
        zrobot._logger.debug("dd_ships:{}".format([(s.name, s.level) for s in ships]))

        self.ze.ship_groups[0] = ([111], 1, False)
        self.ze.ship_groups[3] = ([118], 1, False)
        for i in range(1, 3):
            self.ze.ship_groups[i] = (dd_ships, 1, False)
        self.ze.ship_groups[4] = self.ze.ship_groups[5] = (None, 1, False)

        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

    def postprocessing(self):
        self.ze.auto_strengthen()


class Mission2_4(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('2-4A', 204, ze)
        self.battle_fleet = [111, 147, 174, 172, 1, 118]

    def set_first_nodes(self):
        self.node_a = zrobot.Node('A', enemy_avoid=zemulator.ZjsnShip.type_id('战巡'))
        self.node_b = zrobot.Node('B', enemy_avoid=zemulator.ZjsnShip.type_id('战巡'))
        return [self.node_a, self.node_b]

    def prepare(self):
        fleet = self.battle_fleet
        fleet_group = [([i], 1, False) for i in fleet]
        self.ze.ship_groups = fleet_group
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

    def postprocessing(self):
        for i in self.battle_fleet:
            self.ze.strengthen(i)


class Mission3_2(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('3-2boss', 302, ze)
        self.battle_fleet = [111, 147, 174, 1, 422, 118]

    def set_first_nodes(self):
        self.node_c = zrobot.Node('C')
        self.node_e = zrobot.Node('E')
        self.node_g = zrobot.Node('G', night_flag=True)

        self.node_c.add_next(self.node_e)
        self.node_e.add_next(self.node_g)
        return self.node_c

    def prepare(self):
        fleet = self.battle_fleet
        fleet_group = [([i], 1, False) for i in fleet]
        self.ze.ship_groups = fleet_group
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

    def postprocessing(self):
        for i in self.battle_fleet:
            self.ze.strengthen(i)


class Mission3_4_A(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('3-4A', 304, ze)
        self.battle_fleet = [1612, 103, 174, 172, 118, 798]

    def set_first_nodes(self):
        self.node_a = zrobot.Node('A', enemy_avoid=zemulator.ZjsnShip.type_id('战巡'))
        return self.node_a

    def prepare(self):
        fleet = self.battle_fleet
        fleet_group = [([i], 1, False) for i in fleet]
        self.ze.ship_groups = fleet_group
        dd_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=False):
            conditions = [ship["level"] > 1,
                          ship.type in ['驱逐'],
                          ship.can_evo or ship.evolved,
                          ship.locked,
                          ship.name not in ['雪风', '沃克兰'],
                          ]
            if all(conditions):
                dd_ships.append(ship.id)
        self.ze.ship_groups[0] = [[self.ze.userShip.name('安德烈').id], 1, False]
        for i in range(1, 5):
            self.ze.ship_groups[i] = [dd_ships, 1, False]
        zrobot._logger.debug(
            "dd_ships:{}".format([self.ze.userShip[ship_id].name for ship_id in dd_ships]))

        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

        # def postprocessing(self):
        #     self.ze.strengthen(self.ze.userShip.name('胡德'))
        #     for i in self.battle_fleet:
        #         self.ze.strengthen(i)


class Mission3_4(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('3-4 3点', 304, ze)
        self.battle_fleet = [111, 147, 174, 1, 422, 118]

    def set_first_nodes(self):
        self.node_a = zrobot.Node('A', enemy_target=6)
        self.node_b = zrobot.Node('b')
        self.node_c = zrobot.Node('c')
        self.node_d = zrobot.Node('d')
        self.node_e = zrobot.Node('e', node_type='resource')
        self.node_f = zrobot.Node('f', node_type='resource')
        self.node_g = zrobot.Node('g')

        self.node_a.add_next([self.node_b, self.node_c])
        self.node_b.add_next(self.node_d)
        self.node_c.add_next([self.node_e, self.node_d])
        self.node_d.add_next(self.node_f)
        self.node_e.add_next(self.node_g)
        self.node_g.add_next(self.node_f)

        return self.node_a

    def prepare(self):
        fleet = self.battle_fleet
        fleet_group = [([i], 1, False) for i in fleet]
        self.ze.ship_groups = fleet_group
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

    def postprocessing(self):
        for i in self.battle_fleet:
            self.ze.strengthen(i)


class Mission_3_4_Boss(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('3-4 3点', 304, ze)
        self.battle_fleet = ['声望', '纳尔逊', '提尔比茨', '罗德尼', '萨拉托加', '列克星敦']

    def set_first_nodes(self):
        self.node_a = zrobot.Node('A', enemy_avoid=zemulator.ZjsnShip.type_id('战巡'))
        self.node_c = zrobot.Node('c')
        self.node_e = zrobot.Node('e', node_type='resource')
        self.node_i = zrobot.Node('i')
        self.node_j = zrobot.Node('j', formation=4, night_flag=1)

        self.node_a.add_next(self.node_c)
        self.node_c.add_next(self.node_e)
        self.node_e.add_next(self.node_i)
        self.node_i.add_next(self.node_j)

        return self.node_a

    def prepare(self):
        if self.boss_hp == 0:
            return False
        fleet = [self.ze.userShip.name(name).id for name in self.battle_fleet]
        fleet_group = [([i], 0.8, True) for i in fleet]
        self.ze.ship_groups = fleet_group
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

    def postprocessing(self):
        pass

    def summery(self):
        super().summery()
        zrobot._logger.debug("boss hp={}".format(self.boss_hp))


class Mission_4_4_Boss(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('4-4 boss', 404, ze)
        self.battle_fleet = ['提尔比茨', '威尔士亲王', '纳尔逊', '罗德尼', '萨拉托加', '列克星敦']

    def set_first_nodes(self):
        self.node_a = zrobot.Node('A', enemy_avoid=zemulator.ZjsnShip.type_id('战巡'))
        self.node_c = zrobot.Node('c')
        self.node_f = zrobot.Node('f', node_type='resource')
        self.node_i = zrobot.Node('i')
        self.node_l = zrobot.Node('l', formation=4, night_flag=1)

        self.node_a.add_next(self.node_c)
        self.node_c.add_next(self.node_f)
        self.node_f.add_next(self.node_i)
        self.node_i.add_next(self.node_l)

        return self.node_a

    def prepare(self):
        if self.boss_hp == 0:
            return False

        fleet = [self.ze.userShip.name(name).id for name in self.battle_fleet]
        fleet_group = [([i], 0.8, True) for i in fleet]
        self.ze.ship_groups = fleet_group
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

    def summery(self):
        super().summery()
        zrobot._logger.debug("boss hp={}".format(self.boss_hp))


class Mission_Event(china_server.MissionEvent):
    event_base = 9940
    event_num = 3
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__(ze)
        # self.battle_fleet_name = ['胡德', '俾斯麦', '威尔士亲王', '黎塞留', '罗德尼', '声望']
        self.battle_fleet_name = ['赤城', '海伦娜', '亚特兰大', '大凤', '追赶者', '普林斯顿']

    def set_first_nodes(self):
        # nm = zrobot.Node('m', formation=1, night_flag=1)
        # nk = zrobot.Node('k')
        # nf = zrobot.Node('f')
        # ng = zrobot.Node('g')
        # nc = zrobot.Node('c', node_type=zrobot.NODE_RESOURCE)
        # nb = zrobot.Node('b', node_type=zrobot.NODE_RESOURCE)
        # na = zrobot.Node('a', formation=5)

        # na.add_next(nb)
        # nb.add_next(nc)
        # nc.add_next(ng)
        # nc.add_next(nf)
        # ng.add_next(nk)
        # nf.add_next(nk)
        # nk.add_next(nm)
        self.node_a = self.node_chain([
            # zrobot.Node('a', formation=4, night_flag=1, additional_spy_filter=lambda x: int(x['enemyVO']['enemyFleet']['formation'])==3),
            zrobot.Node('a'),
            zrobot.Node('d'),
            zrobot.Node('f'),
            zrobot.Node('l', node_type=zrobot.NODE_RESOURCE),
            zrobot.Node('m', night_flag=1),
        ])

        return self.node_a


class MissionEventCollection(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('event_ex', 9936, ze)
        self.battle_fleet = []
        self.battle_fleet_name = []
        self.battle_fleet_name = ['胡德', '声望', '罗德尼', '前卫', '拉菲', '信赖']
        # self.enable = True
        self.target_ship = '约翰斯顿'

    def set_first_nodes(self):
        # zrobot.Node.DEFAULT_SLEEP_TIME = 15
        self.node_a = self.node_chain([
            zrobot.Node("b"),
            zrobot.Node("e", node_type=zrobot.NODE_RESOURCE),
            zrobot.Node("i", node_type=zrobot.NODE_RESOURCE),
            zrobot.Node("j", node_type=zrobot.NODE_RESOURCE),
            zrobot.Node("p"),
            zrobot.Node("q", formation=4, night_flag=1),
        ])

        # zrobot.Node.DEFAULT_SLEEP_TIME = 30

        return self.node_a

    def prepare(self):
        # if self.boss_hp == 0:
        #     zrobot._logger.debug("boss dead, over")
        #     return False
        target_ship = self.target_ship
        if self.ze.userShip.name(target_ship, 0):
            zrobot._logger.debug("got {}, over".format(target_ship))
            return False
        self.battle_fleet = [self.ze.userShip.name(name).id for name in self.battle_fleet_name]
        if not self.battle_fleet:
            self.battle_fleet = self.ze.working_ships_id
        fleet = self.battle_fleet
        fleet_group = [([i], 0.85, True) for i in fleet]
        self.ze.ship_groups = fleet_group
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True


class Mission_Event_2(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('mission event', 9919, ze)
        self.battle_fleet = []
        self.enable = True

    def set_first_nodes(self):
        self.node_a = self.node_chain([
            zrobot.Node('a', node_type='resource'),
            zrobot.Node('d', formation=3, sleep_time=15),
            zrobot.Node('g', formation=5, sleep_time=15),
            zrobot.Node('k', formation=5, sleep_time=15),
        ])

        return self.node_a

    def prepare(self):
        # 所有装了声呐的反潜船
        as_ships = []
        for ship in self.ze.userShip.unique:
            conditions = [
                          ship.type in ['驱逐', '轻巡'],
                          "10008321" in ship.equipment or "10008421" in ship.equipment,
                          ]
            if all(conditions):
                as_ships.append(ship.id)
        zrobot._logger.debug(
            "as_ships:{}".format([self.ze.userShip[ship_id].name for ship_id in as_ships]))

        for i in range(0, 4):
            self.ze.ship_groups[i] = (as_ships, 1, True)
        for i in range(4, 6):
            self.ze.ship_groups[i] = (None, 1, False)

        return self.ze.change_ships()

    def summery(self):
        super().summery()
        zrobot._logger.debug("boss hp={}".format(self.boss_hp))

class JapanChallenge(zrobot.Challenge):
    """docstring for JapanChallenge"""

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__(ze)
        self.friends = [22876, 21892, 18869]
        # self.ship_list = [17263, 17546, 7203, 775, 1213, 10380, 173, 1258, 9131, 8830]
        self.start_point = 80

    def formation_for_fish(self, fish_num):
        fish_fleet = self.battle_fleet[:]
        if fish_num > 0:
            fish_fleet[-1] = self.ze.userShip.name('宁海').id
        self.ze.instant_workingfleet(fish_fleet)


class Japan_Mission_1_5(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Japan_Mission_1_5, self).__init__('1-5', 105, ze)

    def set_first_nodes(self):
        self.node_a = zrobot.Node('A', formation=1)
        return self.node_a

    def prepare(self):
        # 所有高级改造DD
        if self.success_count > 11:
            return False
        dd_ships = [self.ze.userShip.name('萤火虫').id]

        for i in range(1, 6):
            self.ze.ship_groups[i] = (None, 1, False)
        self.ze.ship_groups[0] = (dd_ships, 1, False)

        try:
            self.ze.change_ships()
        except zemulator.ZjsnError as zerror:
            return False
        return True

    def postprocessing(self):
        pass


# class JapanTask(zrobot.Mission):
#     """日常任务"""
#     def __init__(self, ze: zemulator.ZjsnEmulator):
#         super().__init__('Task', 0, ze)
#         self.task_solution = {2200132: Japan_Mission_1_1,
#                                2200232: Japan_Mission_1_5,
#                                2200332: Japan_Mission_1_1,}
#         for key in self.task_solution:
#             self.task_solution[key] = self.task_solution[key](self.ze)
#         self.task_mission = None
#     def _prepare(self):
#         task_id = next(filter(lambda x: x in self.ze.task, self.task_solution), None)
#         if task_id:
#             self.task_mission = self.task_solution[task_id]
#             self.task_mission._prepare()
#             self.available = self.task_mission.available
#         else:
#             self.available = False
#         return
#     def prepare(self):
#         passs
#
#     def set_first_nodes(self):
#         pass
#
#     def start(self):
#         self.task_mission.start()


class Japan_Mission_5_2_C(zrobot.Mission):
    """5-2 C 炸鱼"""

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Japan_Mission_5_2_C, self).__init__('5-2C', 502, ze)
        self.battle_fleet = [782, 932, 293, 572, 302, 172]
        fleet_group = [([i], 1, False) for i in self.battle_fleet]
        self.ze.ship_groups = fleet_group

    def set_first_nodes(self):
        self.node_c = zrobot.Node('C', enemy_avoid=2, formation=5)
        return self.node_c

    def prepare(self):
        # 所有高级改造DD
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError as zerror:
            return False
        return True

    def postprocessing(self):
        pass


class Japan_Mission_6_1_A(zrobot.Mission_6_1_A):
    """鱼塘 炸鱼"""

    def __init__(self, ze: zemulator):
        super().__init__(ze)
        self.boss_ships = 'U96'


class JapanRobot(zrobot.Robot):
    """docstring for Robot"""

    def __init__(self):
        super().__init__('junhongbill', 'ouzhoutiduzjsn', japan_server=True)
        self.ze.common_lag = 50
        self.ze.equipment_formula = [20, 50, 10, 130]
        self.ze.boat_formula = [50, 200, 100, 30]
        self.explore.explore_table = (
            ([110, 183, 710, 391, 386, 449], '20002'),
            ([121, 102, 109, 108, 107, 219], '20001'),
            ([105, 143, 2891, 9005, 3002, 120], '40001'),
            ([1475, 550, 211, 187, 185, 258], '50003'),
        )
        # self.campaign.target_mission = 202
        # self.campaign.formation_code = 5

    def set_missions(self):
        # self.m1_4a = Mission1_4(self.ze)
        # self.machine.add_states(self.m1_4a.state)
        # self.machine.add_transition(**self.m1_4a.trigger)

        self.add_mission(JapanChallenge(self.ze))

        # self.add_mission(MissionEventCollection(self.ze))
        # self.add_mission(Mission_Event_2(self.ze))
        self.add_mission(Mission_Event(self.ze))
        self.add_mission(zrobot.Mission_1_1(self.ze))
        self.add_mission(china_server.Mission_5_3(self.ze))
        # self.challenge = JapanChallenge(self.ze)
        # self.machine.add_states(self.challenge.state)
        # self.machine.add_transition(**self.challenge.trigger)

        # self.m3_4 = Mission3_4(self.ze)
        # self.machine.add_states(self.m3_4.state)
        # self.machine.add_transition(**self.m3_4.trigger)

        self.add_mission(Mission3_4_A(self.ze))
        self.pants = JapanPants(self.ze)
        self.add_mission(self.pants)

        # self.m3_2 = Mission3_2(self.ze)
        # self.machine.add_states(self.m3_2.state)
        # self.machine.add_transition(**self.m3_2.trigger)


        # self.m4_4_boss = Mission_4_4_Boss(self.ze)
        # self.machine.add_states(self.m4_4_boss.state)
        # self.machine.add_transition(**self.m4_4_boss.trigger)

        # self.m3_4_boss = Mission_3_4_Boss(self.ze)
        # self.machine.add_states(self.m3_4_boss.state)
        # self.machine.add_transition(**self.m3_4_boss.trigger)

        # self.m1_1_a = Japan_Mission_1_1(self.ze)
        # self.machine.add_states(self.m1_1_a.state)
        # self.machine.add_transition(**self.m1_1_a.trigger)

        # self.m5_2_c = Japan_Mission_5_2_C(self.ze)
        # self.machine.add_states(self.m5_2_c.state)
        # self.machine.add_transition(**self.m5_2_c.trigger)

        # self.m_event = Mission_Event(self.ze)
        # self.machine.add_states(self.m_event.state)
        # self.machine.add_transition(**self.m_event.trigger)


if __name__ == '__main__':
    r = JapanRobot()
    # r.ze.boat_formula = [200, 30, 200, 30]
    # r.ze.build_boat_remain = 10
    # r.missions['pants'].switch()
    # r.missions['kill_fish'].switch()
    # r.missions['偷钢'].switch()
    # r.missions['1-1A'].switch()
    # r.missions['event'].switch()
    # r.kill_fish.switch()
    # r.kill_fish.boss_ships = '射水鱼'
    r.start()
    # r.ze.login()
    # print(r.ze.fleet)
