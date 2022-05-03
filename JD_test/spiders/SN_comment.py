import re

import scrapy
from pydispatch import dispatcher
from scrapy import signals
import json
from jsonpath import jsonpath
from selenium import webdriver

from JD_test.items import GoodsCommentContent

from scrapy_redis.spiders import RedisSpider
from scrapy_redis.utils import bytes_to_str


class SnCommentSpider(RedisSpider):
    name = 'SN_comment'
    allowed_domains = ['suning.com']
    redis_key = 'sn_comment:start_urls'
    def __init__(self, set_comment_page=1, *args, **kwargs):
        # 参数初始化
        self.base_url = ''
        self.set_comment_page = int(set_comment_page)
        self.product_id = ''
        super(SnCommentSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def make_request_from_data(self, data):
        try:
            url_data = json.loads(data)
        except Exception as e:
            url = bytes_to_str(data, self.redis_encoding)
            return self.make_requests_from_url(url)
        base_detail_url = 'https://product.suning.com/'
        self.set_comment_page = url_data['set_comment_page']
        self.base_url = base_detail_url.format(key_word=url_data['key_word'])
        self.product_id = url_data['product_id']

    def parse_detail(self, response):
        cluster = response.xpath('//script[@type="text/javascript"]/text()').get()
        cluster_id = re.search(r"clusterId\":\"(\d*).*?\"", cluster).group(1)
        id_list = re.search(r"(\d+)-(\d+)", response.meta['goods_id']).groups()
        first_id = id_list[0]
        second_id = id_list[1]
        comment_summary_interface = f"https://review.suning.com/ajax/review_count/cluster-{cluster_id}-0000000{second_id}-{first_id}-----satisfy.htm?callback=satisfy"
        yield scrapy.Request(comment_summary_interface, callback=self.parse_comments, meta={'item': response.meta['item'],
                                                                                            'first_id': first_id,
                                                                                            'second_id': second_id,
                                                                                            'cluster_id': cluster_id})
