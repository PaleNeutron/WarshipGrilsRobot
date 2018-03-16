#!/usr/bin/env python3
import base64
import collections
import datetime
import distutils.version
import itertools
import json
import logging
import math
import os
import time
from typing import Iterator

import requests
import requests.exceptions

zlogger = logging.getLogger('zjsn.zrobot.zemulator')


# with open(os.path.dirname(os.path.realpath(__file__)) + os.sep + "init.txt", encoding="utf8") as f:
#     __ZJSN_DATA = json.load(f)
#
# _INIT_DATA_.ship_card = {int(i['cid']): i for i in __ZJSN_DATA["shipCard"]}
# _INIT_DATA_.error_code = __ZJSN_DATA['errorCode']
# _INIT_DATA_.equipment_card = {int(i['cid']): i for i in __ZJSN_DATA["shipEquipmnt"]}
# 
# with open(os.path.dirname(os.path.realpath(__file__)) + os.sep + "init_japan.txt", encoding="utf8") as f:
#     __ZJSN_DATA = json.load(f)
# 
# _INIT_DATA_.ship_card.update({int(i['cid']): i for i in __ZJSN_DATA["shipCard"] if int(i['cid']) not in _INIT_DATA_.ship_card})
# _INIT_DATA_.equipment_card.update({int(i['cid']): i for i in __ZJSN_DATA["shipEquipmnt"] if int(i['cid']) not in _INIT_DATA_.equipment_card})

class InitData(object):
    """init data for zjsn"""

    def __init__(self):
        self._data = None
        self._data_j = None
        self.ship_card = None
        self.error_code = None
        self.equipment_card = None
        self.version = distutils.version.LooseVersion("0")
        self.version_japan = distutils.version.LooseVersion("0")
        self.init_file_path = os.path.dirname(os.path.realpath(__file__)) + os.sep + "init.txt"
        self.init_file_path_japan = os.path.dirname(os.path.realpath(__file__)) + os.sep + "init_japan.txt"

        self.load()

    def load(self):
        """load init.txt and parse the json format data"""
        if os.path.exists(self.init_file_path):
            # get china server data
            try:
                with open(self.init_file_path, encoding="utf8") as f:
                    self._data = json.load(f)
                self.ship_card = {int(i['cid']): i for i in self._data["shipCard"]}
                self.error_code = self._data['errorCode']
                self.equipment_card = {int(i['cid']): i for i in self._data["shipEquipmnt"]}
                self.version = distutils.version.LooseVersion(self._data["DataVersion"])
                # get japan server data
                if os.path.exists(self.init_file_path_japan):
                    with open(self.init_file_path_japan, encoding="utf8") as f:
                        self._data_j = json.load(f)
            except json.decoder.JSONDecodeError:
                self.version = distutils.version.LooseVersion("000")
                return
            self.version = distutils.version.LooseVersion(self._data["DataVersion"])
            if self._data_j:
                self.ship_card.update(
                    {int(i['cid']): i for i in self._data_j["shipCard"] if int(i['cid']) not in self.ship_card})
                self.equipment_card.update({int(i['cid']): i for i in self._data_j["shipEquipmnt"] if
                                            int(i['cid']) not in self.equipment_card})
        else:
            self.version = distutils.version.LooseVersion("000")

    def update(self, data, japan=False):
        self._data = data
        if not japan:
            self.rename()
            with open(self.init_file_path, "w", encoding="utf8") as f:
                json.dump(self._data, f)
        else:
            with open(self.init_file_path_japan, "w", encoding="utf8") as f:
                json.dump(self._data, f)
        self.load()

    def get_trans_table(self):
        from pyquery import PyQuery as pq
        name_table = {}
        r = requests.get(
            "https://www.zjsnrwiki.com/wiki/%E6%97%A5%E7%B3%BB%E8%88%B0%E5%90%8D%E5%AF%B9%E7%85%A7%E8%A1%A8", verify=False)
        p = pq(r.text)
        table = p(".wikitable")

        for t in table("tr")[1:]:
            p = pq(t)("td a")
            real_name = p[0].text
            animal_name = p[1].text
            name_table[animal_name] = real_name

        return name_table

    def rename(self):
        tb = self.get_trans_table()
        new_girl = {}
        for girl in self._data["shipCard"]:
            new_girl[girl["cid"]] = girl
            if girl["title"] in tb:
                zlogger.info(girl["title"] + " ==> " + tb[girl["title"]])
                girl["title"] = tb[girl["title"]]


_INIT_DATA_ = InitData()

class ZjsnError(Exception):
    """docstring for ZjsnError"""

    def __init__(self, message, eid=0, last_url=""):
        super(ZjsnError, self).__init__("{}, code:{}, url:{}".format(message, eid, last_url))
        self.eid = int(eid)
        self.last_request = last_url


