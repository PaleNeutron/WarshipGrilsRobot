#!/usr/bin/env python3
import zemulator
import zrobot


# class Mission_6_1_A_China(zrobot.Mission_6_1_A):
#     def __init__():
#     self.boss_ships = '射水鱼'

class Mission_5_2_C(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_5_2_C, self).__init__('5-2C', 502, ze)

    def set_first_nodes(self):
        self.node_c = zrobot.Node('C', enemy_target='轻母')
        self.node_f = zrobot.Node('F')
        self.node_h = zrobot.Node('H')
        self.node_i = zrobot.Node('I')
        self.node_j = zrobot.Node(
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
            zrobot._logger.info('有北京风了，2-5已经毕业')
            return
        ss_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [ship["level"] > 1,
                          ship.type in ['潜艇', '炮潜'],
                          ]
            if all(conditions):
                ss_ships.append(ship.id)
        zrobot._logger.debug("ss_ships:{}".format(
            [(self.ze.userShip[ship_id].name, self.ze.userShip[ship_id].level) for ship_id in ss_ships]))

        for i in range(0, 6):
            self.ze.ship_groups[i] = (ss_ships, 1, False)
        self.ze.ship_groups[0][0].insert(
            0, self.ze.userShip.name("U47").id)  # 尽可能狼群U47旗舰

        return self.ze.change_ships()


class Mission_2_5_mid(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_2_5_mid, self).__init__('2-5mid', 205, ze)

    def set_first_nodes(self):
        self.node_a = zrobot.Node('A')
        self.node_b = zrobot.Node('B')
        self.node_d = zrobot.Node('D', node_type='skip')
        self.node_h = zrobot.Node('H', node_type='skip')
        self.node_k = zrobot.Node('K', node_type='skip')
        self.node_o = zrobot.Node('O', night_flag=1)

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
            zrobot._logger.info('有岛风了，2-5中路已经毕业')
            return
        ss_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [ship["level"] > 60,
                          ship.type in ['潜艇'],
                          ]
            if all(conditions):
                ss_ships.append(ship.id)
        zrobot._logger.debug("ss_ships:{}".format(
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
        zrobot._logger.debug("cv_ships:{}".format(
            [(self.ze.userShip[ship_id].name, self.ze.userShip[ship_id].level) for ship_id in cv_ships]))

        self.ze.ship_groups[0] = ([16523], 0.7, True)  # 飙车胡德
        self.ze.ship_groups[1] = self.ze.ship_groups[2] = (ss_ships, 0, False)
        self.ze.ship_groups[3] = self.ze.ship_groups[5] = (
            cv_ships, 0.7, False)
        self.ze.ship_groups[4] = (taitai, 0.7, True)
        # self.ze.ship_groups[3][0].insert(0,13664)  # 大凤优先4号位置
        self.ze.ship_groups[3] = ([13664], 0.7, True)  # 大凤
        self.ze.ship_groups[4] = ([115], 0.7, True)  # 太太
        self.ze.ship_groups[5] = ([43707], 0.7, True)  # 加加

        return self.ze.change_ships()


class Mission_5_5_C(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_5_5_C, self).__init__('5-5C', 505, ze)

    def set_first_nodes(self):
        self.node_c = zrobot.Node('C', formation=4, enemy_avoid=zemulator.ZjsnShip.type_id("轻巡"))
        self.node_f = zrobot.Node('F')
        self.node_i = zrobot.Node('I', formation=4, night_flag=1)
        self.node_c.add_next(self.node_f)
        self.node_f.add_next(self.node_i)
        return self.node_c

    def prepare(self):
        # 所有90级以上水下船只
        ss_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [ship["level"] >= 70,
                          ship.type in ['潜艇', '炮潜'],
                          ]
            if all(conditions):
                ss_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in ss_ships]
        zrobot._logger.debug("ss_ships:{}".format(
            [(s.name, s.level) for s in ships]))

        for i in range(0, 6):
            self.ze.ship_groups[i] = (ss_ships, 1, False)
        self.ze.ship_groups[0][0].insert(
            0, self.ze.userShip.name("U47").id)  # 尽可能狼群U47旗舰

        return self.ze.change_ships()


class Mission_5_5_B(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_5_5_B, self).__init__('5-5B', 505, ze)

    def set_first_nodes(self):
        self.node_b = zrobot.Node(
            'B', additional_spy_filter=lambda sr: '战巡' in str(sr) or '雷巡' in str(sr))
        return self.node_b

    def prepare(self):
        boss_ships = [9210, 5324]  # 牛仔级
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
        zrobot._logger.debug("ca_ships:{}".format(
            [(s.name, s.level) for s in ships]))

        for i in range(1, 5):
            self.ze.ship_groups[i] = (ca_ships, 1, False)

        self.ze.ship_groups[0] = (boss_ships, 1, True)
        self.ze.ship_groups[5] = (cv_ship, 1, True)

        return self.ze.change_ships()


class Mission_2_5_up(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_2_5_up, self).__init__('2-5-up', 205, ze)

    def set_first_nodes(self):
        self.node_a = self.node_chain([zrobot.Node('A', enemy_avoid='20502003'),
                                       zrobot.Node('B'),
                                       zrobot.Node('c', node_type='resource').add_next(
                                           zrobot.Node('g').add_next(
                                               zrobot.Node('j', night_flag=1, formation=4))),
                                       zrobot.Node('f'),
                                       zrobot.Node(
                                           'j', night_flag=1, formation=4),
                                       ])
        return self.node_a

    def prepare(self):
        if 10010213 in self.ze.unlockShip:
            zrobot._logger.debug('有陆奥了')
            return False
        # 所有高级潜艇
        ss_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [ship["level"] > 60,
                          ship.type in ['潜艇'],
                          ]
            if all(conditions):
                ss_ships.append(ship.id)
        zrobot._logger.debug("ss_ships:{}".format(
            [(self.ze.userShip[ship_id].name, self.ze.userShip[ship_id].level) for ship_id in ss_ships]))

        for i in range(1, 4):
            self.ze.ship_groups[i] = (ss_ships, 0, False)
        self.ze.ship_groups[0] = ([43014], 0.8, True)
        self.ze.ship_groups[4] = ([115], 0.8, True)
        self.ze.ship_groups[5] = ([43707], 0.8, True)

        return self.ze.change_ships()


class Mission_2_5_down(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_2_5_down, self).__init__('2-5down', 205, ze)

    def set_first_nodes(self):
        self.node_a = zrobot.Node('A', additional_spy_filter=lambda sr: len(
            sr['enemyVO']['enemyShips']) == 5)
        # self.node_a = Node('A', node_type='skip')
        self.node_b = zrobot.Node('B')
        self.node_e = zrobot.Node('E', node_type='resource')
        self.node_i = zrobot.Node('I')
        self.node_l = zrobot.Node('L', night_flag=1, formation=4)
        self.node_m = zrobot.Node('M', night_flag=1, formation=4)
        self.node_n = zrobot.Node('N', night_flag=1, formation=4)

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
        zrobot._logger.debug("ss_ships:{}".format(
            [(s.name, s.level) for s in ships]))

        for i in range(0, 6):
            self.ze.ship_groups[i] = (ss_ships, 0, False)
        self.ze.ship_groups[0][0].insert(0, 6744)  # 尽可能狼群U47旗舰

        return self.ze.change_ships()


class Mission_6_3(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_6_3, self).__init__('6-3', 603, ze)

    def set_first_nodes(self):
        self.node_b = zrobot.Node(
            'B', enemy_target=zemulator.ZjsnShip.type_id('重巡'), formation=4)
        # self.node_a = Node('A', node_type='skip')
        self.node_e = zrobot.Node('E', formation=4)
        self.node_h = zrobot.Node('H', formation=4)
        self.node_j = zrobot.Node('J', formation=4, night_flag=1)

        self.node_b.add_next(self.node_e)
        self.node_e.add_next(self.node_h)
        self.node_h.add_next(self.node_j)
        return self.node_b

    def prepare(self):
        if 10030812 in self.ze.unlockShip and 10021811 in self.ze.unlockShip:
            zrobot._logger.info('有哥特兰和古斯塔夫了')
            return False
        # 所有能开幕的水下船只
        ss_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [ship["level"] > 75,
                          ship.type in ['潜艇', '炮潜'],
                          ]
            if all(conditions):
                ss_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in ss_ships]
        zrobot._logger.debug("ss_ships:{}".format(
            [(s.name, s.level) for s in ships]))

        for i in range(0, 6):
            self.ze.ship_groups[i] = (ss_ships, 0, False)
        self.ze.ship_groups[0][0].insert(0, 6744)  # 尽可能狼群U47旗舰

        return self.ze.change_ships()


class MissionPants(zrobot.Mission):
    """"""

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(MissionPants, self).__init__('pants', 201, ze)
        self.pants_num = 0
        self.pants_yesterday = 20
        self.enable = True
        self.last_pants_time = self.ze.now

    def set_first_nodes(self):
        self.node_b = zrobot.Node('B', node_type='resource')
        self.node_d = zrobot.Node('D', node_type='resource')
        self.node_f = zrobot.Node(
            'F', night_flag=1, enemy_target=zemulator.ZjsnShip.type_id('补给'))
        self.node_b.add_next(self.node_d)
        self.node_d.add_next(self.node_f)

        return self.node_b

    @property
    def pants_available(self):
        now = self.ze.now
        if self.last_pants_time < self.ze.now.replace(hour=0, minute=0, second=0) < now:
            self.pants_yesterday = self.ze.spoils
        return self.ze.spoils_event and self.ze.todaySpoilsNum < 50

    def prepare(self):
        if not self.pants_available:
            self.available = False
            return

        if self.count > 100:
            zrobot._logger.warning('pants {}, SL {}'.format(
                self.ze.todaySpoilsNum, self.count))
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
        zrobot._logger.debug("dd_ships:{}".format(
            [(s.name, s.level) for s in ships]))

        # 所有高级改造cv
        cv_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=False):
            conditions = [ship.type in ['航母'],
                          ship.level > 1,
                          ship.evolved == 1 or not ship.can_evo,
                          ]
            if all(conditions):
                cv_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in cv_ships]
        zrobot._logger.debug("cv_ships:{}".format(
            [(s.name, s.level) for s in ships]))

        self.ze.ship_groups = [()]*6
        for i in range(0, 4):
            self.ze.ship_groups[i] = (dd_ships, 1, False)
        for i in range(2, 4):
            self.ze.ship_groups[i] = (cv_ships, 1, False)
        # self.ze.ship_groups[2] = ([self.ze.userShip.name("约克城").id], 1, True)
        self.ze.ship_groups[4] = self.ze.ship_groups[5] = (None, 1, False)

        return self.ze.change_ships()

    def summery(self):
        if self.success:
            zrobot._logger.info("{} SL {} 次, 共捞{}胖次, result:{}".format(
                self.mission_name, self.count,
                self.ze.todaySpoilsNum + 1,
                [(i.name, i.level) for i in self.ze.working_ships]))
            self.count = 0
            self.last_pants_time = self.ze.now


