import logging
import re
import time

from redis.exceptions import ConnectionError

import scrapy
from pydispatch import dispatcher
from scrapy import signals
import json
from jsonpath import jsonpath
from selenium import webdriver

from JD_test.items import GoodsItem, GoodsComment, GoodsCommentContent

from scrapy_redis.spiders import RedisSpider
from scrapy_redis.utils import bytes_to_str
from scrapy.exceptions import DontCloseSpider


def retry_if_redis_error(exception):
    logging.info('-重试----')
    return isinstance(exception, ConnectionAbortedError) or isinstance(exception, ConnectionError)


class SnProductSpider(RedisSpider):
    name = 'SN_product'
    allowed_domains = ['suning.com']
    redis_key = 'sn_product:start_urls'
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
        super(SnProductSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def spider_closed(self, spider):
        print('spider closed')
        # 关闭spider时退出浏览器
        self.browser.quit()

    def spider_idle(self, spider):
        """
        Schedules a request if available, otherwise waits.
        or close spider when waiting seconds > MAX_IDLE_TIME_BEFORE_CLOSE.
        MAX_IDLE_TIME_BEFORE_CLOSE will not affect SCHEDULER_IDLE_BEFORE_CLOSE.
        """
        for _ in range(0,5):
            try:
                if self.server is not None and self.count_size(self.redis_key) > 0:
                    self.spider_idle_start_time = int(time.time())

                self.schedule_next_requests()
            except ConnectionError:
                time.sleep(1)
                continue

        max_idle_time = self.settings.getint("MAX_IDLE_TIME_BEFORE_CLOSE")
        idle_time = int(time.time()) - self.spider_idle_start_time
        if max_idle_time != 0 and idle_time >= max_idle_time:
            return

        raise DontCloseSpider

    def make_request_from_data(self, data):
        try:
            url_data = json.loads(data)
        except Exception as e:
            url = bytes_to_str(data, self.redis_encoding)
            return self.make_requests_from_url(url)
        base_search_url = "https://search.suning.com/{key_word}/"
        # 爬取页数
        self.set_page = url_data['set_page']
        # 爬取评论页数
        self.set_comment_page = url_data['set_comment_page']
        self.base_url = base_search_url.format(key_word=url_data['key_word'])
        self.col_name = url_data['key_word']
        # 任务id
        if 'task_id' in url_data:
            self.sp_id = url_data['task_id']
        return self.make_requests_from_url(self.base_url)

    def parse(self, response):
        li_list = response.xpath('//div[contains(@class, "product-list")]/ul/li[contains(@class, "item-wrap")]')
        logging.info(len(li_list))
        for li in li_list:
            # 商品id
            goods_id = li.xpath('./@id').get()
            # 名称
            name_wrap = li.xpath('.//div[contains(@class, "title-selling-point")]/a')
            name = name_wrap.xpath('string(.)').get()
            # 详情页链接
            detail_url = li.xpath('.//div[contains(@class, "title-selling-point")]/a/@href').get()
            detail_url = "https:" + detail_url
            # 图片链接
            img = li.xpath('.//div[contains(@class,"img-block")]/a/img/@src').get()
            image_url = 'https:' + img
            image_urls = [image_url]
            # 苏宁商品价格的整数和小数是分开的，需要分别获取
            price_wrap = li.xpath('.//span[contains(@class, "def-price")]')
            try:
                price_int = int(price_wrap.xpath('./text()[2]').get().strip())
            except Exception as e:
                try:
                    price_int = int(price_wrap.xpath('./text()[1]').get().strip())
                except:
                    try:
                        price_int = int(''.join(price_wrap.xpath('./text()').getall()).strip())
                    except:
                        price_int = 0
            price_frac = price_wrap.xpath('./i[2]/text()').get()
            try:
                price = price_int + (int(price_frac[1:]) / 100)
            except Exception as e:
                price = price_int
            # 店铺
            shop = li.xpath('.//div[contains(@class, "store-stock")]/a/text()').get()
            item = GoodsItem(id=goods_id, name=name, shop=shop, task_id=self.sp_id, price=price, source='苏宁',
                             prod_class=self.col_name, image_urls=image_urls)
            yield scrapy.Request(detail_url, callback=self.parse_detail, meta={'item': item, 'goods_id': goods_id})
        try:
            list_page = response.meta['list_page']
        except Exception as e:
            list_page = 1
        list_page = list_page + 1
        if list_page <= self.set_page:
            next_url = self.base_url + '&cp=' + str(list_page-1)
            yield scrapy.Request(next_url, callback=self.parse, meta={'list_page': list_page})

    def parse_detail(self, response):
        cluster = response.xpath('//script[@type="text/javascript"]/text()').get()
        cluster_id = re.search(r"clusterId\":\"(\d*).*?\"", cluster).group(1)
        id_list = re.search(r"(\d+)-(\d+)", response.meta['goods_id']).groups()
        first_id = id_list[0]
        second_id = id_list[1]
        # 有两种不同逻辑
        comment_cluster_interface = f"https://review.suning.com/ajax/review_count/cluster-{cluster_id}-0000000{second_id}-{first_id}-----satisfy.htm?callback=satisfy"
        comment_general_interface = f"https://review.suning.com/ajax/review_count/general--0000000{second_id}-{first_id}-----satisfy.htm?callback=satisfy"
        if cluster_id == '':
            comment_summary_interface = comment_general_interface
        else:
            comment_summary_interface = comment_cluster_interface
        yield scrapy.Request(comment_summary_interface, callback=self.parse_comments, meta={'item': response.meta['item'],
                                                                                            'first_id': first_id,
                                                                                            'second_id': second_id,
                                                                                            'cluster_id': cluster_id})

    def suning_comment_interface(self, first_id, second_id, cluster_id, comment_page):
        comment_interface = ''
        if cluster_id == "":
            comment_interface = f'https://review.suning.com/ajax/cluster_review_lists/general--0000000{second_id}-{first_id}-total-{comment_page+1}-default-10-----reviewList.htm?callback=reviewList'
        else:
            comment_interface = f'https://review.suning.com/ajax/cluster_review_lists/cluster-{cluster_id}-0000000{second_id}-{first_id}-total-{comment_page+1}-default-10-----reviewList.htm?callback=reviewList'
        return comment_interface

    def parse_comments(self, response):
        first_id = response.meta['first_id']
        second_id = response.meta['second_id']
        cluster_id = response.meta['cluster_id']
        goods_id = response.meta['item']['id']
        # 去掉json数据外的包裹函数
        result = json.loads(response.text.lstrip("satisfy(").rstrip(")"))
        comment_num = int(jsonpath(result, '$..totalCount')[0])
        good_comment_num = int(jsonpath(result, '$..fiveStarCount')[0]) + int(jsonpath(result, '$..fourStarCount')[0])
        bad_comment_num = int(jsonpath(result, '$..twoStarCount')[0]) + int(jsonpath(result, '$..oneStarCount')[0])
        if comment_num > 0:
            good_comment_rate = round(good_comment_num / comment_num, 2)
            negative_comment_rate = round(bad_comment_num / comment_num, 2)
        else:
            good_comment_rate = 0
            negative_comment_rate = 0
        comment_item = GoodsComment(comment_num=comment_num, good_comment_rate=good_comment_rate,
                                    negative_comment_rate=negative_comment_rate)
        item = response.meta['item']
        item['cluster'] = cluster_id
        item['comment_info'] = dict(comment_item)
        if self.set_comment_page > 0:
            yield scrapy.Request(url=self.suning_comment_interface(first_id=first_id,
                                                                   second_id=second_id,
                                                                   cluster_id=cluster_id,
                                                                   comment_page=0),
                                 callback=self.parse_comments_content,
                                 meta={'current_page': 0, 'goods_id': goods_id,
                                       'first_id': first_id,'second_id': second_id, 'cluster_id': cluster_id})
        yield item

    def parse_comments_content(self, response):
        first_id = response.meta['first_id']
        second_id = response.meta['second_id']
        cluster_id = response.meta['cluster_id']
        goods_id = response.meta['goods_id']
        current_comment_page = response.meta['current_page']
        # 去掉json数据外的包裹函数
        result = json.loads(response.text.lstrip("reviewList(").rstrip(")"))
        # print(result['commodityReviews'][0]['commodityInfo']['charaterDesc1'])
        # 苏宁超出最大评论数时会返回无评论数据
        if "无评价数据" in result['returnMsg']:
            return
        # 取出评论内容数组
        comments = result['commodityReviews']
        for i in range(0, len(comments)):
            user_client = ''
            try:
                user_client = comments[i]['deviceType']
            except Exception as e:
                try:
                    user_client = comments[i]['sourceSystem']
                except Exception as e:
                    user_client = 'PC'
            comments_content_item = GoodsCommentContent(goods_id=goods_id, comment_id=comments[i]['commodityReviewId'],
                                                        comment_content=comments[i]['content'],
                                                        score=comments[i]['qualityStar'],
                                                        isPlus=comments[i]['userInfo']['isVip'],
                                                        userClient=user_client,
                                                        create_time=comments[i]['publishTime'],
                                                        task_id=self.sp_id,
                                                        prod_class=self.col_name)
            yield comments_content_item
        if current_comment_page + 1 < self.set_comment_page:
            yield scrapy.Request(url=self.suning_comment_interface(first_id, second_id, cluster_id, current_comment_page+1),
                                 callback=self.parse_comments_content,
                                 meta={'current_page': current_comment_page + 1,
                                       'goods_id': goods_id,
                                       'first_id': first_id,'second_id': second_id, 'cluster_id': cluster_id})

    def comments_content_extract(self, comments, comment_array=None):
        # 提取评论内容
        if comment_array is None:
            comment_array = []
        for i in range(0, len(comments)):
            comment_array.append({
                'create_time': comments[i]['publishTime'],
                'content': comments[i]['content'],
                'score': comments[i]['qualityStar'],
                'userClient': comments[i]['deviceType'] if 'deviceType' in comments[i] else comments[i]['sourceSystem'],
                'isPlus': comments[i]['userInfo']['isVip']
            })

        return comment_array