class ZjsnApi(object):
    """docstring for ZjsnApi"""
    CHINA = "china"
    JAPAN = "japan"

    def __init__(self, host):
        super(ZjsnApi, self).__init__()
        self.host = host
        self.location = self.CHINA

    def checkVer(self):
        if self.location == self.CHINA:
            return "http://version.jr.moefantasy.com/index/checkVer/3.0.0/100011/2&version=3.1.0&channel=100011&market=2"
        elif self.location == self.JAPAN:
            return "http://version.jp.warshipgirls.com/index/checkVer/3.0.0/2/0&market=2&channel=0&version=3.0.0"

    def passport(self):
        if self.location == self.CHINA:
            return "http://login.jr.moefantasy.com/index/passportLogin"
        elif self.location == self.JAPAN:
            return 'http://loginand.jp.warshipgirls.com/index/passportLogin'
    
    def get_init(self):
        if self.location == self.CHINA:
            return "http://login.jr.moefantasy.com/index/getInitConfigs/"
        elif self.location == self.JAPAN:
            return 'http://loginand.jp.warshipgirls.com/index/getInitConfigs/'

    def login(self, user_id):
        return self.host + "/index/login/{}".format(user_id)

    def init(self):
        return self.host + "/api/initGame/"

    def bsea(self):
        """返回3.0版本新增的提督府信息， rsp['bSeaData']['todaySpoilsNum']可以看到今天捞胖次的数量"""
        return self.host + "/bsea/getData/"

    def explore(self, fleet_id, explore_id):
        return self.host + "/explore/start/{fleet_id}/{explore_id}/".format(fleet_id=fleet_id, explore_id=explore_id)

    def cancel_explore(self, explore_id):
        return self.host + '/explore/cancel/{explore_id}/'.format(explore_id=explore_id)

    def getExploreResult(self, explore_id):
        return self.host + "/explore/getResult/{explore_id}/".format(explore_id=explore_id)

    def repair(self, ship_id, dock_id):
        return self.host + "/boat/repair/{ship_id}/{dock_id}".format(ship_id=ship_id, dock_id=dock_id)

    def repairComplete(self, ship_id, dock_id):
        return self.host + "/boat/repairComplete/{dock_id}/{ship_id}".format(ship_id=ship_id, dock_id=dock_id)

    def dismantleBoat(self, ships_dismantle, throw_equipment):
        return self.host + "/dock/dismantleBoat/{ships_dismantle}/{throw_equipment}".format(
            ships_dismantle=str(ships_dismantle).replace(" ", ""), throw_equipment=throw_equipment)  # [209]/1/ 1为不卸装备

    # 1/[1096,1020,106,433] 快速编队
    def instantFleet(self, fleet_id, ships_id):
        return self.host + "/boat/instantFleet/{fleet_id}/{ships_id}".format(
            fleet_id=fleet_id, ships_id=str(ships_id).replace(" ", ""))

    # [1096]/ 快速修理
    def instantRepairShips(self, ships_id):
        return self.host + "/boat/instantRepairShips/{}/".format(str(ships_id).replace(" ", ""))

    def supplyBoats(self, ships_id):
        # 后面的/0/0我也不知道什么意思
        return self.host + '/boat/supplyBoats/{ships_id}/0/0'.format(ships_id=str(ships_id).replace(" ", ""))

    def getAward(self, task_cid):
        return self.host + "/task/getAward/{task_cid}/".format(task_cid=task_cid)  # 完成任务

    def strengthen(self, ship_in, ships_id):
        return self.host + "/boat/strengthen/{ship_in}/{ships_id}".format(
            ship_in=ship_in, ships_id=str(ships_id).replace(" ", ""))  # 6744/[31814,31799,31796,31779] 强化

    def lock(self, ship_id):
        return self.host + "/boat/lock/{ship_id}/".format(ship_id=ship_id)  # 126/  锁船.format()

    def skip(self):
        return self.host + '/pve/SkipWar/'

    def dismantleEquipment(self):
        return self.host + '/dock/dismantleEquipment/'  # 用post方法发送content={"10001921":3}.format()

    def skillLevelUp(self, ship_id):
        return self.host + '/boat/skillLevelUp/{ship_id}'.format(ship_id=ship_id)  # 13674/ 升级技能.format()

    def loginAward(self):
        return self.host + '/active/getLoginAward/'

    def buildBoat(self, dock_id, oil, ammo, steel, aluminum):
        return self.host + '/dock/buildBoat/{}/{}/{}/{}/{}'.format(dock_id, oil, steel, ammo,
                                                                   aluminum)  # 1/400/500/130/400 第一项是船坞ID，后面是油，钢，弹，铝.format()

    def buildEquipment(self, dock_id, oil, ammo, steel, aluminum):
        return self.host + '/dock/buildEquipment/{}/{}/{}/{}/{}'.format(dock_id, oil, steel, ammo,
                                                                        aluminum)  # 1/10/90/90/30 第一项是船坞ID，后面是油，钢，弹，铝.format()

    def getBoat(self, dock_id):
        return self.host + '/dock/getBoat/{}'.format(dock_id)  # 2 最后一位是船坞号.format()

    def getEquipment(self, dock_id):
        return self.host + '/dock/getEquipment/{}'.format(dock_id)  # 2 最后一位是船坞号.format()

    def campaignGetFleet(self, mission_code):
        return self.host + '/campaign/getFleet/{}/'.format(mission_code)  # 202/  202是战役编号.format()

    def campaignChangeFleet(self, mission_code, ship_id, position):
        return self.host + '/campaign/changeFleet/{mission_code}/{ship_id}/{position}/'.format(
            mission_code=mission_code, ship_id=ship_id, position=position
        )  # 202/356/2/ 202是战役编号，356是ship id， 2是船的位置，从0开始.format()

    def campaignSpy(self, mission_code):
        return self.host + '/campaign/spy/{}/'.format(mission_code)  # 402/ 4代表航母战役 02代表难度是困难.format()

    def campaignDeal(self, mission_code, formation_code):
        return self.host + '/campaign/challenge/{}/{}'.format(mission_code,
                                                              formation_code)  # 402/2/ 4代表航母战役 02代表难度是困难 最后的2代表阵型.format()

    def campaignResult(self, night_flag):
        return self.host + '/campaign/getWarResult/{}/'.format(night_flag)  # 1/ 最后的1代表进行夜战.format()

    def kiss(self, ship_id):
        return self.host + '/friend/kiss/{ship_id}'.format(ship_id=ship_id)

    def rename(self, ship_id, new_name):
        return self.host + '/boat/renameShip/{ship_id}/{new_name}/'.format(ship_id=ship_id, new_name=new_name)

    def getTactics(self):
        return self.host + '/live/getTactics'

