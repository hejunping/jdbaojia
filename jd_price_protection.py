#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
JD login
"""
import cv2
import time
import numpy as np
from selenium import webdriver
from urllib import request
from selenium.webdriver.common.action_chains import ActionChains
import random
import json
import requests
import re
import easing
import os
import logging


class JdPriceProtection(object):
    root = os.path.abspath(os.path.dirname(__file__))
    brower = None
    path = "{}/images/jd".format(root)
    cookies = "{}/cookies".format(root)
    headers = {"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36"}
    area = None # 所在区域地址ID
    product_info = None
    pin = None
    isAllApply = True
    lg = None
    username = None

    def __init__(self, user, pwd, area):
        self.username = user
        self.set_log()
        self.login(user, pwd)
        self.area = area

    def set_log(self):
        self.lg = logging.getLogger(__name__)
        self.lg.setLevel(level=logging.INFO)
        fh = logging.FileHandler("{}/log/jd.log".format(self.root))
        fh.setLevel(level=logging.INFO)
        fh.setFormatter(logging.Formatter('%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'))
        self.lg.addHandler(fh)

    def init_chrome(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--start-maximized")
        # 谷歌文档提到需要加上这个属性来规避bug
        chrome_options.add_argument('--disable-gpu')
        # 设置屏幕器宽高
        chrome_options.add_argument("--window-size=1440,750")
        self.brower = webdriver.Chrome(chrome_options=chrome_options)

    def loadpage(self, user, passwd):
        """加载登录页面"""
        url = "https://passport.jd.com/new/login.aspx?"
        self.brower.get(url)
        time.sleep(3)
        click_bnt = r'//div/div[@class="login-tab login-tab-r"]/a'
        user_login_form = self.brower.find_element_by_xpath(click_bnt)
        user_login_form.click()
        # 输入用户
        username = self.brower.find_element_by_id("loginname")
        username.send_keys(user)
        # 输入密码
        userpswd = self.brower.find_element_by_id("nloginpwd")
        userpswd.send_keys(passwd)
        self.brower.find_element_by_id("loginsubmit").click()
        time.sleep(3)
        self.drag_check()
        while True:
            try:
                self.drag_check()
            except Exception as e:
                self.lg.info(e)
                self.lg.info("登录成功")
                self.save_cookies()
                self.brower.quit()
                break
        time.sleep(5)

    def get_img_gap(self):
        """获取滑动图片的间距"""
        # 用于找到登录图片的大图
        bigimg_div = r'//div/div[@class="JDJRV-bigimg"]/img'
        # 用来找到登录图片的小滑块
        smalling_div = r'//div/div[@class="JDJRV-smallimg"]/img'
        bigimg = self.brower.find_element_by_xpath(bigimg_div).get_attribute("src")
        smallimg = self.brower.find_element_by_xpath(smalling_div).get_attribute("src")
        # 背景大图命名
        backimg = "%s/backimg.png" % self.path
        # 滑块命名
        slideimg = "%s/slideimg.png" % self.path
        # 下载背景大图保存到本地
        request.urlretrieve(bigimg, backimg)
        # 下载滑块保存到本地
        request.urlretrieve(smallimg, slideimg)
        # 获取图片并灰度化
        block = cv2.imread(slideimg, 0)
        template = cv2.imread(backimg, 0)
        # 二值化后的图片名称
        blockName = "%s/block.jpg" % self.path
        templateName = "%s/template.jpg" % self.path
        # 将二值化后的图片进行保存
        cv2.imwrite(blockName, block)
        cv2.imwrite(templateName, template)
        block = cv2.imread(blockName)
        block = cv2.cvtColor(block, cv2.COLOR_RGB2GRAY)
        block = abs(255 - block)
        cv2.imwrite(blockName, block)
        block = cv2.imread(blockName)
        template = cv2.imread(templateName)
        # 获取偏移量
        result = cv2.matchTemplate(block, template, cv2.TM_CCOEFF_NORMED)  # 查找block在template中的位置，返回result是一个矩阵，是每个点的匹配结果
        x, y = np.unravel_index(result.argmax(), result.shape)
        self.lg.info("x:", y)
        return int(y*0.77)

    def get_track(self, distance):
        '''
        拿到移动轨迹，模仿人的滑动行为，先匀加速后匀减速
        匀变速运动基本公式：
        ①v=v0+at
        ②s=v0t+(1/2)at²
        ③v²-v0²=2as

        :param distance: 需要移动的距离
        :return: 存放每0.2秒移动的距离
        '''
        # 初速度
        v = 0
        # 单位时间为0.2s来统计轨迹，轨迹即0.2内的位移
        t = 0.5
        # 位移/轨迹列表，列表内的一个元素代表0.2s的位移
        tracks = []
        # 当前的位移
        current = 0
        # 到达mid值开始减速
        mid = distance * 7 / 8

        distance += 10  # 先滑过一点，最后再反着滑动回来
        # a = random.randint(1,3)
        while current < distance:
            if current < mid:
                # 加速度越小，单位时间的位移越小,模拟的轨迹就越多越详细
                a = random.randint(2, 4)  # 加速运动
            else:
                a = -random.randint(3, 5)  # 减速运动
            # 初速度
            v0 = v
            # 0.2秒时间内的位移
            s = v0 * t + 0.5 * a * (t ** 2)
            # 当前的位置
            current += s
            # 添加到轨迹列表
            tracks.append(round(s))

            # 速度已经达到v,该速度作为下次的初速度
            v = v0 + a * t

        # 反着滑动到大概准确位置
        for i in range(4):
            tracks.append(-random.randint(2, 3))
        for i in range(4):
            tracks.append(-random.randint(1, 3))
        return tracks

    def drag_check(self):
        """
        拖动模块
        如果发布拖动不流畅，请修改
        修改 selenium 源码 /selenium/webdriver/common/actions/pointer_input.py 文件中的 DEFAULT_MOVE_DURATION = 250 的值，到50左右，
        :return:
        """
        title = self.brower.title
        if title == '认证魔方':
            self.lg.info("{}，等待60秒".format(title))
            time.sleep(60)
        gap = self.get_img_gap()
        self.lg.info("gap:%s" % gap)
        drag_div = r'//div/div[@class="JDJRV-smallimg"]/img'
        element = self.brower.find_element_by_xpath(drag_div)
        action_chains = ActionChains(self.brower)
        action_chains.click_and_hold(on_element=element)
        action_chains.pause(0.2)
        offsets, tracks = easing.get_tracks(gap, 4, 'ease_out_expo')
        # tracks = self.get_track(gap)
        self.lg.info("tracks:", len(tracks), tracks)
        for track in tracks:
            action_chains.move_by_offset(track, 0)
        action_chains.pause(random.uniform(0.5, 0.9))
        action_chains.release()
        action_chains.perform()
        time.sleep(random.randint(3, 9))

    def save_cookies(self):
        cookies = self.brower.get_cookies()
        cookies_dict = {}
        for item in cookies:
            cookies_dict[item['name']] = item['value']
        with open("{}/{}_cookies.txt".format(self.cookies,self.username), 'w') as f:
            f.write(json.dumps(cookies_dict))
        self.lg.info("save cookies ok")

    def check_login(self):
        """检查是否登录"""
        url = "https://pcsitepp-fm.jd.com//rest/pricepro/priceskusPull"
        data = {"page": 1, "pageSize": 10}
        requests.post(url, data=data, cookies=None)

    def get_cookies(self):
        """获取Cookies"""
        cookies = {}
        path = "{}/{}_cookies.txt".format(self.cookies,self.username)
        if os.path.exists(path):
            with open(path, 'r') as f:
                cookies = requests.utils.cookiejar_from_dict(json.loads(f.read()))
        return cookies

    def get_login_pin(self):
        """获取login pin"""
        url = "https://pcsitepp-fm.jd.com/rest/pricepro/priceapply"
        r = requests.get(url, cookies=self.get_cookies())
        loginPin = re.findall('<input type="hidden" id="loginPin" value="(\w+)" />', r.text)
        self.pin = loginPin[0] if len(loginPin) > 0 else None
        return self.pin

    def is_apply(self, orderId, skuId, pin):
        """是否能申请"""
        url = "https://sitepp-fm.jd.com/rest/webserver/skuProResultPC"
        data = {
            "orderId":orderId,
            "skuId":skuId,
            "pin": pin
        }
        headers = self.headers
        headers['referer'] = 'https://pcsitepp-fm.jd.com/rest/pricepro/priceapply'
        r = requests.post(url, data=data, cookies=self.get_cookies(), headers=headers)
        return True if 'overTime' not in r.text else False

    def get_apply_list(self, page_num=1):
        """获取保价列表"""
        bill_info = []
        url = "https://pcsitepp-fm.jd.com//rest/pricepro/priceskusPull"
        data = {"page": page_num, "pageSize": 10}
        cookies = self.get_cookies()
        r = requests.post(url, data=data, cookies=cookies)
        bill = r.text.split('<tr class="sep-row"><td colspan="6"></td></tr>')
        bill.pop(0)
        for item in bill:
            tmp = {}
            orderid = re.findall("订单号：(\d+)", item)
            product_name = re.findall("<a .*?>(.*?)</a>", item)
            product_id = re.findall("<a href=\"//item.jd.com/(\d+).html\" .*?>.*?</a>", item)
            skuidAndSequences = re.findall("queryOrderSkuPriceParam\.skuidAndSequence\.push\(\"(\d+\,\d+)\"\)\;", item)
            newSkuidAndSequences = []
            for ss in skuidAndSequences:
                is_apply = self.is_apply(orderid[0], ss.split(',')[0], self.pin)
                if is_apply:
                    newSkuidAndSequences.append(ss)
            if newSkuidAndSequences:
                tmp['orderid'] = orderid[0]
                tmp['skuidAndSequence'] = newSkuidAndSequences
                bill_info.append(tmp)
        if bill:
            """递归获取所可申请的商品信息"""
            bill_info.extend(self.get_apply_list(page_num+1))
        return bill_info

    def get_price_list(self):
        """设置login pin"""
        self.get_login_pin()
        self.lg.info("获取保价列表")
        url = "https://sitepp-fm.jd.com/rest/webserver/getOrderListSkuPrice"
        queryOrderPriceParam = self.get_apply_list()
        payload_tuples = {"queryOrderPriceParam": json.dumps(queryOrderPriceParam)}
        # print(payload_tuples)
        r = requests.post(url, data=payload_tuples)
        blists = r.json()
        self.lg.info("获取到 {} 件可申请的商品".format(len(blists)))
        for item in blists:
            skuid = item.get("skuid")
            buyingjdprice = item.get("buyingjdprice")
            orderid = item.get("orderid")
            if self.isAllApply:
                self.lg.info("全部申请:订单ID:{}-商品ID{}".format(orderid, skuid))
                self.protect_protect_apply(orderid, skuid)
            else:
                self.lg.info("比价申请")
                self.product_info = self.get_product_info(skuid)
                cprice = self.get_protect_current_price(self.product_info)
                gap = self.get_product_prom(self.product_info, buyingjdprice)
                self.lg.info("当前价格：{},购买价格：{}, 满减价格：{}".format(cprice, buyingjdprice, gap))
                if buyingjdprice > cprice - gap and buyingjdprice > gap:
                    """申请"""
                    self.lg.info("申请金额：{}".format(buyingjdprice - (cprice -gap)))
                    self.protect_protect_apply(orderid, skuid)
        self.lg.info("well done!!")

    def protect_protect_apply(self, orderId, skuId):
        """申请价格保护"""
        url = 'https://pcsitepp-fm.jd.com//rest/pricepro/skuProtectApply'
        data = {
            "orderId": orderId,
            "orderCategory": "Others",
            "skuId": skuId,
            "refundtype": 1
        }
        headers = self.headers
        headers['accept'] = "application/json, text/javascript, */*; q=0.01"
        r = requests.post(url, data=data, cookies=self.get_cookies(), headers=headers)
        self.lg.info("申请提交{}".format(r.text))
        return

    def get_protect_current_price(self, product_info):
        """获取当前商品的价格"""
        url = "https://c0.3.cn/stock"
        data = {
            "skuId": product_info['skuId'],
            "area": product_info['area'],
            "venderId": product_info.get('venderId', ''),
            "cat": product_info.get('cat', ''),
        }
        r = requests.get(url, data, headers=self.headers)
        jdata = r.json()
        jdPriceDic = jdata.get("stock", {}).get("jdPrice", {})
        jdPrice = jdPriceDic.get('tpp', 0) if jdPriceDic.get('tpp') else jdPriceDic.get('p', 0)
        return float(jdPrice)

    def get_product_info(self, skuId):
        """获取购买的产品列表信息"""
        info = {}
        url = "http://item.jd.com/%s.html" % skuId
        r = requests.get(url, headers=self.headers)
        pageconfig = re.findall("var pageConfig = \{([\\s\\S]+)\} catch\(e\) \{\}", r.text)
        cat = re.findall("cat: \[([\\d,]+)\]", pageconfig[0])
        venderId = re.findall("venderId:(\d+)", pageconfig[0])
        shopId = re.findall("shopId:'(\d+)'", pageconfig[0])
        info['cat'] = cat[0] if len(cat) else ""
        info['venderId'] = venderId[0] if len(venderId) else ""
        info['shopId'] = shopId[0] if len(shopId) else ""
        info['skuId'] = skuId
        info['area'] = self.area
        self.product_info = info
        return info

    def get_product_prom(self, projdct_info, buyingjdprice):
        """促销，满减"""
        gap = 0
        url = 'https://cd.jd.com/promotion/v2?skuId={}&area={}&shopId={}&cat={}'.format(projdct_info['skuId'], projdct_info['area'], projdct_info['shopId'], projdct_info['cat'])
        r = requests.get(url, headers=self.headers)
        pj = r.json()
        pickOneTag = pj.get("prom").get("pickOneTag")
        if pickOneTag:
            for tag in pickOneTag:
                if tag.get("name") == "满减":
                    mj_item = re.findall("\d+", tag.get('content'))
                    max = float(mj_item[0])
                    mj_item_gap = float(mj_item[1])
                    if buyingjdprice > max and mj_item_gap > gap:
                        gap = mj_item_gap
        return gap

    def check_login(self):
        is_login = False
        """校验用户是否登录"""
        url = 'https://home.jd.com/2014/data/user/isUserRealNameAuth.action'
        r = requests.get(url, cookies=self.get_cookies())
        if r.text == '1':
            self.lg.info("用户已经登录")
            is_login = True
        return is_login

    def login(self, user, pwd):
        """用户登录"""
        if not self.check_login():
            self.init_chrome()
            self.loadpage(user, pwd)


if __name__ == '__main__':
    jd = JdPriceProtection("xxxx", "xxxxx", "x_xxxx_xxxxx_x")
    jd.get_price_list()