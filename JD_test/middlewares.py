# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import logging
import random

import redis
import requests
import re
from time import sleep

from scrapy import signals
from scrapy.http import HtmlResponse
from scrapy.utils.response import response_status_message
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.pipelines.images import ImagesPipeline

from fake_useragent import UserAgent

from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from itemadapter import is_item, ItemAdapter


class JdTestSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class JdTestDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class RandomUserAgentMiddleware(object):
    # 随机更换user-agent
    # 用父类init方法初始化
    def __init__(self, crawler):
        super(RandomUserAgentMiddleware, self).__init__()
        # 使用fake-useragent
        self.ua = UserAgent()

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def process_request(self, request, spider):
        request.headers.setdefault('User-Agent', self.ua.random)


class JSPageMiddleware(object):
    # 通过selenium请求动态网页
    def process_request(self, request, spider):
        if request.url.find('list.jd.com') != -1 or request.url.find('search.jd.com') != -1:
            spider.browser.get(request.url)
            # 执行代码
            js = "document.documentElement.scrollTop=10000"
            spider.browser.execute_script(js)
            # 显性等待，直到选择器获取到第60个商品的节点
            wait(spider.browser, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#J_goodsList > ul > li:nth-child(60)'))
            )
            print("访问:{0}".format(request.url))
            # 遇到htmlResponse,则不会再调用原生下载器
            return HtmlResponse(url=spider.browser.current_url, body=spider.browser.page_source, encoding="utf-8",
                                request=request)
        elif request.url.find('list.suning.com') != -1 or request.url.find('search.suning.com') != -1:
            spider.browser.get(request.url)
            js = "document.documentElement.scrollTop=10000"
            spider.browser.execute_script(js)
            try:
                wait(spider.browser, 5).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR,
                                                         '#product-list > ul > li:nth-child(120) span.def-price > i'))
                )
            finally:
                print("访问:{0}".format(request.url))
                # 遇到htmlResponse,则不会再调用原生下载器
                return HtmlResponse(url=spider.browser.current_url, body=spider.browser.page_source, encoding="utf-8",
                                    request=request)

        # script = '''
        # function main(splash)
        #     splash:go(splash.args.url)
        #     splash:runjs("document.documentElement.scrollTop=10000")
        #     splash:wait(2)
        #     return splash:html()
        # '''
        # script2 = '''
        # function main(splash)
        #     local result, error = splash:wait_for_resume([[
        #         function main(splash) {
        #             var checkExist = setInterval(function() {
        #                 if (document.querySelector("#J_goodsList > ul > li:nth-child(60)")) {
        #                 clearInterval(checkExist);
        #                 splash.resume();
        #                 }
        #             }, 400);
        #         }
        #     ]], 7)
        #     -- result is {}
        #     -- error is nil
        # end
        # '''


class RandomProxyMiddleware(object):
    # 动态设置ip代理
    def process_request(self, request, spider):
        # 当连接失败时使用代理
        ip_port = 'ng001.weimiaocloud.com:9003'
        proxy = "http://" + ip_port
        if request.meta.get('retry_times', 0) > 0:
            # if 'splash' in request['meta']:
            #     request['meta']['splash']['proxy'] = proxy
            try:
                # ip = requests.get("http://127.0.0.1:5010/get/?type=https").json().get("proxy")
                # request.meta["proxy"] = ip
                request.meta['proxy'] = proxy
            except Exception as e:
                pass

        if request.url.find('club') != -1 or request.url.find('review') != -1:
            ran = random.random()
            if ran > 0.7:
                try:
                    # ip = requests.get("http://127.0.0.1:5010/get/?type=https").json().get("proxy")
                    # request.meta["proxy"] = ip
                    request.meta['proxy'] = proxy
                except Exception as e:
                    pass


class MyRetryMiddleware(RetryMiddleware):
    def process_response(self, request, response, spider):
        if request.meta.get('dont_retry', True):
            return response
        if response.status in self.retry_http_codes:
            logging.info('响应异常，尝试删除代理延时2s重试')
            sleep(2)
            try:
                del request.meta["proxy"]
            except Exception as e:
                pass
            reason = response_status_message(response.status)
            return self._retry(request, reason, spider) or response
        return response

    def process_exception(self, request, exception, spider):
        if (
                isinstance(exception, self.EXCEPTIONS_TO_RETRY)
                and not request.meta.get('dont_retry', False)
        ):
            logging.info('出现错误，尝试删除代理延时5s重试')
            sleep(5)
            try:
                del request.meta["proxy"]
            except Exception as e:
                pass
            return self._retry(request, exception, spider)


class StatsCollectorMiddleware(object):
    def __init__(self, host, port, param, settings):
        self.r = redis.Redis()

    @classmethod
    def from_settings(cls, settings):
        host = settings['REDIS_HOST']
        port = settings['REDIS_PORT']
        param = settings['REDIS_PARAMS']['password']
        return cls(host, port, param, settings=settings)