class ZjsnUserShip(dict):
    """docstring for ZjsnUserShip"""

    def __init__(self, *args, **kwargs):
        super(ZjsnUserShip, self).__init__(*args, **kwargs)
        self.shipNumTop = 0

    def __getitem__(self, item) -> 'ZjsnShip':
        if type(item) == ZjsnShip:
            return item
        elif type(item) == dict:
            return ZjsnShip(item)
        else:
            try:
                return super(ZjsnUserShip, self).__getitem__(int(item))
            except KeyError:
                raise KeyError("no such ship with id {}".format(item))

    def __iter__(self) -> Iterator['ZjsnShip']:
        return iter(self.values())

    def level_order(self, reverse=True) -> 'ZjsnShip':
        """sorted ship objects from z to a"""
        return iter(sorted(self.values(), key=lambda x: x["level"], reverse=True))

    @property
    def unique(self):
        ships = []
        ships_evoCid = []
        for ship in sorted(self, key=lambda x: (x.can_evo or x.evolved, x.level, x.locked), reverse=True):
            if ship.evoCid not in ships_evoCid:
                ships_evoCid.append(ship.evoCid)
                ships.append(ship)
        return ships

    def add_ship(self, ship_dict, ze: "ZjsnEmulator", source='get'):
        self.update(ship_dict)
        for s in ship_dict:
            ship = self[s['id']]
            if ship.cid not in ze.unlockShip:
                ze.lock(ship.id)
                ze.unlockShip.append(ship.cid)
                zlogger.info("{} new ship {}".format(source, ship.name))
            else:
                zlogger.info("{} {}".format(source, ship.name))

    def update(self, E=None, **F):
        if "id" in E:
            super(ZjsnUserShip, self).update({E['id']: ZjsnShip(E)}, **F)
        else:
            new_dict = {ship['id']: ZjsnShip(ship) for ship in E}
            super(ZjsnUserShip, self).update(new_dict, **F)

    def broken_ships_id(self, broken_level=0):
        """broken level 0 : 擦伤, 1 : 中破,  2 : 大破"""
        return [ship.id for ship in self.broken_ships(broken_level)]

    def broken_ships(self, broken_level=0):
        """broken level 0 : 擦伤, 1 : 中破,  2 : 大破"""
        return [ship for ship in self if ship.should_be_repair(broken_level)]

    def save(self, file_name='my_ships.md'):
        markdown_string = ""
        markdown_string += "船名|等级|船型|ID|CID\n"
        markdown_string += "----|----|----|----|----\n"
        for ship in sorted(self, key=lambda x: x["level"], reverse=True):
            if ship["isLocked"] == 1:
                #     if ship["level"] != 1 and str(ship["shipCid"])[-2:]=="11" and ship["fleetId"]==0 and ("10008321" in ship["equipment"] or "10008421" in ship["equipment"]):
                try:
                    markdown_string += "{:<30}|{:<15}|{:<15}|{:<15}|{:<15}\n".format(
                        ship.name, ship["level"], ship.type, ship["id"], ship["shipCid"]
                    )
                except KeyError as ke:
                    print(ke.args)

        # display(Markdown(markdown_string))
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(markdown_string)

    def name(self, ship_name, default="raise") -> 'ZjsnShip':
        """查找船名，返回船对象，不必全称"""
        if type(ship_name) == int:
            return self[ship_name]
        for ship in self.unique:
            if ship_name in ship.name:
                return ship
        if default == "raise":
            raise ZjsnError("no ship called {}".format(ship_name))
        else:
            return default

    def select(self, ships_id) -> 'List[ZjsnShip]':
        return [self[i] for i in ships_id if i != 0]


class ZjsnShip(dict):
    """docstring for ZjsnUserShip"""
    type_list = ['航母',
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
                 '导驱',
                 '防驱', ]

    type_id_list = list(range(1, 17)) + [23, 24]  # 导驱的ID是23，防驱是24

    white_list = [
                     10003912,  # 不是欧派塔
                     10009911,  # ,空想
                     10008211,  # ,萤火虫
                     10013512
                 ],  # 紫石英

    emulator = None  # type: ZjsnEmulator

    def __init__(self, *args, **kwargs):
        super(ZjsnShip, self).__init__(*args, **kwargs)

    def __repr__(self):
        return self.name

    @property
    def id(self):
        return int(self['id'])

    @property
    def cid(self):
        if 'ship_cid' in self:
            return int(self["ship_cid"])
        else:
            return int(self["shipCid"])

    @property
    def locked(self):
        return bool(self["isLocked"])

    @locked.setter
    def locked(self, value):
        self["isLocked"] = value

    @property
    def name(self):
        if self.cid in _INIT_DATA_.ship_card:
            return _INIT_DATA_.ship_card[self.cid]['title'].replace(' ', '')
        else:
            return "unknown ship {}".format(self.cid)

    @property
    def nick_name(self):
        if 'title' in self:
            return self['title']
        else:
            return self.name

    @property
    def type(self):
        if self.cid in _INIT_DATA_.ship_card:
            type_trans_code = ZjsnShip.type_id_list.index(int(_INIT_DATA_.ship_card[self.cid]['type']))
            return ZjsnShip.type_list[type_trans_code]
        else:
            return 0

    @property
    def level(self):
        return self['level']

    @property
    def equipment(self):
        if type(self['equipment']) == dict:
            return self['equipment'].values()
        elif type(self['equipment']) == list:
            return self['equipment']

    @property
    def skillLevel(self):
        return int(self['skillLevel'])

    @property
    def skillType(self):
        return int(self['skillType'])

    @property
    def evoLevel(self):
        if self.evolved:
            return int(_INIT_DATA_.ship_card[int(self.card['evoCid'])]['evoLevel'])
        else:
            return int(self.card['evoLevel'])

    @property
    def card(self):
        if self.cid in _INIT_DATA_.ship_card:
            return _INIT_DATA_.ship_card[self.cid]
        else:
            return 0

    @property
    def star(self):
        if self.cid in _INIT_DATA_.ship_card:
            return int(_INIT_DATA_.ship_card[self.cid]['star'])
        else:
            return 99

    def protected(self):
        conditions = (
            self.cid in self.emulator.unlockShip,  # 不是new
            self.locked != 1,  # 没锁
            self.status == 0,  # 没被修理
            self.id not in self.emulator.fleeted_ships_id,  # 不在任何舰队中
            self.cid not in self.white_list,
            self.star < 5 or self.name in ['欧根亲王', '天狼星', '胡德', '关岛', '阿拉斯加'],  # 小于五星
        )
        return not all(conditions)

    @staticmethod
    def type_id(type_name):
        type_trans_code = ZjsnShip.type_list.index(type_name)
        return ZjsnShip.type_id_list[type_trans_code]

    @property
    def married(self):
        return int(self['married'])

    @property
    def strength_exp(self):
        current_attribute = list(collections.OrderedDict(sorted(self['strengthenAttribute'].items())).values())
        max_attribute = list(
            collections.OrderedDict(sorted(_INIT_DATA_.ship_card[self.cid]['strengthenTop'].items())).values())
        tmp = [m - c for m, c in zip(max_attribute, current_attribute)]
        result = [tmp[1], tmp[3], tmp[2], tmp[0]]
        return result

    @property
    def status(self):
        """0 is free, 1 is explore, 2 is guard, """
        if self.fleet_id:
            fleet_status = self.emulator.fleet[self.fleet_id - 1]['status']
            if fleet_status != 0:
                return fleet_status
        return int(self['status'])

    @property
    def available(self):
        return self.status == 0

    @property
    def fleet_able(self):
        if self.fleet_id:
            fleet_status = self.emulator.fleet[self.fleet_id - 1]['status']
            if fleet_status != 0:
                return False
        return True

    @property
    def can_evo(self):
        return int(_INIT_DATA_.ship_card[self.cid]['canEvo'])

    @property
    def evoCid(self):
        return _INIT_DATA_.ship_card[self.cid]['evoCid']

    @property
    def evolved(self):
        return int(_INIT_DATA_.ship_card[self.cid]['evoClass'])

    @property
    def fleet_id(self):
        return self["fleetId"]

    @property
    def speed(self):
        return float(self["battleProps"]["speed"])

    @property
    def repair_time(self):
        if self["battlePropsMax"]["hp"] == self["battleProps"]["hp"]:
            return 0

        r = _INIT_DATA_.ship_card[self.cid]['repairTime']
        l = self.level
        d = self["battlePropsMax"]["hp"] - self["battleProps"]["hp"]
        if self.married:
            m = 0.7
        else:
            m = 1
        if l < 11:
            a = 0
        else:
            a = math.floor(10 * math.sqrt(l - 11) + 50)
        t = math.ceil(((l * 5 + a) * r * d + 30) * m)
        return t

    def is_broken(self, broken_level=0):
        """broken level 0 : 擦伤, 1 : 中破,  2 : 大破"""
        conditions = False
        if broken_level == 0:
            conditions = self["battleProps"]["hp"] < self["battlePropsMax"]["hp"]
        elif broken_level == 1:
            conditions = self["battleProps"]["hp"] * 2 < self["battlePropsMax"]["hp"]
        elif broken_level == 2:
            conditions = self["battleProps"]["hp"] * 4 < self["battlePropsMax"]["hp"]
        elif 0 < broken_level < 1:
            conditions = self["battleProps"]["hp"] < self["battlePropsMax"]["hp"] * broken_level
        return conditions
    def should_be_repair(self, broken_level=0):
        """broken level 0 : 擦伤, 1 : 中破,  2 : 大破"""
        return self.status != 2 and self.is_broken(broken_level)


