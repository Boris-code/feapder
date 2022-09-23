# -*- coding: utf-8 -*-
"""
Created on 2022/9/15 8:47 PM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

from playwright.sync_api import Response

import feapder


def on_response(response: Response):
    print(response.url)


class TestPlaywright(feapder.AirSpider):
    __custom_setting__ = dict(
        RENDER_DOWNLOADER="feapder.network.downloader.PlaywrightDownloader",
        WEBDRIVER=dict(
            page_on_event_callback=dict(response=on_response),  # 监听response事件
            storage_state_path="playwright_state.json",  # 保存登录状态
        ),
    )

    def start_requests(self):
        yield feapder.Request("https://www.baidu.com", render=True)

    def download_midware(self, request):
        request.cookies = {"hhhhh": "66666"}
        # request.cookies = [
        #     {
        #         "domain": ".baidu.com",
        #         "expirationDate": 1663923578.800305,
        #         "hostOnly": False,
        #         "httpOnly": True,
        #         "name": "ab_sr",
        #         "path": "/",
        #         "secure": True,
        #         "session": False,
        #         "storeId": "0",
        #         "value": "1.0.1_MTIyODdmYzQzYTg2NzY0MGYwYWUwOTA5ODJkNTFlZDUxOTg1MzkyNzViYTc3NmFiZTk3MmU2ZTI0MDdkZTM4YzdlODQ5N2Q2ZDQzMGI0N2Y1NGE2Y2E3NjBlZWU4ZTA2MzQ3MGU5M2ZlM2M5MTBmNDVlMzU2NDBiMzZlOWNjN2IwZWZkZGRmOGIwOTUxMGYzMjQ4NDQyZGJjYTViOWI3Mg==",
        #         "id": 1,
        #     },
        #     {
        #         "domain": ".baidu.com",
        #         "expirationDate": 1664009672,
        #         "hostOnly": False,
        #         "httpOnly": False,
        #         "name": "BA_HECTOR",
        #         "path": "/",
        #         "secure": False,
        #         "session": False,
        #         "storeId": "0",
        #         "value": "ak2g8k0h8g8l8h25ah0kljp71hiqt2819",
        #         "id": 2,
        #     },
        #     {
        #         "domain": ".baidu.com",
        #         "expirationDate": 1682511471.350234,
        #         "hostOnly": False,
        #         "httpOnly": False,
        #         "name": "BAIDUID",
        #         "path": "/",
        #         "secure": False,
        #         "session": False,
        #         "storeId": "0",
        #         "value": "1922A166433AFD91AACA9A2591DDA842:FG=1",
        #         "id": 3,
        #     },
        #     {
        #         "domain": ".baidu.com",
        #         "expirationDate": 1695459279.623494,
        #         "hostOnly": False,
        #         "httpOnly": False,
        #         "name": "BAIDUID_BFESS",
        #         "path": "/",
        #         "secure": True,
        #         "session": False,
        #         "storeId": "0",
        #         "value": "1922A166433AFD91AACA9A2591DDA842:FG=1",
        #         "id": 4,
        #     },
        #     {
        #         "domain": ".baidu.com",
        #         "expirationDate": 2661324632,
        #         "hostOnly": False,
        #         "httpOnly": False,
        #         "name": "BIDUPSID",
        #         "path": "/",
        #         "secure": False,
        #         "session": False,
        #         "storeId": "0",
        #         "value": "451C45AEDA6E3B41F0F5F906A4D61A12",
        #         "id": 5,
        #     },
        #     {
        #         "domain": ".baidu.com",
        #         "hostOnly": False,
        #         "httpOnly": False,
        #         "name": "delPer",
        #         "path": "/",
        #         "secure": False,
        #         "session": True,
        #         "storeId": "0",
        #         "value": "0",
        #         "id": 6,
        #     },
        #     {
        #         "domain": ".baidu.com",
        #         "hostOnly": False,
        #         "httpOnly": False,
        #         "name": "H_PS_PSSID",
        #         "path": "/",
        #         "secure": False,
        #         "session": True,
        #         "storeId": "0",
        #         "value": "36543_36460_37357_36885_37273_36569_36786_37259_26350_37384_37351",
        #         "id": 7,
        #     },
        #     {
        #         "domain": ".baidu.com",
        #         "expirationDate": 1689768463.32528,
        #         "hostOnly": False,
        #         "httpOnly": False,
        #         "name": "H_WISE_SIDS",
        #         "path": "/",
        #         "secure": False,
        #         "session": False,
        #         "storeId": "0",
        #         "value": "107320_110085_179346_180636_194519_196428_197471_197711_199569_204901_206125_208721_209204_209568_210304_210323_210969_212296_212739_213042_213355_214115_214130_214137_214143_214793_215730_216207_216448_216518_216616_216741_216848_216883_217090_217168_217185_217439_217915_218327_218359_218445_218454_218481_218538_218548_218598_218637_218800_218833_219254_219363_219414_219448_219449_219509_219548_219625_219666_219712_219732_219733_219738_219742_219815_219819_219839_219854_219864_219943_219946_219947_220071_220190_220301_220662_220775_220800_220853_220998_221007_221086_221107_221116_221119_221121_221278_221371_221381_221457_221502",
        #         "id": 8,
        #     },
        #     {
        #         "domain": ".baidu.com",
        #         "expirationDate": 1695353323.712556,
        #         "hostOnly": False,
        #         "httpOnly": False,
        #         "name": "MCITY",
        #         "path": "/",
        #         "secure": False,
        #         "session": False,
        #         "storeId": "0",
        #         "value": "-%3A",
        #         "id": 9,
        #     },
        #     {
        #         "domain": ".baidu.com",
        #         "hostOnly": False,
        #         "httpOnly": False,
        #         "name": "PSINO",
        #         "path": "/",
        #         "secure": False,
        #         "session": True,
        #         "storeId": "0",
        #         "value": "5",
        #         "id": 10,
        #     },
        #     {
        #         "domain": ".baidu.com",
        #         "expirationDate": 3799549293.733737,
        #         "hostOnly": False,
        #         "httpOnly": False,
        #         "name": "PSTM",
        #         "path": "/",
        #         "secure": False,
        #         "session": False,
        #         "storeId": "0",
        #         "value": "1652065648",
        #         "id": 11,
        #     },
        #     {
        #         "domain": ".baidu.com",
        #         "expirationDate": 1695367975.75261,
        #         "hostOnly": False,
        #         "httpOnly": False,
        #         "name": "ZFY",
        #         "path": "/",
        #         "secure": True,
        #         "session": False,
        #         "storeId": "0",
        #         "value": "X58MLRUa4SBUYQuGvOlCmzOuPsS0tcc0HBo6K5QWhBs:C",
        #         "id": 12,
        #     },
        #     {
        #         "domain": ".www.baidu.com",
        #         "expirationDate": 1695367986,
        #         "hostOnly": False,
        #         "httpOnly": False,
        #         "name": "baikeVisitId",
        #         "path": "/",
        #         "secure": False,
        #         "session": False,
        #         "storeId": "0",
        #         "value": "dbd65753-d077-4a08-9464-ab1bedaf4793",
        #         "id": 13,
        #     },
        #     {
        #         "domain": "www.baidu.com",
        #         "hostOnly": True,
        #         "httpOnly": False,
        #         "name": "BD_CK_SAM",
        #         "path": "/",
        #         "secure": False,
        #         "session": True,
        #         "storeId": "0",
        #         "value": "1",
        #         "id": 14,
        #     },
        #     {
        #         "domain": "www.baidu.com",
        #         "hostOnly": True,
        #         "httpOnly": False,
        #         "name": "BD_HOME",
        #         "path": "/",
        #         "secure": False,
        #         "session": True,
        #         "storeId": "0",
        #         "value": "1",
        #         "id": 15,
        #     },
        #     {
        #         "domain": "www.baidu.com",
        #         "expirationDate": 1664787279,
        #         "hostOnly": True,
        #         "httpOnly": False,
        #         "name": "BD_UPN",
        #         "path": "/",
        #         "secure": False,
        #         "session": False,
        #         "storeId": "0",
        #         "value": "123253",
        #         "id": 16,
        #     },
        # ]
        return request

    def parse(self, reqeust, response):
        print(response.text)
        response.browser.save_storage_stage()


if __name__ == "__main__":
    TestPlaywright(thread_count=1).run()
