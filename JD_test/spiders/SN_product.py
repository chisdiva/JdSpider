import re

import scrapy
from pydispatch import dispatcher
from scrapy import signals
import json
from jsonpath import jsonpath
from selenium import webdriver

from JD_test.items import GoodsItem, GoodsComment, GoodsCommentContent

from scrapy_redis.spiders import RedisSpider
from scrapy_redis.utils import bytes_to_str


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
        return scrapy.Request(self.base_url, callback=self.parse, meta={'list_page': 1})

    def parse(self, response):
        li_list = response.xpath('//div[contains(@class, "product-list")]/ul/li[contains(@class, "item-wrap")]')
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
                price_int = int(price_wrap.xpath('./text()[1]').get().strip())
            price_frac = price_wrap.xpath('./i[2]/text()').get()
            price = price_int + (int(price_frac[1:]) / 100)
            # 店铺
            shop = li.xpath('.//div[contains(@class, "store-stock")]/a/text()').get()
            item = GoodsItem(id=goods_id, name=name, shop=shop, task_id=self.sp_id, price=price, source='苏宁',
                             prod_class=self.col_name, image_urls=image_urls)
            yield scrapy.Request(detail_url, callback=self.parse_detail, meta={'item': item, 'goods_id': goods_id})

        list_page = response.meta['list_page']
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
        comment_num = jsonpath(result, '$..totalCount')[0]
        good_comment_num = int(jsonpath(result, '$..fiveStarCount')[0]) + int(jsonpath(result, '$..fourStarCount')[0])
        bad_comment_num = int(jsonpath(result, '$..twoStarCount')[0]) + int(jsonpath(result, '$..oneStarCount')[0])
        good_comment_rate = round(good_comment_num / comment_num, 2)
        negative_comment_rate = round(bad_comment_num / comment_num, 2)
        comment_item = GoodsComment(comment_num=comment_num, good_comment_rate=good_comment_rate,
                                    negative_comment_rate=negative_comment_rate)
        item = response.meta['item']
        item['comment_info'] = dict(comment_item)
        if self.set_comment_page > 0:
            yield scrapy.Request(url=self.suning_comment_interface(first_id=first_id,
                                                                   second_id=second_id,
                                                                   cluster_id=cluster_id,
                                                                   comment_page=0),
                                 callback=self.parse_comments_content,
                                 meta={'current_page': 0, 'comment_array': None, 'goods_id': goods_id,
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
        print(result['commodityReviews'][0]['commodityInfo']['charaterDesc1'])
        # 苏宁超出最大评论数时会返回无评论数据
        if "无评价数据" in result['returnMsg'] or current_comment_page + 1 > self.set_comment_page:
            comments_content_item = GoodsCommentContent(id=goods_id, comments_content=response.meta['comment_array'],
                                                        task_id=self.sp_id,
                                                        prod_class=self.col_name)
            yield comments_content_item
        else:
            # 取出评论内容数组
            comments = result['commodityReviews']
            comment_array = self.comments_content_extract(comments, response.meta['comment_array'])
            yield scrapy.Request(url=self.suning_comment_interface(first_id, second_id, cluster_id, current_comment_page+1),
                                 callback=self.parse_comments_content,
                                 meta={'comment_array': comment_array,
                                       'current_page': current_comment_page + 1,
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