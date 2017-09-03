#/usr/bin/env python3.6

import re
import selenium.common.exceptions
from pyvirtualdisplay import Display
from bs4 import BeautifulSoup
from splinter import Browser
from time import sleep
from .exceptions import *
from .logger import logger
from .color import *
from .data import *


class API(object):
    '''Interface object'''

    def __init__(self, level):
        self.movements = []
        self.stocks = []
        self.logger = logger(level)
        self.vbro = Display()

    def _css(self, css_path):
        '''css find function abbreviation'''
        return self.browser.find_by_css(css_path)

    def _name(self, name):
        '''name find function abbreviation'''
        return self.browser.find_by_name(name)

    def _elCss(self, css_path):
        '''check if element is present by css'''
        return self.browser.is_element_present_by_css(css_path)

    def _num(self, string):
        '''convert a string to float (float gave me problems)'''
        return re.findall(r"[-+]?\d*\.\d+|\d+", string)[0]

    def launch(self, brow="firefox"):
        self.vbro.start()
        self.logger.debug("virtual display launched")
        self.browser = Browser(brow)
        self.logger.debug("browser {brow} launched".format(brow=brow))

    def login(self, username, password, mode="demo"):
        '''Login function'''
        url = "https://trading212.com/it/login"
        self.logger.debug("visiting {url}".format(url=url))
        try:
            self.browser.visit(url)
        except selenium.common.exceptions.WebDriverException:
            self.logger.critical("connection timed out")
        # self._css(path['login-btn']).click() obsolete
        self._name("login[username]").fill(username)
        self._name("login[password]").fill(password)
        self._css(path['log']).click()
        timeout = 30
        while not self._elCss(path['logo']):
            timeout -= 1
            if timeout == 0:
                self.logger.critical("login failed")
            sleep(1)
        self.logger.debug("logged in")
        if mode == "demo" and self._elCss(path['alert-box']):
            self._css(path['alert-box']).click()

    def logout(self):
        '''logout func (to quit browser)'''
        try:
            self.browser.quit()
        except:
            raise BrowserException("browser not started")
        self.vbro.stop()
        self.logger.debug("Logged out")

    def addMov(self, product, quantity=None, mode="buy", stop_limit=None):
        '''Add movement function'''
        self._css(path['add-mov'])[0].click()
        self._css(path['search-box'])[0].fill(product)
        if not self._elCss(path['first-res']):
            self.logger.error("{product} not found".format(
                product=underline(product)))
            self._css('span.orderdialog-close')[0].click()
            return 0
        self._css(path['first-res'])[0].click()
        self._css(path[mode + '-btn'])[0].click()
        if quantity is not None:
            self._css(path['quantity'])[0].fill(str(quantity))
        if stop_limit is not None:
            self._css(path['limit-gain-' + stop_limit['gain'][0]]
                      )[0].fill(str(stop_limit['gain'][1]))
            self._css(path['limit-loss-' + stop_limit['loss'][0]]
                      )[0].fill(str(stop_limit['loss'][1]))
        self._css(path['confirm-btn'])[0].click()
        self.logger.info("Added movement of {quant} {product} with limit \
            {limit}".format(quant=bold(quantity), product=bold(product),
                            limit=bold(stop_limit)))
        sleep(1)

    def closeMov(self, mov_id):
        '''close a position'''
        self._css("#" + mov_id + " div.close-icon")[0].click()
        self.browser.find_by_text("OK")[0].click()
        sleep(1.5)
        if self._elCss("#" + mov_id + " div.close-icon"):
            self.logger.error("failed to close mov {id}".format(id=mov_id))
            return 0
        else:
            self.logger.info("closed mov {id}".format(id=bold(mov_id)))
            return 1

    def checkPos(self):
        '''check all current positions'''
        soup = BeautifulSoup(
            self._css("tbody.dataTable-show-currentprice-arrows").html,
            "html.parser")
        movs = []
        count = 0
        for x in soup.find_all("tr"):
            prod_id = x['id']
            product = x.select("td.name")[0].text
            quant = x.select("td.quantity")[0].text
            if "direction-label-buy" in soup.find_all("tr")[0].select("td.direction")[0].span['class']:
                mode = "long"
            else:
                mode = "short"
            price = self._num(x.select("td.averagePrice")[0].text)
            earn = self._num(x.select("td.ppl")[0].text)
            mov = Movement(prod_id, product, quant, mode, price, earn)
            movs.append(mov)
            count += 1
        self.logger.debug(
            "{count} positions updated".format(count=bold(count)))
        self.movements = movs

    def checkStocks(self, stocks):
        '''check specified stocks (list)'''
        soup = BeautifulSoup(
            self._css("div.scrollable-area-content").html, "html.parser")
        count = 0
        for product in soup.select("div.tradebox"):
            name = product.select("span.instrument-name")[0].text.lower()
            if [x for x in stocks if name.find(x) != -1]:  # to tidy up
                if not [x for x in self.stocks if x.name == name]:
                    self.stocks.append(Stock(name))
                stock = [x for x in self.stocks if x.name == name][0]
                sell_price = product.select("div.tradebox-price-sell")[0].text
                raw_sent = product.select(
                    "span.tradebox-buyers-container.number-box")[0].text
                try:
                    sent = (int(raw_sent.strip('%')) / 100)
                except:
                    sent = None
                stock.addVar([sell_price, sent])
                count += 1
        self.logger.debug("added {count} stocks".format(count=bold(count)))

    def addPrefs(self, prefs):
        '''add prefered stocks'''
        for pref in prefs:
            self._css(path['search-btn'])[0].click()
            self._css(path['all-tools'])[0].click()
            self._css(path['search-pref'])[0].fill(pref)
            if self._elCss(path['plus-icon']):
                self._css(path['add-btn'])[0].click()
        self._css(path['close-prefs'])[0].click()
        self._css("span.prefs-icon-node")[0].click()
        self._css(
            "div.item-tradebox-prefs-menu-list-sentiment_mode")[0].click()
        self._css("span.prefs-icon-node")[0].click()
        self.logger.debug("added {prefs} to preferencies".format(
            prefs=', '.join([bold(x) for x in prefs])))

    def clearPrefs(self):
        '''clear all stock preferencies'''
        self._css(path['search-btn'])[0].click()
        self._css(path['all-tools'])[0].click()
        for res in self._css("div.search-results-list-item"):
            if not res.find_by_css(path['plus-icon']):
                res.find_by_css(path['add-btn'])[0].click()
        sleep(0.5)
        self._css('div.widget_message span.btn')[0].click()
        # fix errors
        self._css(path['close-prefs'])[0].click()
        while not self._elCss(path['search-btn']):
            time.sleep(0.5)
        self.logger.debug("cleared preferencies")


class Movement(object):
    def __init__(self, prod_id, product, quantity, mode, price, earn):
        self.id = prod_id
        self.product = product
        self.quantity = quantity
        self.mode = mode
        self.price = price
        self.earn = earn


class Stock(object):
    def __init__(self, name):
        self.name = name
        self.vars = []

    def addVar(self, var):
        '''add a variation (list)'''
        self.vars.append(var)
