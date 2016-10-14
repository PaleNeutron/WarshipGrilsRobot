import requests
import time
import logging
import json
import collections
import os

zlogger = logging.getLogger(__name__)

with open(os.path.dirname(os.path.realpath(__file__)) + os.sep + "init.txt", encoding="utf8") as f:
    __ZJSN_DATA = json.load(f)

shipCard = {i['cid']: i for i in __ZJSN_DATA["shipCard"]}
errorCode = __ZJSN_DATA['errorCode']


class ZjsnError(Exception):
    """docstring for ZjsnError"""
    def __init__(self, message, eid=0):
        super(ZjsnError, self).__init__(message)
        self.eid = eid


class ZjsnApi(object):
    """docstring for ZjsnApi"""

    def __init__(self):
        super(ZjsnApi, self).__init__()
        self.login = "/index/login/"
        self.init = "/api/initGame/"
        self.explore = "/explore/start/"   #10003/'
        self.cancel_explore = '/explore/cancel/'   #10003/'
        self.getExploreResult = "/explore/getResult/"
        self.repair = "/boat/repair/"
        self.repairComplete = "/boat/repairComplete/"
        self.dismantleBoat = "/dock/dismantleBoat/"  # [209]/1/ 1为不卸装备
        # 1/[1096,1020,106,433] 快速编队
        self.instantFleet = "/boat/instantFleet/"
        # [1096]/ 快速修理
        self.instantRepairShips = "/boat/instantRepairShips/"
        self.getAward = "/task/getAward/"  # 2201632/ 完成任务
        self.strengthen = "/boat/strengthen/"  # 6744/[31814,31799,31796,31779] 强化
        self.lock = "/boat/lock/"  # 126/  锁船
        self.skip = '/pve/SkipWar/'


class ZjsnUserShip(dict):
    """docstring for ZjsnUserShip"""

    def __init__(self, *args, **kwargs):
        super(ZjsnUserShip, self).__init__(*args, **kwargs)

    def __getitem__(self, item):
        if type(item) == ZjsnShip:
            return item
        elif type(item) == dict:
            return ZjsnShip(item)
        else:
            try:
                return super(ZjsnUserShip, self).__getitem__(item)
            except KeyError:
                raise KeyError("no such ship with id" + str(item))

    def __iter__(self):
        return iter(self.values())

    def update(self, E=None, **F):
        if "id" in E:
            super(ZjsnUserShip, self).__init__({E['id']: ZjsnShip(E)}, **F)
        else:
            for ship in E:
                super(ZjsnUserShip, self).__init__({ship['id']: ZjsnShip(ship)}, **F)


    def broken_ships(self, broken_level=0):
        """broken level 0 : 擦伤, 1 : 中破,  2 : 大破"""
        broken_ships = []
        for ship in self:
            if ship.should_be_repair(broken_level):
                broken_ships.append(ship.id)
                zlogger.debug(
                    "{}(id={}) is broken".format(ship.name, ship.id))
        return broken_ships


class ZjsnShip(dict):
    """docstring for ZjsnUserShip"""

    def __init__(self, *args, **kwargs):
        super(ZjsnShip, self).__init__(*args, **kwargs)
        self.type_list = ['全部',
                          '航母',
                          '轻母',
                          '装母',
                          '战列',
                          '航战',
                          '战巡',
                          '重巡',
                          '航巡',
                          '雷巡',
                          '轻巡',
                          '重炮',
                          '驱逐',
                          '潜母',
                          '潜艇',
                          '炮潜',
                          '补给',
                          '其他',]

    @property
    def id(self):
        return self['id']

    @property
    def cid(self):
        return self["shipCid"]

    @property
    def locked(self):
        return self["isLocked"]

    @property
    def name(self):
        return shipCard[self.cid]['title']

    @property
    def type(self):
        return self.type_list[shipCard[self.cid]['type']]

    @property
    def level(self):
        return self['level']

    @property
    def strength_exp(self):
        current_attribute = list(collections.OrderedDict(sorted(self['strengthenAttribute'].items())).values())
        max_attribute = list(
            collections.OrderedDict(sorted(shipCard[self.cid]['strengthenTop'].items())).values())
        tmp = [m - c for m, c in zip(max_attribute, current_attribute)]
        result = [tmp[1], tmp[3], tmp[2], tmp[0]]
        return result

    @property
    def status(self):
        return self['status']

    @property
    def can_evo(self):
        return shipCard[self.cid]['canEvo']

    @property
    def evolved(self):
        return shipCard[self.cid]['evoClass']

    @property
    def fleet_id(self):
        return self["fleetId"]


    def should_be_repair(self, broken_level=0):
        """broken level 0 : 擦伤, 1 : 中破,  2 : 大破"""
        conditions = [self.status != 2,  # 没有被维修
                      # ship["fleetId"] == 0 or ship["fleetId"] == 1, #
                      # 不在除了第一舰队之外的任何舰队中
                      ]
        if broken_level == 0:
            conditions.append(
                self["battleProps"]["hp"] < self["battlePropsMax"]["hp"])
        elif broken_level == 1:
            conditions.append(
                self["battleProps"]["hp"] * 2 < self["battlePropsMax"]["hp"])
        elif broken_level == 2:
            conditions.append(
                self["battleProps"]["hp"] * 4 < self["battlePropsMax"]["hp"])
        return all(conditions)