class Mission_4_3(zrobot.Mission):
    """一次45铝，一小时2700铝，再见了，远征铝"""

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('偷铝', 403, ze)

    def set_first_nodes(self):
        self.node_b = zrobot.Node('B')
        self.node_d = zrobot.Node('D', node_type='resource')

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
        zrobot._logger.debug("dd_ships:{}".format(
            [(s.name, s.level) for s in ships]))

        self.ze.ship_groups[0] = (dd_ships, 0, False)  # 旗舰必须是完好的防止大破
        for i in range(1, 4):
            self.ze.ship_groups[i] = (dd_ships, 1, False)
        self.ze.ship_groups[4] = self.ze.ship_groups[5] = (None, 1, False)

        return self.ze.change_ships()

    def summery(self):
        super().summery()
        if self.success:
            if 'userResVo' in self.node_d.battle_result:
                zrobot._logger.info("资源： 油:{0[oil]:<7} 弹:{0[ammo]:<7} 钢:{0[steel]:<7} 铝:{0[aluminium]:<7}".format(
                    self.node_d.battle_result['userResVo']))


class Mission_5_3(zrobot.Mission):
    """一次45铝，一小时2700铝，再见了，远征铝"""

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('偷钢', 503, ze)

    def set_first_nodes(self):
        self.node_b = zrobot.Node('B')
        self.node_d = zrobot.Node('D', node_type='resource')

        self.node_b.add_next(self.node_d)
        self.aluminum = 0

        return self.node_b

    def prepare(self):
        # 所有高级DD
        dd_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=False):
            conditions = [ship["level"] > 80,
                          ship.type in ['驱逐'],
                          # ship.evolved == 1,
                          ]
            if all(conditions):
                dd_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in dd_ships]
        zrobot._logger.debug("dd_ships:{}".format(
            [(s.name, s.level) for s in ships]))

        self.ze.ship_groups[0] = (dd_ships, 0, False)  # 旗舰必须是完好的防止大破
        for i in range(1, 4):
            self.ze.ship_groups[i] = (dd_ships, 1, False)
        self.ze.ship_groups[4] = self.ze.ship_groups[5] = (None, 1, False)

        return self.ze.change_ships()

    def summery(self):
        super().summery()
        if self.success:
            if 'userResVo' in self.node_d.battle_result:
                zrobot._logger.info("资源： 油:{0[oil]:<7} 弹:{0[ammo]:<7} 钢:{0[steel]:<7} 铝:{0[aluminium]:<7}".format(
                    self.node_d.battle_result['userResVo']))


