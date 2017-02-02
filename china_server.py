import logging

import zemulator
import zrobot


class Mission_6_1_A(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_6_1_A, self).__init__('kill_fish', 601, ze)

    def set_first_nodes(self):
        node_a = zrobot.Node('A', formation=5,
                             additional_spy_filter=lambda x: x["enemyVO"]["enemyFleet"]["id"] == 60102003)
        return node_a
    def boss_ship(self):
        # return [s.id for s in self.ze.userShip if s.type == '潜艇' and s.level < 70]
        return [self.ze.userShip.name('博格').id]
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
        zrobot._logger.debug(
            "dd_ships:{}".format([self.ze.userShip[ship_id].name for ship_id in dd_ships]))

        # boss_ships = [s.id for s in self.ze.userShip if s.type == '重炮' and s.locked]
        if self.boss_ship():
            boss_ships = self.boss_ship()
            self.ze.ship_groups[0] = (boss_ships, 2, True)
        else:
            boss_ships = dd_ships
            self.ze.ship_groups[0] = (boss_ships, 1, False)
        # boss_ships = [self.ze.userShip.name('赤城').id]
        boss_ships.sort(key=lambda x: self.ze.userShip[x].level)
        zrobot._logger.debug("boss_ships:{}".format(
            [self.ze.userShip[ship_id].name for ship_id in boss_ships]))


        for i in range(1, 5):
            self.ze.ship_groups[i] = (dd_ships, 1, False)

        if any([self.ze.userShip[s].speed > 27 for s in boss_ships]):
            self.ze.ship_groups[5] = (slow_ships, 1, False)
            zrobot._logger.debug("slow_ships:{}".format(
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
        self.ze.ship_groups[0][0].insert(0, 6744)  # 尽可能狼群U47旗舰
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError as zerror:
            zrobot._logger.critical(zerror)
            return False
        return True


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


class Mission_5_5_C(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_5_5_C, self).__init__('5-5C', 505, ze)

    def set_first_nodes(self):
        self.node_c = zrobot.Node('C', formation=4,
                                  additional_spy_filter=lambda sr: '战巡' in str(sr) or '航母' in str(sr))
        self.node_f = zrobot.Node('F')
        self.node_i = zrobot.Node('I', formation=4, night_flag=1)
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
        zrobot._logger.debug("ss_ships:{}".format([(s.name, s.level) for s in ships]))

        for i in range(0, 6):
            self.ze.ship_groups[i] = (ss_ships, 1, False)
        self.ze.ship_groups[0][0].insert(0, 6744)  # 尽可能狼群U47旗舰
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True


class Mission_5_5_B(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_5_5_B, self).__init__('5-5B', 505, ze)

    def set_first_nodes(self):
        self.node_b = zrobot.Node('B', additional_spy_filter=lambda sr: '战巡' in str(sr) or '雷巡' in str(sr))
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
        zrobot._logger.debug("ca_ships:{}".format([(s.name, s.level) for s in ships]))

        for i in range(1, 5):
            self.ze.ship_groups[i] = (ca_ships, 1, False)

        self.ze.ship_groups[0] = (boss_ships, 1, True)
        self.ze.ship_groups[5] = (cv_ship, 1, True)
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True


class Mission_2_5_down(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_2_5_down, self).__init__('2-5down', 205, ze)

    def set_first_nodes(self):
        self.node_a = zrobot.Node('A', additional_spy_filter=lambda sr: len(sr['enemyVO']['enemyShips']) == 5)
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
        zrobot._logger.debug("ss_ships:{}".format([(s.name, s.level) for s in ships]))

        for i in range(0, 6):
            self.ze.ship_groups[i] = (ss_ships, 0, False)
        self.ze.ship_groups[0][0].insert(0, 6744)  # 尽可能狼群U47旗舰
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True


class Mission_6_3(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_6_3, self).__init__('6-3', 603, ze)

    def set_first_nodes(self):
        self.node_b = zrobot.Node('B', enemy_target=zemulator.ZjsnShip.type_id('重巡'), formation=4)
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
        zrobot._logger.debug("ss_ships:{}".format([(s.name, s.level) for s in ships]))

        for i in range(0, 6):
            self.ze.ship_groups[i] = (ss_ships, 0, False)
        self.ze.ship_groups[0][0].insert(0, 6744)  # 尽可能狼群U47旗舰
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True


class MissionPants(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(MissionPants, self).__init__('pants', 201, ze)
        self.pants_num = 0
        self.pants_yesterday = 277

    def set_first_nodes(self):
        self.node_b = zrobot.Node('B', node_type='resource')
        self.node_d = zrobot.Node('D', node_type='resource')
        self.node_f = zrobot.Node('F', night_flag=1, enemy_target=zemulator.ZjsnShip.type_id('补给'))
        self.node_b.add_next(self.node_d)
        self.node_d.add_next(self.node_f)

        return self.node_b

    def prepare(self):
        if self.ze.spoils - self.pants_yesterday >= 50:
            self.available = False
            return

        if self.count > 100:
            zrobot._logger.warning('pants {}, SL {}'.format(self.ze.spoils - self.pants_yesterday, self.count))
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
        zrobot._logger.debug("dd_ships:{}".format([(s.name, s.level) for s in ships]))

        for i in range(0, 4):
            self.ze.ship_groups[i] = (dd_ships, 1, False)
        self.ze.ship_groups[2] = ([self.ze.userShip.name("苍龙").id], 1, False)
        self.ze.ship_groups[3] = ([self.ze.userShip.name("企业").id], 1, False)
        self.ze.ship_groups[4] = self.ze.ship_groups[5] = (None, 1, False)

        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

    def summery(self):
        if self.success:
            zrobot._logger.info("{} SL {} 次, 共捞{}胖次, result:{}".format(
                self.mission_name, self.count,
                self.ze.spoils - self.pants_yesterday,
                [(i.name, i.level) for i in self.ze.working_ships]))
            self.count = 0


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
        zrobot._logger.debug("dd_ships:{}".format([(s.name, s.level) for s in ships]))

        self.ze.ship_groups[0] = (dd_ships, 0, False)  # 旗舰必须是完好的防止大破
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
        zrobot._logger.debug("dd_ships:{}".format([(s.name, s.level) for s in ships]))

        for i in range(1, 6):
            self.ze.ship_groups[i] = (None, 1, False)
        self.ze.ship_groups[0] = (dd_ships, 0, False)

        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True


class Mission_1_1(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_1_1, self).__init__('1-1A', 101, ze)

    def set_first_nodes(self):
        self.node_a = zrobot.Node('A')
        return self.node_a

    def prepare(self):
        # 所有高级改造DD
        dd_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [100 > ship["level"] > 20,
                          ship.type in ['驱逐'],
                          ship.evolved == 1,
                          ]
            if all(conditions):
                dd_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in dd_ships]
        zrobot._logger.debug("dd_ships:{}".format([(s.name, s.level) for s in ships]))

        for i in range(1, 6):
            self.ze.ship_groups[i] = (None, 1, False)
        self.ze.ship_groups[0] = (dd_ships, 1, False)

        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True


class Mission_6_4(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_6_4, self).__init__('6-4 两点', 604, ze)
        self.pants_num = 0

    def set_first_nodes(self):
        # self.node_a = Node('A', additional_spy_filter=lambda sr: '战巡' in str(sr) or '航母'in str(sr))
        self.node_a = zrobot.Node('A', enemy_avoid='战巡')
        self.node_b = zrobot.Node('B', night_flag=True)

        self.node_a.add_next(self.node_b)
        return self.node_a

    def prepare(self):
        if 10023712 in self.ze.unlockShip:
            zrobot._logger.debug('有昆特了')
            return False
        boss_ships = [44420, 9210, 5324]  # 密苏里, 牛仔级
        cv_ships = []
        for ship in sorted(self.ze.userShip, key=lambda x: x["level"], reverse=True):
            conditions = [1 < ship["level"] < 99,
                          ship.type in ['航母'],
                          ]
            if all(conditions):
                cv_ships.append(ship.id)
        ships = [self.ze.userShip[ship_id] for ship_id in cv_ships]
        zrobot._logger.debug("cv_ships:{}".format([(s.name, s.level) for s in ships]))

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
        zrobot._logger.debug("ca_ships:{}".format([(s.name, s.level) for s in ships]))

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

class Mission_6_4_fish(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super(Mission_6_4_fish, self).__init__('6-4 fish', 604, ze)
        self.pants_num = 0

    def set_first_nodes(self):
        # self.node_a = Node('A', additional_spy_filter=lambda sr: '战巡' in str(sr) or '航母'in str(sr))
        self.node_c = self.node_chain([zrobot.Node('c', formation=4, night_flag=1),
                                       zrobot.Node('f', formation=4),
                                       zrobot.Node('h'),
                                       zrobot.Node('j', node_type="resource"),
                                       zrobot.Node('l', enemy_target='20100003', formation=4),
                                       ])
        self.node_b = self.node_chain([zrobot.Node('b', formation=4, night_flag=1),
                                       zrobot.Node('d', formation=4, night_flag=1),
                                       ])
        self.node_a = zrobot.Node('a', enemy_avoid='驱逐')
        self.node_a.add_next(self.node_b)
        self.node_a.add_next(self.node_c)
        return self.node_a

    def prepare(self):
        target = 10023712
        if target in self.ze.unlockShip:
            zrobot._logger.info('有{}了'.format(zemulator.shipCard[target]["title"]))
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
        zrobot._logger.debug("ss_ships:{}".format([(s.name, s.level) for s in ships]))

        for i in range(0, 6):
            self.ze.ship_groups[i] = (ss_ships, 0, False)
        self.ze.ship_groups[0][0].insert(0, 6744)  # 尽可能狼群U47旗舰
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

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
                                       zrobot.Node('q', formation=4, night_flag=1),
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
        try:
            self.ze.change_ships()
        except zemulator.ZjsnError:
            return False
        return True

    def summery(self):
        super().summery()
        zrobot._logger.debug("boss hp={}".format(self.boss_hp))

class MissionEvent5(zrobot.Mission):
    def __init__(self, ze: zemulator.ZjsnEmulator):
        super().__init__('E5', 9936, ze)
        self.battle_fleet = [13598, 7865, 830, 13664, 115, 43707]
        # self.battle_fleet = []
        self.enable = True

    def set_first_nodes(self):
        self.node_a = self.node_chain([zrobot.Node('b', enemy_target=993603001),
                                       zrobot.Node('f', node_type="skip"),
                                       zrobot.Node('j', node_type="resource"),
                                       zrobot.Node('p'),
                                       zrobot.Node('q', formation=4, night_flag=1),
                                       ])

        return self.node_a

    def prepare(self):
        if 10028911 in self.ze.unlockShip:
            zrobot._logger("有黄毛了，告别E5")
            return False

        # fleet = [self.ze.userShip.name(name).id for name in self.battle_fleet]
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

class ChinaRobot(zrobot.Robot):
    def __init__(self):
        super().__init__()

        self.ze.username = 'junhongbill'
        self.ze.password = 'ouzhoutiduzjsn'
        self.ze.equipment_formula = [10, 90, 90, 30]
        self.ze.boat_formula = [200, 30, 200, 30]
        self.explore.explore_table = (
            ([35442, 35500, 3846, 7376, 183, 103], '10003'),
            ([42093, 7367, 3877, 13972, 11497, 8452], '50003'),
            ([128, 14094, 113, 101, 577, 7373], '40001'),
            ([123, 13973, 27865, 14138, 10706, 104], '20001')
        )
        self.campaign.mission_code = 402

    def set_missions(self):
        challenge = zrobot.Challenge(self.ze)
        challenge.battle_fleet = [1410, 52359, 213, 13708, 50367, 56604]
        challenge.ninghai = 1215
        challenge.friends = [2593850, 74851, 2827412]
        self.add_mission(challenge)
        self.add_mission(Mission_6_3(self.ze))
        # self.add_mission(MissionEvent5(self.ze))
        # self.add_mission(Mission_6_4_fish(self.ze))
        # self.add_mission(Mission_5_2_C(self.ze))
        # self.add_mission(Mission_2_5_mid(self.ze))
        # self.add_mission(Mission_2_5_down(self.ze))
        self.add_mission(Mission_5_5_C(self.ze))
        # self.add_mission(Mission_1_1(self.ze))
        # self.add_mission(Mission_4_3(self.ze))
        # self.add_mission(Mission_2_2(self.ze))
        # self.add_mission(Mission_5_5_B(self.ze))
        # self.add_mission(Mission_6_4(self.ze))
        self.add_mission(MissionPants(self.ze))
        self.add_mission(Mission_6_1_A(self.ze))


if __name__ == '__main__':
    from transitions import logger as transitions_logger
    from logging import handlers
    import os

    log_formatter = logging.Formatter(
        '%(asctime)s: %(levelname)s: %(message)s', datefmt='%H:%M:%S')
    if os.name == 'nt':
        stream_handler = logging.StreamHandler()
    else:
        stream_handler = handlers.TimedRotatingFileHandler('china_server.log', when='midnight', backupCount=3, encoding='utf8')
    stream_handler.setFormatter(log_formatter)

    f_handler = handlers.TimedRotatingFileHandler('zrobot.log', when='midnight', backupCount=3, encoding='utf8')
    f_handler.setFormatter(log_formatter)

    zrobot._logger.addHandler(stream_handler)
    zrobot._logger.addHandler(f_handler)
    zrobot._logger.setLevel(logging.DEBUG)
    f_handler.setLevel(logging.INFO)

    transitions_logger.addHandler(stream_handler)
    transitions_logger.setLevel(logging.INFO)
    r = ChinaRobot()
    # r.missions['pants'].enable = True
    r.missions['5-5C'].enable = True
    # r.missions['kill_fish'].enable = True
    t = r.start()