class ZjsnTask(dict):
    """docstring for ZjsnTask"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __getitem__(self, item):
        try:
            return super().__getitem__(int(item))
        except KeyError:
            raise KeyError("no such task with id {}".format(item))

    def update(self, E=None, **F):
        if "taskCid" in E:
            super().update({int(E['taskCid']): E}, **F)
        else:
            new_dict = {int(t['taskCid']): t for t in E}
            super().update(new_dict, **F)

    def remove(self, item):
        item = int(item)
        if item in self:
            del self[item]

    @property
    def finished_tasks(self):
        award_list = [task_cid for task_cid in self
                      if all([c["totalAmount"] == c["finishedAmount"]
                              for c in self[task_cid]["condition"]])]
        return award_list


class ZjsnEmulator(object):
    """docstring for ZjsnEmulator"""
    result_list = ['SSS',
                   'SS',
                   'S',
                   'A',
                   'B',
                   'C',
                   'D']
    KEY_VERSION = distutils.version.LooseVersion("3.1.0")
    ENCODE_USERNAME_VERSION = distutils.version.LooseVersion("3.3.0")

    def __init__(self):
        super(ZjsnEmulator, self).__init__()
        ZjsnShip.emulator = self
        self.s = requests.Session()
        self.userShip = ZjsnUserShip()
        self.task = ZjsnTask()

        self.repairDock = [{}]
        self.pveExplore = [{}]
        self.dock = [{}]
        self.equipmentDock = [{}]

        self.fleet = [{}]
        self.unlockShip = []

        self._default_headers = {'Accept-Encoding': 'identity',
                                 'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 5.1.1; GT-P5210 Build/LMY48Z)'}

        # with open("shipCard.json", encoding="utf8") as f:
        #     self.shipCard = json.load(f)

        self.initGame = ""

        self.username = "your username"
        self.password = "your password"

        # self.url_server = 'http://s2.jr.moefantasy.com'

        self.working_fleet = 2
        self.drop500 = False
        self.todaySpoilsNum = 0

        self.api = ZjsnApi(None)

        self.common_lag = 25  # 远征和修理收取的延迟秒数
        self.operation_lag = 0.5  # 每次操作的延迟秒数

        self.node = 0

        self.login_time = self.now

        self.ship_groups = [([], 1, False)] * 6
        # ship_groups item is (ship_group, broken_level, instant_flag)
        self.spoils = 0
        self.spoils_event = False

        self.boat_formula = [200, 30, 200, 30]
        self.equipment_formula = [20, 50, 10, 100]

        self.campaign_num = 0
        self.build_boat_remain = 0
        self.build_equipment_remain = 0

        self.last_request = None
        self.last_request_time = 0

        self.version = distutils.version.LooseVersion("3.1.0")
        self.max_level = 100

    @property
    def working_ships_id(self):
        return self.fleet[int(self.working_fleet) - 1]["ships"]

    @property
    def working_ships(self):
        return [self.userShip[i] for i in self.working_ships_id]

    def fleet_ships(self, fleet_id):
        return [self.userShip[i] for i in self.fleet_ships_id(fleet_id)]

    def fleet_ships_id(self, fleet_id):
        return self.fleet[int(fleet_id) - 1]["ships"]

    @property
    def fleeted_ships_id(self):
        return itertools.chain.from_iterable([i['ships'] for i in self.fleet])

    @property
    def explore_fleets(self):
        return [int(e['fleetId']) for e in self.pveExplore]

    @property
    def explore_ships_id(self):
        return [s.id for s in self.userShip if s.fleet_id in self.explore_fleets]

    def get(self, url, error_count=0, sleep_flag=True, method='GET', **kwargs):
        """kwargs: sleep=True"""
        if error_count:
            time.sleep(error_count ** 3)
        if error_count > 10:
            raise ConnectionError("lost connection")
        error_count += 1

        if 'headers' in kwargs:
            kwargs['headers'].update(self._default_headers)
        else:
            kwargs['headers'] = self._default_headers

        try:
            r = self.s.request(method, url, timeout=30, **kwargs)
            self.last_request = r
        except (
                requests.exceptions.ConnectionError, requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError):
            return self.get(url, error_count, sleep_flag, method, **kwargs)
        if sleep_flag:
            t = self.operation_lag - (time.time() - self.last_request_time)
            if t > 0:
                time.sleep(t)
            self.last_request_time = time.time()


        try:
            rj = r.json()
        except:
            return self.get(url, error_count, sleep_flag, method, **kwargs)

        if r.status_code != 200:
            return self.get(url, error_count, sleep_flag, method, **kwargs)
        elif "eid" in rj:
            eid = rj["eid"]
            if eid == -1:  # 操作太快
                zlogger.warning('操作太快, url: {}'.format(url))
                time.sleep(self.operation_lag * 2)
                return self.get(url, error_count, sleep_flag, method, **kwargs)
            elif eid == -9999:  # 维护啦
                zlogger.warning('服务器维护中')
                time.sleep(30 * 60)
                error_count -= 1
                return self.get(url, error_count, sleep_flag, method, **kwargs)
            else:
                raise ZjsnError(_INIT_DATA_.error_code[str(eid)], rj["eid"], self.last_request.url)
        else:
            if "updateTaskVo" in rj:
                for task in rj["updateTaskVo"]:
                    if int(task["taskCid"]) in self.task:
                        self.task[task["taskCid"]]["condition"] = task["condition"]

            if method == 'POST':
                return r
            else:
                return rj

    def login(self):
        r0 = self.get(self.api.checkVer())
        # get client version
        self.version = distutils.version.LooseVersion(r0["version"]["newVersionId"])
        # check data version
        if self.api.location == self.api.JAPAN:
            i_v = _INIT_DATA_.version_japan
        else:
            i_v = _INIT_DATA_.version
        if distutils.version.LooseVersion(r0["version"]['DataVersion']) > i_v:
            self.update_data()
        self.s = requests.Session()
        if self.version >= self.ENCODE_USERNAME_VERSION:
            username = base64.encodebytes(self.username.encode())
            password = base64.encodebytes(self.password.encode())
        else:
            username = self.username
            password = self.password
        r1 = self.get(self.api.passport(), method='POST',
                      sleep_flag=False,
                      data={"username": username,
                            "pwd": password})
        self.s.cookies = requests.utils.cookiejar_from_dict(dict(r1.cookies))
        self.s.cookies.update({'path': '/'})
        defaultServer = r1.json()['defaultServer']
        server_json = next(filter(lambda x: x['id'] == defaultServer, r1.json()['serverList']))
        self.url_server = server_json['host'][:-1]
        self.api.host = self.url_server
        # 亲测userID没有作用，决定登陆哪个账号的是cookie
        self.uid = r1.json()["userId"]
        self.get(self.api.login(self.uid), sleep_flag=False)
        self.initGame = self.get(self.api.init(), sleep_flag=False)
        self.get(self.url_server + "/pve/getPveData/", sleep_flag=False)
        event_data = self.get(self.url_server + "/pevent/getPveData/", sleep_flag=False)

        j = self.initGame
        self.userShip.clear()
        self.userShip.update(j["userShipVO"])
        self.userShip.shipNumTop = j['userVo']['detailInfo']['shipNumTop']
        self.spoils_event = bool(j["marketingData"]["isSpoilsShopEvent"])

        self.pveExplore = j["pveExploreVo"]["levels"]
        self.repairDock = j["repairDockVo"]
        self.dock = j['dockVo']
        self.equipmentDock = j['equipmentDockVo']

        self.fleet = j["fleetVo"]
        self.unlockShip = j["unlockShip"]
        cid_of_1 = 0
        for s in self.userShip:
            if s.id == 1:
                cid_of_1 = s.evoCid
                break
        self.unlockShip.append(cid_of_1)
        self.unlockEquipment = j['unlockEquipment']
        self.equipment = j['equipmentVo']
        self.task.update(j['taskVo'])

        self.spoils = int(self.get(self.url_server + '/shop/getSpoilsShopList')['spoils'])

        if j['marketingData']['continueLoginAward']['canGetDay'] != -1:
            r = self.get(self.api.loginAward())
            if 'shipVO' in r:
                self.userShip.add_ship(r['shipVO'], ze=self)
        self.login_time = self.now

        self.userShip.save('{}_{}.md'.format(self.username, server_json['name']))

        if self.version >= self.ENCODE_USERNAME_VERSION:
            self.max_level = 110
        zlogger.debug("login finished")
        return True

    def update_data(self):
        r_data = self.get(self.api.get_init())
        _INIT_DATA_.update(r_data, japan=self.api.location == self.api.JAPAN)
    def go_home(self):
        self.relogin()
        r_sl = self.get(self.url_server + "/active/getUserData/", sleep_flag=False)
        r_sl = self.get(self.url_server + "/pve/getUserData/", sleep_flag=False)
        self.get_campaign_data()
        self.bsea()
        self.get_award()

    def get_campaign_data(self):
        r_c = self.get(self.url_server + "/campaign/getUserData/", sleep_flag=False)
        self.campaign_num = int(r_c['passInfo']['remainNum'])

    @property
    def tz(self):
        if self.api.location == self.api.CHINA:
            timezone = datetime.timezone(datetime.timedelta(hours=8))
        elif self.api.location == self.api.JAPAN:
            timezone = datetime.timezone(datetime.timedelta(hours=9))
        else:
            timezone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
        return timezone

    @property
    def now(self):
        return datetime.datetime.now(self.tz)

    def relogin(self):
        if self.login_time < self.now.replace(hour=6, minute=0, second=0) < self.now:
            self.login()
            return True
        if self.login_time < self.now.replace(hour=0, minute=0, second=0) < self.now:
            self.login()
            self.drop500 = False
            return True
        return False

    def kiss(self):
        pass

    def bsea(self):
        r = self.get(self.api.bsea())
        self.todaySpoilsNum = int(r["bSeaData"]["todaySpoilsNum"])
        return r

    def build(self, dock_id, oil, ammo, steel, aluminum):

        r = self.get(self.api.buildBoat(dock_id, oil, ammo, steel, aluminum))
        self.dock = r['dockVo']
        return r

    def buildEquipment(self, dock_id, oil, ammo, steel, aluminum):
        r = self.get(self.api.buildEquipment(dock_id, oil, ammo, steel, aluminum))
        self.equipmentDock = r['equipmentDockVo']
        return r

    def get_award(self):
        for task_cid in self.task.finished_tasks:
            zlogger.debug("task: {} finish".format(self.task[task_cid]["title"]))
            r = self.get(self.api.getAward(task_cid))
            self.task.remove(task_cid)
            if 'taskVo' in r:
                self.task.update(r['taskVo'])
            if 'shipVO' in r:
                self.userShip.add_ship(r['shipVO'], ze=self)

    def change_ships(self):
        ship_groups = [i for i in self.ship_groups if i[0] != None]
        tmp_fleet_ships_id = []
        for i, g in enumerate(ship_groups):
            new_id = self.get_substitue(i, tmp_fleet_ships_id, g)
            if new_id:
                tmp_fleet_ships_id.append(new_id)
            else:
                return False

        if tmp_fleet_ships_id != self.working_ships_id:
            new_fleet = tmp_fleet_ships_id[:len(ship_groups)]
            self.instant_workingfleet(new_fleet)
        return True

    def get_substitue(self, location, tmp_fleet_ships_id, ship_group_info):
        working_ships = tmp_fleet_ships_id[:]
        ship_group, b_level, instant_flag = ship_group_info
        ship_group = ship_group[:]
        # if len(ship_group) > len(working_ships):
        #     working_ships += (len(ship_group) - len(working_ships)) * [0]
        # else:
        #     working_ships = working_ships[:len(ship_group)]
        new_ship_id = None

        if not ship_group:
            zlogger.info("no ship to use in location {}".format(location))
            return False
        # if len(self.working_ships_id) > location and self.working_ships_id[location] in ship_group:
        #     ship_group.insert(0, self.working_ships_id[location])
        for s_id in ship_group:
            s = self.userShip[s_id]
            conditions = (s.evoCid not in [self.userShip[si].evoCid for si in working_ships if si != 0],
                          s.locked,
                          s.fleet_able,  # 没在远征队伍里
                          s.status != 2,  # 没在修理
                          not s.should_be_repair(b_level),
                          )
            if all(conditions):
                new_ship_id = s_id
                break

        if instant_flag and not new_ship_id:
            for s_id in ship_group:
                s = self.userShip[s_id]
                conditions = (s.evoCid not in [self.userShip[si].evoCid for si in working_ships if si != 0],
                              s.locked,
                              s.fleet_able,  # 没在远征队伍里
                              s.is_broken(0),
                              )
                if all(conditions):
                    new_ship_id = s_id
                    self.repair(new_ship_id, 0, instant=True)
                    break
        if not new_ship_id:
            zlogger.debug("no ship to use in location {}".format(location))
        return new_ship_id

    def instant_workingfleet(self, ships_id):
        if ships_id:
            r = self.instant_fleet(self.working_fleet, ships_id)
            return r

    def instant_fleet(self, fleet_id, ships_id):
        fleet_id = int(fleet_id)
        if ships_id:
            for new_id in ships_id:
                current_fid = self.userShip[new_id].fleet_id
                if current_fid not in [fleet_id, 0]:
                    r1 = self.instant_fleet(current_fid, [s for s in self.fleet_ships_id(current_fid) if s != new_id])

            zlogger.debug('编队{}: {}'.format(fleet_id, [self.userShip[i].name for i in ships_id]))
            r = self.get(self.api.instantFleet(fleet_id, ships_id))
            if len(r["fleetVo"]) == 1:
                f = r["fleetVo"][0]
            else:
                f = r["fleetVo"][fleet_id - 1]
            self.fleet[fleet_id - 1] = f
            self.userShip.update(r['shipVO'])
            return r

    def dismantle(self, throw_equipment=0):
        ships_dismantle = []
        for ship in self.userShip:
            conditions = (not ship.protected(),
                          ship.type in ['驱逐',  # DD
                                        '轻巡',  # 轻巡
                                        '重巡',  # 重巡
                                        '轻母'])  # 轻母
            if all(conditions):
                ships_dismantle.append(ship["id"])
        if len(ships_dismantle) > 0:
            r = self.get(self.api.dismantleBoat(ships_dismantle, throw_equipment))
            del_ships = r['delShips']
            zlogger.debug('dismantle: {}'.format([self.userShip[s].name for s in del_ships]))
            if 'equipmentVo' in r:
                self.equipment = r['equipmentVo']
            for ship_id in del_ships:
                self.userShip.pop(ship_id, None)
        else:
            r = 0
        return r

    def auto_strengthen(self):
        # cid_table = [ship.cid for ship in self.userShip if ship.level > 1]
        u_ships = self.userShip.unique
        for ship in sorted(self.userShip, key=lambda x: (bool(x.evolved), int(x.level)), reverse=True):
            self.auto_skill(ship)
            conditions = (
                ship.locked == 1,
                not (ship.name in ['罗德尼', '纳尔逊', '大凤', '空想', '萤火虫'] and ship.level < ship.evoLevel + 10),
                (not ship.can_evo and ship in u_ships) or ship.evolved == 1 or ship.type in ['潜艇', '炮潜'],  # 不能改造或者已经改造
                ship.fleet_id not in self.explore_fleets,  # 不在远征舰队中
                any(ship.strength_exp),
            )
            if all(conditions):
                r = self.strengthen(ship)

    def strengthen(self, ship_in, target_attribute=None):
        # todo 让强化更智能，自动分辨狗粮价值
        ship_in = self.userShip[ship_in]
        if not target_attribute:
            target_attribute = [0, 1, 2, 3]
        ships_strengthen = []
        ship_types = []
        # 分别是火力，装甲，鱼雷，对空
        food_type = [['重巡', '战巡', '战列'],
                     ['驱逐'],
                     ['驱逐'],
                     ['轻巡']]
        if not any(ship_in.strength_exp):
            # if not self.auto_skill(ship_in):
            return -1  # 没必要强化
        for attribute_id, exp_remain in enumerate(ship_in.strength_exp):
            if attribute_id in target_attribute and exp_remain > 0:
                ship_types.extend(food_type[attribute_id])
        if not ship_types:
            return -1  # 没必要强化

        for ship in self.userShip:
            conditions = [not ship.protected(),
                          ship.type != '战列' or ship.star < 4,
                          ship.type in ship_types]
            if all(conditions):
                ships_strengthen.append(ship.id)
        if len(ships_strengthen) > 0:
            ships_strengthen = ships_strengthen[:2]  # 一次最多吃2艘船
            r = self.get(self.api.strengthen(ship_in.id, ships_strengthen))
            zlogger.debug("{} eats {}".format(ship_in.name, [self.userShip[s].name for s in ships_strengthen]))
            del_ships = r['delShips']
            for ship_id in del_ships:
                self.userShip.pop(ship_id, None)
            self.equipment = r['equipmentVo']
            self.userShip.update(r['shipVO'])


        else:
            r = 0  # 没船强化
        return r

    def auto_skill(self, ship):
        ship = self.userShip[ship]
        if 'skillId' in ship:
            if all([not any(ship.strength_exp),
                    ship.skillLevel != 3,
                    ship.type != '补给',
                    ship.skillType != 98,  # “球上倒立”技能无法升级
                    ]):
                zlogger.debug('{} skill level up to {}'.format(ship.name, ship.skillLevel + 1))
                r = self.get(self.api.skillLevelUp(ship.id))
                self.userShip.update(r['shipVO'])
                return r

    def cleanup_equipment(self):
        white_list = [10011821,
                      10002121,
                      10008321,
                      10008521]

        black_list = [10001021,
                      10001721,
                      10009021,
                      10001621,
                      10001821,
                      10005521,
                      10001921]

        for i in self.equipment:
            if i['num'] > 0:
                cid = int(i['equipmentCid'])
                if cid in _INIT_DATA_.equipment_card:
                    if (_INIT_DATA_.equipment_card[cid]['star'] < 3 and cid not in white_list) or cid in black_list:
                        d = ('content=' + str('{{"{}":{}}}')).format(cid, i['num']).encode()
                        r = self.get(self.api.dismantleEquipment(), method='POST',
                                     headers={'Content-Type': 'application/x-www-form-urlencoded'}, data=d)
                        self.equipment = r.json()['equipmentVo']
                else:
                    zlogger.warning("unknown equipment {}".format(cid))

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
        r = self.get(self.api.explore(fleet_id, explore_id))
        self.pveExplore = r["pveExploreVo"]["levels"]
        self.fleet = r["fleetVo"]

    def explore_result(self, explore_id):
        r = self.get(self.api.getExploreResult(explore_id))
        self.pveExplore = r["pveExploreVo"]["levels"]
        self.fleet = r["fleetVo"]
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

    def get_all_explore(self):
        for ex in self.pveExplore:
            if ex["endTime"] + self.common_lag < time.time():
                fleet_id = ex["fleetId"]
                explore_id = ex["exploreId"]
                self.explore_result(explore_id)

    def cancel_explore(self, fleet_id):
        for ex in self.pveExplore:
            fleetId = ex["fleetId"]
            explore_id = ex["exploreId"]
            if int(fleet_id) == int(fleetId):
                r = self.get(self.api.cancel_explore(explore_id))
                self.pveExplore = r["pveExploreVo"]["levels"]
                self.fleet = r["fleetVo"]
                return True

    def get_boat(self, dock_id):
        if len(self.userShip) < self.userShip.shipNumTop:
            r = self.get(self.api.getBoat(dock_id))
            self.dock = r['dockVo']
            if 'shipVO' in r:
                self.userShip.add_ship([r['shipVO']], ze=self, source='build')

    def get_equipment(self, dock_id):
        r = self.get(self.api.getEquipment(dock_id))
        self.equipmentDock = r['equipmentDockVo']
        # if r['equipmentCid'] in [i['equipmentCid']
        get_flag = False  # 是否增加了一个新装备
        equipment_name = _INIT_DATA_.equipment_card[int(r['equipmentCid'])]['title']
        # todo 判断是否解锁了一件新装备
        for i in self.equipment:
            if r['equipmentCid'] == i['equipmentCid']:
                i['num'] = r['equipmentVo']['num']
                zlogger.info('build equipment: {}'.format(equipment_name))
                get_flag = True
                break
        if not get_flag:
            self.equipment.append(r['equipmentVo'])
        zlogger.info('build equipment: {}'.format(equipment_name))

    def auto_build(self):
        for ex in filter(lambda d: 'endTime' in d, self.dock):
            if ex["endTime"] + self.common_lag < time.time():
                dock_id = ex["id"]
                self.get_boat(dock_id)
        for i in self.dock:
            if 'endTime' not in i and i['locked'] == 0 and self.build_boat_remain > 0:
                dock_id = i['id']
                self.build(dock_id, *self.boat_formula)
                self.build_boat_remain -= 1

    def auto_build_equipment(self):
        for ex in filter(lambda d: 'endTime' in d, self.equipmentDock):
            if ex["endTime"] + self.common_lag < time.time():
                dock_id = ex["id"]
                self.get_equipment(dock_id)
        for i in self.equipmentDock:
            if self.build_equipment_remain > 0 and 'endTime' not in i and i['locked'] == 0:
                dock_id = i['id']
                self.buildEquipment(dock_id, *self.equipment_formula)
                self.build_equipment_remain -= 1

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

    def repair_all(self, broken_level=0, instant=False, avoid_working_flag=False):
        """broken level 0 : 擦伤, 1 : 中破,  2 : 大破
        不会修理正在远征和修理的船"""
        if avoid_working_flag:
            avoid_ships_id = self.explore_ships_id + self.working_ships_id
        else:
            avoid_ships_id = self.explore_ships_id

        ships = [i.id for i in self.userShip.broken_ships(broken_level) if
                 i.status == 0 and i.id not in avoid_ships_id]
        # 先修时间最短的
        ships.sort(key=lambda x: self.userShip[x].repair_time, reverse=True)
        for dock_index, dock in enumerate(self.repairDock):
            if "endTime" in dock:
                if dock["endTime"] + self.common_lag < time.time():
                    self.repair_complete(dock["shipId"], dock_index)
            if "endTime" not in dock and dock["locked"] == 0 and len(ships) > 0:
                self.repair(ships.pop(), dock_index, instant)

    def repair_instant(self, broken_level=1):
        """对工作舰队用快修修理"""
        broken_ships = []
        for ship_id in self.working_ships_id:
            if self.userShip[ship_id].is_broken(broken_level):
                self.repair(ship_id, 0, instant=True)
                broken_ships.append(self.userShip[ship_id].name)
        return broken_ships

    def repair(self, ship_id, dock_id, instant=False):
        ship = self.userShip[ship_id]
        time.sleep(1)
        if not instant and ship.status == 0:
            r = self.get(self.api.repair(ship_id, dock_id + 1))
            zlogger.debug(
                    "repair {}".format(self.userShip[ship_id].name))
            self.repairDock = r["repairDockVo"]
            self.userShip.update(r["shipVO"])
        elif ship.status in [0, 2]:
            r = self.get(self.api.instantRepairShips([ship_id]))
            zlogger.debug(
                    "instant repair {}".format(self.userShip[ship_id].name))
            self.userShip.update(r["shipVOs"])
            if "repairDockVo" in r:
                self.repairDock = r["repairDockVo"]

    def repair_ships_instant(self, ships_id):
        if not ships_id:
            return True
        if not all([self.userShip[i].status in [0, 2] for i in ships_id]):
            return False
        broken_ships = self.userShip.select(ships_id)
        broken_ships_id = [s.id for s in broken_ships]
        broken_ships_name = [s.name for s in broken_ships]
        r = self.get(self.api.instantRepairShips(broken_ships_id))
        zlogger.debug("instant repair {}".format(broken_ships_name))
        self.userShip.update(r["shipVOs"])
        if "repairDockVo" in r:
            self.repairDock = r["repairDockVo"]
        return r

    def repair_complete(self, ship_id, dock_id):
        r = self.get(self.api.repairComplete(ship_id, dock_id + 1))
        self.repairDock = r["repairDockVo"]
        # I don't know why sometimes shipVO not in response
        if "shipVO" in r:
            self.userShip.update(r["shipVO"])

    def go_out(self, map_code, ignore500=False):
        # try:
        if self.drop500 and not ignore500:
            raise ZjsnError('500已满', eid=-215)
        if len(self.userShip) < self.userShip.shipNumTop:
            r = self.get(
                self.url_server + "/pve/cha11enge/{0}/{1}/0/".format(map_code, self.working_fleet))
        else:
            raise ZjsnError('船坞已满', eid=-215)
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
        # if self.fleet[int(self.working_fleet) - 1]["ships"][0] in self.userShip.broken_ships(2):
        #     raise KeyError("flagship big broken")
        r = self.get(self.url_server + "/pve/newNext/")
        self.node = r["node"]
        return self.node

    def spy(self):
        r = self.get(self.url_server + "/pve/spy/")
        return r

    def dealto(self, formation_code, big_broken_protect=True):
        if [i for i in self.userShip.broken_ships_id(2) if
            i in self.working_ships_id] and big_broken_protect:
            raise ZjsnError("big broken")
        """阵型编号 1 单纵 2 复纵 3 轮型 4 梯形 5 单横"""
        node = self.node
        r = self.get(
            self.url_server + "/pve/dealto/{0}/{1}/{2}".format(node, self.working_fleet, formation_code))
        return r

    def deal(self, formation_code, big_broken_protect=True):
        if [i for i in self.userShip.broken_ships_id(2) if
            i in self.working_ships_id] and big_broken_protect:
            raise ZjsnError("big broken")
        """阵型编号 1 单纵 2 复纵 3 轮型 4 梯形 5 单横"""
        node = self.node
        r = self.get(
            self.url_server + "/pve/deal/{0}/{1}/{2}".format(node, self.working_fleet, formation_code))
        return r

    def lock(self, ship_id):
        r = self.get(self.api.lock(ship_id))
        # TODO figure out why "locked" info no updated
        self.userShip.update(r['shipVO'])
        return r

    def getWarResult(self, night_flag=0):
        """0 不夜战, 1 夜战"""
        r = self.get(self.url_server + "/pve/getWarResult/" + str(night_flag))
        result_level = r["warResult"]["resultLevel"]

        if len(r["shipVO"]) > len(self.working_ships_id):
            for s_d in r["shipVO"]:
                if int(s_d['id']) not in self.userShip:
                    self.userShip.add_ship([s_d], ze=self,
                                           source='result {}, get'.format(self.result_list[int(result_level)]))
        self.userShip.update(r["shipVO"])
        if "drop500" in r:
            self.drop500 = True
            zlogger.warning('今日500船已满')
        if "newShipVO" in r:
            self.userShip.add_ship(r["newShipVO"], ze=self,
                                   source='result {}, get'.format(self.result_list[int(result_level)]))
        if 'spoils' in r:
            self.spoils = r['spoils']
        return r

    def supply_workingfleet(self):
        r = self.supplyFleet(self.working_fleet)
        return r

    def supplyFleet(self, fleet_id):
        if any([s["battlePropsMax"]["oil"] - s["battleProps"]["oil"] for s in self.fleet_ships(fleet_id)]):
            r = self.get(self.url_server + "/boat/supplyFleet/{}/".format(fleet_id))
            self.userShip.update(r['shipVO'])
            return r

    def supply_boats(self, ships_id):
        ships = [self.userShip[i] for i in ships_id]
        if any([s["battlePropsMax"]["oil"] - s["battleProps"]["oil"] for s in ships]):
            r = self.get(self.api.supplyBoats(ships_id))
            self.userShip.update(r['shipVO'])

    def skip(self):
        r = self.get(self.api.skip())
        return r['isSuccess']

    def war_report(self):
        pass

    def unlocked_report(self):
        base_ships = [_INIT_DATA_.ship_card[s_id]['title'] for s_id in
                      (set(_INIT_DATA_.ship_card) - set(self.unlockShip))
                      if s_id < 11000000]
        evo_ships = [_INIT_DATA_.ship_card[s_id]['title'] for s_id in
                     (set(_INIT_DATA_.ship_card) - set(self.unlockShip))
                     if 11000000 < s_id < 18000000]
        zlogger.info("unlocked base ships:\n{}".format('\n'.join(base_ships)))
        zlogger.info("unlocked evo ships:\n{}".format('\n'.join(evo_ships)))

    def rename_ship(self, ship_id, new_name):
        r = self.get(self.api.rename(ship_id, new_name))
        if 'shipVO' in r:
            self.userShip.update(r['shipVO'])
        return r

# if __name__ == '__main__':
#     e = ZjsnEmulator()
#     # e.username = 'paleneutron1'
#     # e.url_server = 'http://s13.jr.moefantasy.com'
#     e.login()
#     for ship in e.userShip:
#         print(ship.name, ship.level, ship.id, ship.cid, ship.type, ship.locked, ship.strength_exp)
#     # e.auto_strengthen()
#     # e.cleanup_equipment()
#     e.build(500, 130, 600, 400)