class Mission_2_2(zrobot.Mission):
    """一次17油，一小时1000油，效率高于远征，大有可为"""

    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('偷油', 202, ze)

    def set_first_nodes(self):
        self.node_a = zrobot.Node('A')
        self.node_c = zrobot.Node('C', node_type='resource')

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
        zrobot._logger.debug("dd_ships:{}".format(
            [(s.name, s.level) for s in ships]))

        for i in range(1, 6):
            self.ze.ship_groups[i] = (None, 1, False)
        self.ze.ship_groups[0] = (dd_ships, 0, False)

        return self.ze.change_ships()


# class Mission_1_1(zrobot.Mission):
#     def __init__(self, ze: zemulator.ZjsnEmulator):
#         super(Mission_1_1, self).__init__('1-1A', 101, ze)

#     def set_first_nodes(self):
#         self.node_a = zrobot.Node('A')
#         return self.node_a

#     def prepare(self):
#         # 所有高级改造DD
#         dd_ships = []
#         for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
#             conditions = [100 > ship["level"] > 20,
#                           ship.type in ['驱逐'],
#                           ship.evolved == 1,
#                           ]
#             if all(conditions):
#                 dd_ships.append(ship.id)
#         ships = [self.ze.userShip[ship_id] for ship_id in dd_ships]
#         zrobot._logger.debug("dd_ships:{}".format(
#             [(s.name, s.level) for s in ships]))

