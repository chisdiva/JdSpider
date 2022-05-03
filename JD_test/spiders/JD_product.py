import logging
import math
import pickle
import time

import pymongo
import scrapy
from pydispatch import dispatcher
from scrapy import signals
import json
from jsonpath import jsonpath
from selenium import webdriver
import requests

from JD_test.items import GoodsItem, GoodsComment, GoodsCommentContent

from scrapy_redis.spiders import RedisSpider
from scrapy.exceptions import DontCloseSpider

from twisted.web.client import ResponseFailed


def str2num(num_str):
    if num_str.endswith('+'):
        num_str = num_str[:-1]
    if num_str.endswith('万'):
        num_str = num_str[:-1] + '0000'
    return int(num_str)


class JdProductSpider(RedisSpider):
    # 集成RedisSpider
    name = 'JD_product'
    allowed_domains = ['jd.com']
    # 指定起始url在Redis中的Key
    redis_key = 'jd_product:start_urls'

    # start_urls = ['https://list.jd.com/list.html?cat=1713%2C3258%2C3297&page={}&s=1&click=0']

    def __init__(self, set_page=1, set_comment_page=1, *args, **kwargs):
        # 参数初始化
        self.base_url = ''
        self.col_name = ''
        self.set_page = int(set_page)
        self.set_comment_page = int(set_comment_page)
        self.sp_id = 0

        # selenium配置
        self.options = webdriver.ChromeOptions()
        prefs = {"profile.managed_default_content_settings.images": 2}
        self.options.add_experimental_option("prefs", prefs)
        self.options.add_argument('--headless')
        self.browser = webdriver.Chrome(executable_path="D:\scrpay_test\chromedriver.exe",
                                        chrome_options=self.options)
        super(JdProductSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def spider_closed(self, spider):
        print('spider closed')
        # 关闭spider时退出浏览器
        self.browser.quit()
        # 关闭spider时发送请求表明爬虫完成
        # r = requests.get("http://127.0.0.1:7866/spider/finished")

    # def spider_idle(self):
    #     """
    #     Schedules a request if available, otherwise waits.
    #     or close spider when waiting seconds > MAX_IDLE_TIME_BEFORE_CLOSE.
    #     MAX_IDLE_TIME_BEFORE_CLOSE will not affect SCHEDULER_IDLE_BEFORE_CLOSE.
    #     """
    #     if self.server is not None and self.count_size(self.redis_key) > 0:
    #         self.spider_idle_start_time = int(time.time())
    #
    #     self.schedule_next_requests()
    #
    #     max_idle_time = self.settings.getint("MAX_IDLE_TIME_BEFORE_CLOSE")
    #     idle_time = int(time.time()) - self.spider_idle_start_time
    #     if max_idle_time != 0 and idle_time >= max_idle_time:
    #         return
    #     if idle_time >= 90 and self.crawler.stats.get_value('crawled_product_number') > 0:
    #         # requests.get('http://1.14.150.188:7866/spider/JDClosed', params={'productNum': crawled_product_num,
    #         #                                                                  'commentsNum': crawled_comments_num})
    #         return
    #     raise DontCloseSpider

    def make_request_from_data(self, data):
        """
        从Redis数据库中读取信息构建请求
        """
        url_data = json.loads(data)
        logging.info(url_data)
        base_search_url = "https://search.jd.com/Search?keyword={key_word}&enc=utf-8"
        self.set_page = url_data['set_page']
        self.set_comment_page = url_data['set_comment_page']
        self.base_url = url_data['s_category_url'] if 's_category_url' in url_data else base_search_url.format(
            key_word=url_data['key_word'])
        self.col_name = url_data['s_category_name'] if 's_category_name' in url_data else url_data['key_word']
        if 'task_id' in url_data:
            self.sp_id = url_data['task_id']
        return scrapy.Request(self.base_url, callback=self.parse, meta={'list_page': 1})

    def parse(self, response):
        # 从结果列表页解析商品数据
        li_list = response.xpath('//*[@id="J_goodsList"]/ul/li')
        for li in li_list:
            goods_id = li.xpath('./@data-sku').get()
            names = li.xpath('.//div[contains(@class,"p-name")]/a/em')
            name = names.xpath('string(.)').get()
            price = round(float(li.xpath('.//div[contains(@class,"p-price")]/strong/i/text()').get()), 2)
            shop = li.xpath('.//div[contains(@class,"p-shop")]/span/a/text()').get()
            # 京东的商品和图片链接可能有不同的形式，因此如果未获取到结果要尝试另一解析规则
            if shop is None:
                shop = li.xpath('.//div[contains(@class,"p-shopnum")]//a/text()').get()
            image_url = li.xpath('.//div[contains(@class,"p-img")]/a/img/@src').get()
            if image_url is None:
                image_url = li.xpath('.//div[contains(@class,"p-img")]/a/img/@data-lazy-img').get()
            image_url = 'https:' + image_url
            # 图片管道的image_urls应为数组
            image_urls = [image_url]
            # 构造商品Item实体
            item = GoodsItem(id=goods_id, name=name, price=price, shop=shop, prod_class=self.col_name,
                             task_id=self.sp_id, image_urls=image_urls, source='京东')
            # 构造评论信息接口
            # score:0为全部评论 3为好评 2为中评 1为差评
            comment_summary_interface = "https://club.jd.com/comment/productCommentSummaries.action?referenceIds={goods_id}".format(
                goods_id=goods_id
            )
            #生成评论信息接口，放入爬取队列
            yield scrapy.Request(comment_summary_interface, callback=self.parse_comments, meta={'item': item})

        # 构造下一页的链接并生成请求
        list_page = response.meta['list_page']
        list_page = list_page + 2
        if list_page < self.set_page * 2:
            next_url = self.base_url + '&page=' + str(list_page)
            yield scrapy.Request(next_url, callback=self.parse, meta={'list_page': list_page})

    def parse_comments(self, response):
        item = response.meta['item']
        comment_item = GoodsComment()
        try:
            result = json.loads(response.text)
        except Exception as e:
            raise ResponseFailed
        # 提取评论相关数据
        comment_item['comment_num'] = jsonpath(result, '$..CommentCountStr')[0]
        comment_item['good_comment_rate'] = jsonpath(result, '$..GoodRate')[0]
        comment_item['negative_comment_rate'] = jsonpath(result, '$..PoorRate')[0]
        item['comment_info'] = dict(comment_item)

        # 在这里进行评论内容抓取，把结果返回
        if self.set_comment_page > 0:
            yield scrapy.Request(url=self.create_comment_interface(item['id'], 0),
                                 callback=self.parse_comments_content,
                                 meta={'current_page': 0,
                                       'goods_id': item['id'],
                                       'comment_array': None,
                                       })

        yield item

    def parse_comments_content(self, response, goods_id=None):
        if goods_id is None:
            goods_id = response.meta['goods_id']
        current_comment_page = response.meta['current_page']
        try:
            result = json.loads(response.text)
        except Exception as e:
            comments_content_item = GoodsCommentContent()
            return comments_content_item
        # 取出评论内容数组
        comments = result['comments']
        # 最大页数
        max_page = int(result['maxPage'])

        if current_comment_page + 1 < self.set_comment_page and current_comment_page + 1 < max_page:
            # 小于最大页数，则交给提取函数提取内容，然后继续请求
            comment_array = self.comments_content_extract(comments, response.meta['comment_array'])
            yield scrapy.Request(url=self.create_comment_interface(goods_id, current_comment_page + 1),
                                 callback=self.parse_comments_content,
                                 meta={'comment_array': comment_array, 'current_page': current_comment_page + 1,
                                       'goods_id': goods_id})
        else:
            comment_array = self.comments_content_extract(comments, response.meta['comment_array'])
            comments_content_item = GoodsCommentContent(id=goods_id, comments_content=comment_array,
                                                        task_id=self.sp_id, crawl_time=time.time(),
                                                        prod_class=self.col_name)
            yield comments_content_item

    def create_comment_interface(self, goods_id, comment_page):
        comment_interface = 'https://club.jd.com/comment/productPageComments.action?productId={goods_id}&score={score_type}&sortType=6&page={comment_page}&pageSize=10&isShadowSku=0&fold=1'.format(
            goods_id=str(goods_id), score_type=0, comment_page=comment_page)
        return comment_interface

    def comments_content_extract(self, comments, comment_array=None):
        # 提取评论内容
        if comment_array is None:
            comment_array = []
        for i in range(0, len(comments)):
            comment_array.append({
                'create_time': comments[i]['creationTime'],
                'content': comments[i]['content'],
                'score': comments[i]['score'],
                'isPlus': comments[i]['plusAvailable'] > 0,
                'userClient': comments[i]['userClient']
            })


        return comment_array


'''
    def parse_detail(self, response):
        brand = response.xpath('//ul[contains(@id,"parameter-brand")]/li/a/text()').get()
        # 构造评论信息接口
        # score:0为全部评论 3为好评 2为中评 1为差评
        comment_summary_interface = "https://club.jd.com/comment/productCommentSummaries.action?referenceIds={goods_id}".format(
            goods_id=response.meta['goods_id']
        )
        item = response.meta['item']
        item['brand'] = brand
        yield scrapy.Request(comment_summary_interface, callback=self.parse_comments,
                             meta={'item': item})
'''
