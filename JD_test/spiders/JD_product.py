import pymongo
import scrapy
from pydispatch import dispatcher
from scrapy import signals
from JD_test.items import JdGoodsItem, GoodsComment, GoodsCommentContent

import json
from jsonpath import jsonpath
from selenium import webdriver


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

    def __init__(self, set_page=None, set_comment_page=None, *args, **kwargs):
        # 连接数据库
        self.category_db = pymongo.MongoClient('127.0.0.1', 27017)['JD_test']
        self.url_doc = self.category_db['Category'].find_one({'s_category_name': '拖车绳'})
        self.base_url = self.url_doc['s_category_url']
        # 获取参数
        self.set_page = set_page
        self.set_comment_page = set_comment_page
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

    def start_requests(self):
        print(self.url_doc)
        for page in range(1, int(self.set_page), 2):
            url = self.base_url + '&page=' + str(page)
            print('访问第{}页'.format(page))
            yield scrapy.Request(url)

    def parse(self, response):
        li_list = response.xpath('//*[@id="J_goodsList"]/ul/li')
        for li in li_list:
            goods_id = li.xpath('./@data-sku').get()
            name = li.xpath('.//div[contains(@class,"p-name")]/a/em/text()').get()
            price = li.xpath('.//div[contains(@class,"p-price")]/strong/i/text()').get()
            # comment_num = li.xpath('.//div[@class="p-commit"]/strong/a/text()').extract()
            item = JdGoodsItem(id=goods_id, name=name, price=price)
            # 构造评论信息接口
            # score:0为全部评论 3为好评 2为中评 1为差评
            comment_interface = self.create_comment_interface(goods_id=goods_id, comment_page=0)

            yield scrapy.Request(comment_interface, callback=self.parse_comments,
                                 meta={'item': item}, dont_filter=True)

    def parse_comments(self, response):
        item = response.meta['item']
        comment_item = GoodsComment()
        result = json.loads(response.text)
        # 提取评论相关数据
        comment_item['comment_num'] = jsonpath(result, '$..commentCountStr')[0]
        comment_item['good_comment_rate'] = jsonpath(result, '$..goodRate')[0]
        comment_item['negative_comment_rate'] = jsonpath(result, '$..poorRate')[0]
        item['comment_info'] = dict(comment_item)

        # 在这里进行评论内容抓取，把结果返回
        yield scrapy.Request(url=self.create_comment_interface(item['id'], 0),
                             callback=self.parse_comments_content,
                             meta={'current_page': 0,
                                   'goods_id': item['id'],
                                   'comment_array': None},
                             dont_filter=True)
        yield item

    def parse_comments_content(self, response, goods_id=None, current_comment_page=None):
        if goods_id is None:
            goods_id = response.meta['goods_id']
        if current_comment_page is None:
            current_comment_page = response.meta['current_page']
        result = json.loads(response.text)
        # 取出评论内容数组
        comment_count = str2num(jsonpath(result, '$..commentCountStr')[0])
        comments = result['comments']
        print('评论的内容有+++++++++++')
        print(len(comments))
        if current_comment_page < self.set_comment_page-1 and (current_comment_page + 1) * 10 < comment_count:
            if current_comment_page == 0:
                print('第{}页评论++++++++++++'.format(current_comment_page))
                comment_array = self.comments_content_extract(comments)
            else:
                comment_array = self.comments_content_extract(comments, response.meta['comment_array'])

            yield scrapy.Request(url=self.create_comment_interface(goods_id, current_comment_page + 1),
                                 callback=self.parse_comments_content,
                                 meta={'comment_array': comment_array, 'current_page': current_comment_page + 1,
                                       'goods_id': goods_id},
                                 dont_filter=True)
        else:
            comment_array = self.comments_content_extract(comments, response.meta['comment_array'])
            comments_content_item = GoodsCommentContent(goods_id=goods_id, comments_content=comment_array)
            print('存储评论——+++++++++')
            yield comments_content_item

    def create_comment_interface(self, goods_id, comment_page):
        comment_interface = 'https://club.jd.com/comment/productPageComments.action?productId={goods_id}&score={score_type}&sortType=5&page={comment_page}&pageSize=10&isShadowSku=0&fold=1'.format(
            goods_id=str(goods_id), score_type=0, comment_page=comment_page)
        return comment_interface

    def comments_content_extract(self, comments, comment_array=None):
        # 提取评论内容
        if comment_array is None:
            comment_array = []
        for i in range(0, len(comments)):
            comment_array.append(comments[i]['content'])

        return comment_array
