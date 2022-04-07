import time

import pymongo
import scrapy
from pydispatch import dispatcher
from scrapy import signals
import json
from jsonpath import jsonpath
from selenium import webdriver
import requests

from JD_test.items import JdGoodsItem, GoodsComment, GoodsCommentContent


def str2num(num_str):
    if num_str.endswith('+'):
        num_str = num_str[:-1]
    if num_str.endswith('万'):
        num_str = num_str[:-1] + '0000'
    return int(num_str)


class JdBookSpider(scrapy.Spider):
    name = 'JD_product'
    allowed_domains = ['jd.com']

    # start_urls = ['https://list.jd.com/list.html?cat=1713%2C3258%2C3297&page={}&s=1&click=0']

    def __init__(self, set_page=2, set_comment_page=1, crawl_all_flag=False, key_word=None, category_name=None,
                 spider_id=None, *args,
                 **kwargs):
        if key_word is None and category_name is None and crawl_all_flag is False:
            raise Exception('参数错误！')
        if key_word is None:
            # 分类爬取
            self.col_name = category_name
            self.category_db = pymongo.MongoClient('127.0.0.1', 27017)['JD_test']
            self.url_doc = self.category_db['Category'].find({"s_category_name": category_name})

            self.base_url = list(self.url_doc)[0]['s_category_url']
        else:
            # 关键词爬取
            self.col_name = key_word
            self.base_url = "https://search.jd.com/Search?keyword={key_word}&enc=utf-8".format(key_word=key_word)
        # 获取参数
        self.set_page = int(set_page)
        self.set_comment_page = int(set_comment_page)
        self.sp_id = 0
        if spider_id is not None:
            self.sp_id = spider_id

        # selenium配置
        self.options = webdriver.ChromeOptions()
        prefs = {"profile.managed_default_content_settings.images": 2}
        self.options.add_experimental_option("prefs", prefs)
        self.options.add_argument('--headless')
        self.browser = webdriver.Chrome(executable_path="D:\scrpay_test\chromedriver.exe",
                                        chrome_options=self.options)
        super(JdBookSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def spider_closed(self, spider):
        print('spider closed')
        # 关闭spider时退出浏览器
        self.browser.quit()
        # 关闭spider时发送请求表明爬虫完成
        #r = requests.get("http://127.0.0.1:7866/spider/finished")

    def start_requests(self):
        for page in range(1, int(self.set_page), 2):
            url = self.base_url + '&page=' + str(page)
            print('访问第{}页'.format(page))
            yield scrapy.Request(url)

    def parse(self, response):
        li_list = response.xpath('//*[@id="J_goodsList"]/ul/li')
        for li in li_list:
            goods_id = li.xpath('./@data-sku').get()
            names = li.xpath('.//div[contains(@class,"p-name")]/a/em')
            name = names.xpath('string(.)').get()
            price = li.xpath('.//div[contains(@class,"p-price")]/strong/i/text()').get()
            # comment_num = li.xpath('.//div[@class="p-commit"]/strong/a/text()').extract()
            shop = li.xpath('.//div[contains(@class,"p-shop")]/span/a/text()').get()
            item = JdGoodsItem(id=goods_id, name=name, price=price, shop=shop, prod_class=self.col_name,
                               task_id=self.sp_id)
            # 构造详情页接口
            # detail_interface = f"https://item.jd.com/{goods_id}.html"
            # yield scrapy.Request(detail_interface, callback=self.parse_detail,
                                 # meta={'item': item, 'goods_id': goods_id})
            # 构造评论信息接口
            # score:0为全部评论 3为好评 2为中评 1为差评
            comment_summary_interface = "https://club.jd.com/comment/productCommentSummaries.action?referenceIds={goods_id}".format(
                goods_id=goods_id
            )
            yield scrapy.Request(comment_summary_interface, callback=self.parse_comments, meta={'item': item})

    def parse_comments(self, response):
        item = response.meta['item']
        comment_item = GoodsComment()
        result = json.loads(response.text)
        # 提取评论相关数据
        comment_item['comment_num'] = jsonpath(result, '$..CommentCountStr')[0]
        comment_item['good_comment_rate'] = jsonpath(result, '$..GoodRate')[0]
        comment_item['negative_comment_rate'] = jsonpath(result, '$..PoorRate')[0]
        item['comment_info'] = dict(comment_item)
        item['crawl_time'] = time.time()

        # 在这里进行评论内容抓取，把结果返回
        yield scrapy.Request(url=self.create_comment_interface(item['id'], 0),
                             callback=self.parse_comments_content,
                             meta={'current_page': 0,
                                   'goods_id': item['id'],
                                   'comment_array': None})
        yield item

    def parse_comments_content(self, response, goods_id=None, current_comment_page=None):
        if goods_id is None:
            goods_id = response.meta['goods_id']
        if current_comment_page is None:
            current_comment_page = response.meta['current_page']
        result = json.loads(response.text)
        # 取出评论内容数组
        comments = result['comments']
        # 最大页数
        max_page = int(result['maxPage'])
        if current_comment_page + 1 < self.set_comment_page and current_comment_page + 1 < max_page:
            if current_comment_page == 0:
                print('第{}页评论++++++++++++'.format(current_comment_page))
                comment_array = self.comments_content_extract(comments)
            else:
                comment_array = self.comments_content_extract(comments, response.meta['comment_array'])

            yield scrapy.Request(url=self.create_comment_interface(goods_id, current_comment_page + 1),
                                 callback=self.parse_comments_content,
                                 meta={'comment_array': comment_array, 'current_page': current_comment_page + 1,
                                       'goods_id': goods_id})
        else:
            # 只有一页的情况
            if max_page == 1:
                comment_array = self.comments_content_extract(comments)
            else:
                comment_array = self.comments_content_extract(comments, response.meta['comment_array'])
            comments_content_item = GoodsCommentContent(id=goods_id, comments_content=comment_array, task_id=self.sp_id,
                                                        crawl_time=time.time())
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
                'score': comments[i]['score']
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