class ZjsnEmulator(object):
    """docstring for ZjsnEmulator"""

    def __init__(self):
        super(ZjsnEmulator, self).__init__()
        self.s = requests.Session()
        self.repairDock = [{}]
        self.userShip = ZjsnUserShip()
        self.pveExplore = [{}]
        self.fleet = [{}]
        self.unlockShip = []

        # with open("shipCard.json", encoding="utf8") as f:
        #     self.shipCard = json.load(f)

        self.initGame = ""

        self.username = "junhongbill"
        self.password = "ouzhoutiduzjsn"

        self.url_passport_hm = "http://login.jr.moefantasy.com/index/passportLogin"
        self.url_server = 'http://s2.jr.moefantasy.com'

        self.working_fleet = 1

        self.api = ZjsnApi()

        self.common_lag = 25  # 远征和修理收取的延迟秒数
        self.operation_lag = 1  # 每次操作的延迟秒数

        self.node = 0

        self.mission_flag = ""

        # self.connection_error = 0
        self.ship_groups = [[]] * 6
        self.award_list = []

        self.FLAG_FULL = "船满"
        self.FLAG_REPAIR = "维修中,无法出击"
        self.FLAG_EXPLORE = "远征中,无法出击"
        self.FLAG_EXIT = "退出"

    def get(self, url, error_count=0, sleep_flag=True, method='GET',**kwargs):
        """kwargs: sleep=True"""
        if error_count > 3:
            raise ConnectionError("lost connection")
        error_count += 1

        try:
            r = self.s.request(method, url, **kwargs)
        except requests.exceptions.ConnectionError:
            return self.get(url, error_count, sleep_flag, method, **kwargs)
        if sleep_flag:
            time.sleep(self.operation_lag)

        if r.status_code != 200:
            return self.get(url, error_count, sleep_flag, method, **kwargs)
        elif "eid" in r.json():
            eid = r.json()["eid"]
            if eid == -1:  # 操作太快
                time.sleep(self.operation_lag * 2)
                return self.get(url, error_count, sleep_flag, method, **kwargs)
            else:
                raise ZjsnError(errorCode[str(eid)], r.json()["eid"])
        else:
            if "updateTaskVo" in r.json():
                for task in r.json()["updateTaskVo"]:
                    if all([c["totalAmount"] == c["finishedAmount"] for c in task["condition"]]):
                        self.award_list.append(task["taskCid"])
                        zlogger.debug("task {} finish".format(task["taskCid"]))
            return r.json()

    def login(self):
        self.s = requests.Session()
        r1 = self.get(self.url_passport_hm, method='POST',
                      sleep_flag=False,
                      data={"username": self.username,
                            "pwd": self.password})
        self.s.cookies = requests.utils.cookiejar_from_dict(dict(r1.cookies))
        # 亲测userID没有作用，决定登陆哪个账号的是cookie
        self.get(self.url_server + self.api.login + r1["userId"], sleep_flag=False)
        self.initGame = self.get(self.url_server + self.api.init, sleep_flag=False)
        self.get(self.url_server + "/pve/getPveData/", sleep_flag=False)
        self.get(self.url_server + "/pevent/getPveData/", sleep_flag=False)

        j = self.initGame
        self.userShip.update(j["userShipVO"])
        self.pveExplore = j["pveExploreVo"]["levels"]
        self.repairDock = j["repairDockVo"]
        self.fleet = j["fleetVo"]
        self.unlockShip = j["unlockShip"]

    def get_award(self):
        for task_cid in self.award_list:
            self.get(
                self.url_server + self.api.getAward + "{}/".format(task_cid))
        self.award_list = []

    def change_ships(self):
        for i, ship_id in enumerate(self.fleet[self.working_fleet - 1]["ships"]):
            ship = self.userShip[ship_id]
            ship_group, b_level, instant_flag = self.ship_groups[i]
            changed_flag = False
            if ship.should_be_repair(b_level):
                if len(ship_group) > 0:
                    new_ship = ship_group.pop()
                    self.fleet[self.working_fleet - 1]["ships"][i] = new_ship
                    zlogger.debug("{}上场了".format(ZjsnShip(new_ship).name))
                    changed_flag = True
                elif instant_flag == True:
                    self.repair(ship.id, 0, instant=True)
                else:
                    KeyError("no ship to use in location {}".format(i))

                if changed_flag:
                    self.instant_fleet(self.fleet[self.working_fleet - 1]["ships"])

    # def get_ship(self, ship_id):
    #     if type(ship_id) == dict:
    #         return ship_id
    #     else:
    #         for ship in self.userShip:
    #             if ship["id"] == ship_id:
    #                 return ship
    #         raise KeyError("no such ship")

    # def get_substitue(self, location, broken_ship_id):
    #     for i, ship_id in enumerate(self.ship_groups[location]):
    #         ship = self.userShip[ship_id]
    #         repair_flag = ship.should_be_repair()
    #         if ship["status"] != 2 and not repair_flag:
    #             self.ship_groups[location][i] = broken_ship_id
    #             return ship_id
    #     raise KeyError("no ship to use in location {}".format(location))



    def go_home(self):
        r_sl = self.get(self.url_server + "/active/getUserData/", sleep_flag=False)
        r_sl = self.get(self.url_server + "/pve/getUserData/", sleep_flag=False)
        r_sl = self.get(self.url_server + "/campaign/getUserData/", sleep_flag=False)
        self.get_award()

    def instant_fleet(self, ships_id):
        r = self.get(self.url_server + self.api.instantFleet + str(self.working_fleet) +
                     "/" + str(ships_id).replace(" ", ""))
        self.fleet[self.working_fleet - 1] = r["fleetVo"][0]
        return r

    def dismantle(self, throw_equipment=0):
        ships_dismantle = []
        for ship in self.userShip:
            conditions = [ship["shipCid"] in self.unlockShip,  # 不是new
                          ship["isLocked"] != 1,  # 没锁
                          ship["shipCid"] not in [  # 10003912,  # 不是欧派塔
                              10009911,  # ,空想
                              10008211,  # ,萤火虫
                              10013512],  # 紫石英
                          ship.type in [12,  # DD
                                        10,  # 轻巡
                                        7,  # 重巡
                                        2]]  # 轻母
            if all(conditions):
                ships_dismantle.append(ship["id"])
        if len(ships_dismantle) > 0:
            r = self.get(self.url_server + self.api.dismantleBoat +
                         str(ships_dismantle).replace(" ", "") + "/{}/".format(throw_equipment))
            del_ships = r['delShips']
            for ship_id in del_ships:
                self.userShip.pop(ship_id, None)
        else:
            r = 0
        return r

    def auto_strengthen(self):
        cid_table = [ship.cid for ship in self.userShip]
        for ship in sorted(self.userShip, key=lambda x: (bool(x.evolved), int(x.level)), reverse=True):
            conditions = [
                ship.locked == 1,
                cid_table.count(ship.cid) == 1,
                ship.can_evo == '0' or ship.evolved == 1,  # 不能改造或者已经改造
                ship.fleet_id in [0, 1],  # 不在远征舰队中
                any(ship.strength_exp),
            ]
            if all(conditions):
                r = self.strengthen(ship)
                if r == 0:
                    break

    def strengthen(self, ship_in, target_attribute=None):
        ship_in = self.userShip[ship_in]
        if not target_attribute:
            target_attribute = [1, 2, 3, 4]
        ships_strengthen = []
        ship_types = []
        food_type = [None, 12, 12, 10]
        for attribute_id, exp_remain in enumerate(ship_in.strength_exp):
            if attribute_id in target_attribute and exp_remain > 0:
                ship_types.append(food_type[attribute_id])

        if not any(ship_types):
            return -1  # 没必要强化

        for ship in self.userShip:
            conditions = [ship["shipCid"] in self.unlockShip,  # 不是new
                          ship["isLocked"] != 1,  # 没锁
                          ship["shipCid"] not in [  # 10003912,  # 不是欧派塔
                              10009911,  # ,空想
                              10008211,  # ,萤火虫
                              10013512],  # 紫石英
                          ship.type in ship_types]
            if all(conditions):
                ships_strengthen.append(ship["id"])
        if len(ships_strengthen) > 0:
            r = self.get(self.url_server + self.api.strengthen + str(ship_in['id']) + "/" +
                         str(ships_strengthen).replace(" ", ""))
            del_ships = r['delShips']
            for ship_id in del_ships:
                self.userShip.pop(ship_id, None)
        else:
            r = 0  # 没船强化
        return r

    # def strengthen_exp_remain(self, ship_id):
    #     ship = self.userShip[ship_id]
    #     current_attribute = list(collections.OrderedDict(sorted(ship['strengthenAttribute'].items())).values())
    #     max_attribute = list(
    #         collections.OrderedDict(sorted(shipCard[ship.cid]['strengthenTop'].items())).values())
    #     tmp = [m - c for m, c in zip(max_attribute, current_attribute)]
    #     result = [tmp[1], tmp[3], tmp[2], tmp[0]]
    #     return result

    # def ship_name(self, ship_id):
    #     try:
    #         ship = self.userShip[ship_id]
    #         name = self.shipCard[str(ship["shipCid"])]["title"]
    #     except KeyError as ke:
    #         name = "unknown ship with cid".format(
    #             self.userShip[ship_id]["shipCid"])
    #     return name

    # def ship_type(self, ship_id):
    #     try:
    #         if type(ship_id) == dict:
    #             ship_type = self.shipCard[str(ship_id["shipCid"])]["type"]
    #         else:
    #             ship_type = self.shipCard[
    #                 str(self.userShip[ship_id]["shipCid"])]["type"]
    #     except KeyError as ke:
    #         ship_type = "unknown ship with cid".format(
    #             self.userShip[ship_id]["shipCid"])
    #     return ship_type

    def explore(self, fleet_id, explore_id):
        r = self.get(
            self.url_server + self.api.explore + str(fleet_id) + "/" + str(explore_id))
        self.pveExplore = r["pveExploreVo"]["levels"]

    def explore_result(self, explore_id):
        r = self.get(
            self.url_server + self.api.getExploreResult + str(explore_id))
        self.pveExplore = r["pveExploreVo"]["levels"]
        return r

    def auto_explore(self):
        for ex in self.pveExplore:
            if ex["endTime"] + self.common_lag < time.time():
                fleet_id = ex["fleetId"]
                explore_id = ex["exploreId"]
                self.explore_result(explore_id)
                self.explore(fleet_id, explore_id)

    def get_explore(self):
        for ex in self.pveExplore:
            if ex["endTime"] + self.common_lag < time.time():
                fleet_id = ex["fleetId"]
                explore_id = ex["exploreId"]
                self.explore_result(explore_id)
                return fleet_id

    # def update_ship_info(self, new_ship):
    #     for i, ship in enumerate(self.userShip):
    #         if ship["id"] == new_ship["id"]:
    #             self.userShip[i] = new_ship.copy()
    #             return
    #     self.userShip.append(new_ship)

    # def update_userShip(self, userShip):
    #     if "id" in userShip:
    #         self.update_ship_info(userShip)
    #     else:
    #         for ship in userShip:
    #             self.update_ship_info(ship)

    def repair_all(self, broken_level=0, instant=False):
        """broken level 0 : 擦伤, 1 : 中破,  2 : 大破
        不会修理第一舰队的船"""
        ships = [i for i in self.userShip.broken_ships(
            broken_level) if i not in self.fleet[self.working_fleet - 1]["ships"]]
        for dock_index, dock in enumerate(self.repairDock):
            if "endTime" in dock:
                if dock["endTime"] + self.common_lag < time.time():
                    self.repair_complete(dock["shipId"], dock_index)
            elif dock["locked"] == 0 and len(ships) > 0:
                self.repair(ships.pop(), dock_index, instant)

    def repair_instant(self, broken_level=1):
        """对第一舰队用快修修理"""
        broken_ships = []
        for ship_id in self.fleet[self.working_fleet - 1]["ships"]:
            if self.userShip[ship_id].should_be_repair(broken_level):
                self.repair(ship_id, 0, instant=True)
                broken_ships.append(self.userShip[ship_id].name)
                zlogger.debug(
                    "instant repair {}".format(self.userShip[ship_id].name))
        return broken_ships

    def repair(self, ship_id, dock_id, instant=False):
        if not instant:
            r = self.get(
                self.url_server + self.api.repair + str(ship_id) + "/" + str(dock_id + 1))
            self.repairDock = r["repairDockVo"]
            self.userShip.update(r["shipVO"])
        else:
            r = self.get(
                self.url_server + self.api.instantRepairShips + "/[" + str(ship_id) + "]/")
            self.userShip.update(r["shipVOs"])

    def repair_complete(self, ship_id, dock_id):
        r = self.get(self.url_server + self.api.repairComplete +
                     str(dock_id + 1) + "/" + str(ship_id))
        self.repairDock = r["repairDockVo"]
        self.userShip.update(r["shipVO"])

    def go_out(self, map_code):
        # try:
        r = self.get(
            self.url_server + "/pve/cha11enge/{0}/{1}/0/".format(map_code, self.working_fleet))
            # self.go_next()
        # except ZjsnError as ke:
        #     if -215 in ke.args:  # 船满了
        #         self.mission_flag = self.FLAG_FULL
        #     elif -413 in ke.args:  # 有船在修
        #         self.mission_flag = self.FLAG_REPAIR
        #     elif -412 in ke.args:
        #         self.mission_flag = self.FLAG_EXPLORE
        #     else:
        #         raise ke
        #     r = ke.args[0]
        # return r

    def go_next(self):
        # todo 确认旗舰大破的eid
        # if self.fleet[self.working_fleet - 1]["ships"][0] in self.userShip.broken_ships(2):
        #     raise KeyError("flagship big broken")
        r = self.get(self.url_server + "/pve/newNext/")
        self.node = r["node"]
        return self.node

    def spy(self):
        r = self.get(self.url_server + "/pve/spy/")
        return r

    def deal(self, formation_code, big_broken_protect=True):
        if [i for i in self.userShip.broken_ships(2) if i in self.fleet[self.working_fleet - 1]["ships"]] and big_broken_protect:
            raise ZjsnError("big broken")
        """阵型编号 1 单纵 2 复纵 3 轮型 4 梯形 5 单横"""
        node = self.node
        r = self.get(
            self.url_server + "/pve/deal/{0}/{1}/{2}".format(node,self.working_fleet, formation_code))
        return r

    def lock(self, ship_id):
        r = self.get(self.url_server + self.api.lock + str(ship_id) + '/')
        return r

    def getWarResult(self, night_flag=0):
        """0 不夜战, 1 夜战"""
        r = self.get(self.url_server + "/pve/getWarResult/" + str(night_flag))
        self.userShip.update(r["shipVO"])
        if "newShipVO" in r:
            new_ships = r["newShipVO"]
            self.userShip.update(new_ships)
            for new_ship in new_ships:
                ship = ZjsnShip(new_ship)
                zlogger.debug(
                "get ship: {}".format(ship.name))
                if ship.cid not in self.unlockShip:
                    self.lock(ship.id)
                    self.unlockShip.append(ship.cid)
        else:
            zlogger.debug("get no ship")
        return r

    def supply(self):
        r = self.get(self.url_server + "/boat/supplyFleet/{}/".format(self.working_fleet))
        return r

    def skip(self):
        r = self.get(self.url_server + self.api.skip)
        return r['isSuccess']

    def war_report(self):
        pass


if __name__ == '__main__':
    e = ZjsnEmulator()
    # e.username = 'paleneutron1'
    # e.url_server = 'http://s13.jr.moefantasy.com'
    e.login()
    for ship in e.userShip:
        print(ship.name, ship.level, ship.id, ship.cid, ship.type, ship.locked, ship.strength_exp)
    e.auto_strengthen()