#         for i in range(1, 6):
#             self.ze.ship_groups[i] = (None, 1, False)
#         self.ze.ship_groups[0] = (dd_ships, 1, False)

#         try:
#             self.ze.change_ships()
#         except zemulator.ZjsnError:
#             return False
#         return True


class Mission_6_4(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_6_4, self).__init__('6-4', 604, ze)
        self.pants_num = 0

    def set_first_nodes(self):
        self.node_a = self.node_chain([zrobot.Node('A', enemy_avoid=zemulator.ZjsnShip.type_id('战巡')),
                                       zrobot.Node('B'),
                                       zrobot.Node('e', enemy_avoid=zemulator.ZjsnShip.type_id('潜艇'), night_flag=1)])
        return self.node_a

    def prepare(self):
        if 10023712 in self.ze.unlockShip:
            zrobot._logger.debug('有昆特了')
            return False
        boss_ships = [s.id for s in self.ze.userShip if s.name ==
                      '赤城' and s.level > 80]  # 赤城带队洗地
        cv_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [20 < ship["level"] < 100,
                          ship.type in ['航母'],
                          ship.name not in ['突击者', '赤城'],
                          ]
            if all(conditions):
                cv_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in cv_ships]
        zrobot._logger.debug("cv_ships:{}".format(
            [(s.name, s.level) for s in ships]))

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
        zrobot._logger.debug("ca_ships:{}".format(
            [(s.name, s.level) for s in ships]))

        for i in range(0, 6):
            self.ze.ship_groups[i] = (cv_ships, 1, True)
        # boss_ships = cv_ships
        self.ze.ship_groups[0] = (boss_ships, 1, True)
        self.ze.ship_groups[1] = ([229], 1, True)
        self.ze.ship_groups[2] = (ca_ships, 1, True)

        return self.ze.change_ships()


class Mission_6_4_fish(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_6_4_fish, self).__init__('6-4 fish', 604, ze)

    def set_first_nodes(self):
        # self.node_a = Node('A', additional_spy_filter=lambda sr: '战巡' in str(sr) or '航母'in str(sr))
        self.node_c = self.node_chain(
            [zrobot.Node('c', formation=4, night_flag=1),
             zrobot.Node('f', formation=4),
             zrobot.Node('h'),
             zrobot.Node('j', node_type="resource"),
             zrobot.Node('l', enemy_target='20100003', formation=4),
            ]
        )
        self.node_b = self.node_chain([zrobot.Node('b', formation=4, night_flag=1),
                                       zrobot.Node(
                                           'd', formation=4, night_flag=1),
                                       ])
        self.node_a = zrobot.Node('a', enemy_avoid=zemulator.ZjsnShip.type_id('驱逐'))
        self.node_a.add_next(self.node_b)
        self.node_a.add_next(self.node_c)
        return self.node_a

    def prepare(self):
        target = 10023712
        if target in self.ze.unlockShip:
            zrobot._logger.info('有{}了'.format(
                zemulator.SHIP_CARD[target]["title"]))
            return False
        # 所有能开幕的水下船只
        ss_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [ship["level"] > 75,
                          ship.type in ['潜艇', '炮潜'],
                          ]
            if all(conditions):
                ss_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in ss_ships]
        zrobot._logger.debug("ss_ships:{}".format(
            [(s.name, s.level) for s in ships]))

        for i in range(0, 6):
            self.ze.ship_groups[i] = (ss_ships, 0, False)
        self.ze.ship_groups[0][0].insert(0, 6744)  # 尽可能狼群U47旗舰

        return self.ze.change_ships()


class MissionEvent2(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('E9', 9940, ze)
        # self.battle_fleet = [229, 370, 16523, 1410, 115, 43707]
        self.battle_fleet = []
        self.enable = True

    def set_first_nodes(self):
        self.node_a = self.node_chain([zrobot.Node('b', enemy_target=994003001),
                                       zrobot.Node('f', node_type="skip"),
                                       zrobot.Node('j', node_type="resource"),
                                       zrobot.Node('p'),
                                       zrobot.Node(
                                           'q', formation=4, night_flag=1),
                                       ])

        return self.node_a

    def prepare(self):
        if self.boss_hp == 0:
            return False

        # fleet = [self.ze.userShip.name(name).id for name in self.battle_fleet]
        if not self.battle_fleet:
            self.battle_fleet = self.ze.working_ships_id
        fleet = self.battle_fleet
        fleet_group = [([i], 0.9, True) for i in fleet]
        self.ze.ship_groups = fleet_group

        return self.ze.change_ships()

    def summery(self):
        super().summery()
        zrobot._logger.debug("boss hp={}".format(self.boss_hp))


class MissionEvent_ex(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('event_ex', 9951, ze)
        self.battle_fleet = []

    def set_first_nodes(self):
        self.node_a = self.node_chain([zrobot.Node('b'),
                                       zrobot.Node('g', node_type="resource"),
                                       zrobot.Node('l', formation=5),
                                       ])

        return self.node_a

    def prepare(self):
        # if 10029011 in self.ze.unlockShip:
        #     zrobot._logger.debug("有96了，告别ex")
        #     return False

        # fleet = [self.ze.userShip.name(name).id for name in self.battle_fleet]
        if not self.battle_fleet:
            self.battle_fleet = self.ze.working_ships_id
        fleet = self.battle_fleet
        fleet_group = [([i], 0.85, True) for i in fleet]
        self.ze.ship_groups = fleet_group

        return self.ze.change_ships()


class MissionEvent_E7(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('e7', 9948, ze)
        self.battle_fleet = [13598, 13664, 1519, 11872, 115, 43707]
        # self.battle_fleet = []

    def set_first_nodes(self):
        self.node_a = self.node_chain([zrobot.Node('a', node_type='skip'),
                                       zrobot.Node('d'),
                                       zrobot.Node('i', node_type='resource'),
                                       zrobot.Node('o', node_type='resource'),
                                       zrobot.Node('r'),
                                       ])
        self.node_a.add_next(zrobot.Node('c', formation=5))
        self.node_a.skip_rate_limit = 0.8

        return self.node_a

    def prepare(self):
        if 10015413 in self.ze.unlockShip:
            zrobot._logger.debug("有勇敢了，告别E7")
            return False

        # fleet = [self.ze.userShip.name(name).id for name in self.battle_fleet]
        if not self.battle_fleet:
            self.battle_fleet = self.ze.working_ships_id
        fleet = self.battle_fleet
        fleet_group = [([i], 0.85, True) for i in fleet]
        self.ze.ship_groups = fleet_group

        return self.ze.change_ships()


class MissionEvent(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        event_base = 9954
        super().__init__('event', event_base + 6, ze)
        # [16523,229,1519,11872,115,43707]
        self.battle_fleet = []

    def set_first_nodes(self):
        # temp = zrobot.Node.DEFAULT_SLEEP_TIME
        # zrobot.Node.DEFAULT_SLEEP_TIME = 20
        # self.ze.working_fleet = 3
        self.node_a = self.node_chain([zrobot.Node('b'),
                                       zrobot.Node('d'),
                                       zrobot.Node('k', node_type='resource'),
                                    #    zrobot.Node('o', node_type=zrobot.NODE_SKIP),
                                       zrobot.Node('p'),
                                       zrobot.Node('r', night_flag=1, formation=4),
                                       ])
        # self.node_a.skip_rate_limit = 0.8
        # zrobot.Node.DEFAULT_SLEEP_TIME = temp
        

        return self.node_a

    def prepare(self):
        if self.boss_hp == 0:
            return False

        # fleet = [self.ze.userShip.name(name).id for name in self.battle_fleet]
        if not self.battle_fleet:
            self.battle_fleet = self.ze.working_ships_id
            zrobot._logger.debug("current battle ships are : {}".format([s.name for s in self.ze.working_ships]))
        fleet = self.battle_fleet
        fleet_group = [([i], 0.85, True) for i in fleet]
        self.ze.ship_groups = fleet_group

        return self.ze.change_ships()

    def summery(self):
        super().summery()
        zrobot._logger.debug("boss hp={}".format(self.boss_hp))


class ChinaRobot(zrobot.Robot):
    def __init__(self):
        super().__init__('junhongbill', 'ouzhoutiduzjsn')
        self.ze.equipment_formula = [10, 90, 90, 30]
        self.ze.boat_formula = [200, 30, 200, 30]
        self.explore.explore_table = (
            ([11063, 329, 58584, 44607, 44538, 63100], '20002'),
            ([7367, 13972, 11497, 8452, 3822, 53932], '10003'),
            ([128, 14094, 113, 101, 52334, 7373], '40001'),
            ([123, 13973, 10800, 53659, 10706, 104], '20001')
        )
        # self.campaign.mission_code = 102
        # self.ze.unlocked_report()
        # for ship in self.ze.userShip:
        #     n = ship.name.replace("日", "曰")
        #     if ship.nick_name != n:
        #         print("{} renamed to {}".format(ship.nick_name, ship.name))
        #         self.ze.rename_ship(ship.id, n)

    def set_missions(self):
        challenge = zrobot.Challenge(self.ze)
        challenge.ninghai = 1215
        challenge.friends = [2593850, 74851, 2827412]

        self.add_mission(challenge)
        self.add_mission(zrobot.TacticTrain(self.ze))
        self.add_mission(Mission_6_3(self.ze))
        self.add_mission(MissionEvent_ex(self.ze))
        # self.add_mission(Mission_6_4_fish(self.ze))
        # self.add_mission(Mission_5_2_C(self.ze))
        # self.add_mission(Mission_2_5_mid(self.ze))
        # self.add_mission(Mission_2_5_down(self.ze))
        # self.add_mission(Mission_2_5_up(self.ze))
        self.add_mission(Mission_5_5_C(self.ze))
        self.add_mission(zrobot.Mission_1_1(self.ze))
        # self.add_mission(Mission_4_3(self.ze))
        # self.add_mission(Mission_2_2(self.ze))
        # self.add_mission(Mission_5_5_B(self.ze))
        self.add_mission(Mission_6_4(self.ze))
        self.add_mission(MissionEvent(self.ze))

        self.pants = MissionPants(self.ze)
        self.add_mission(self.pants)


if __name__ == '__main__':
    r = ChinaRobot()
    # r.missions['event'].switch()
    # r.missions['6-4'].switch()
    # r.missions['pants'].switch()
    # r.missions['5-5C'].enable = True
    # r.missions['kill_fish'].switch()
    # r.kill_fish.boss_ships = '密苏里'
    # r.missions['TacticTrain'].switch()
    t = r.start()
