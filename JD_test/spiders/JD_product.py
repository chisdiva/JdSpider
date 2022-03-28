import scrapy
from pydispatch import dispatcher
from scrapy import signals
from JD_test.items import JdGoodsItem, GoodsComment

import json
from jsonpath import jsonpath
from selenium import webdriver


class JdBookSpider(scrapy.Spider):
    name = 'JD_product'
    allowed_domains = ['jd.com']

    # start_urls = ['https://list.jd.com/list.html?cat=1713%2C3258%2C3297&page={}&s=1&click=0']

    def __init__(self, set_page=5, set_url='https://list.jd.com/list.html?cat=6728,6747,14920', *args, **kwargs):
        # 获取参数
        self.set_url = set_url
        self.set_page = set_page
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
        base_url = self.set_url
        for page in range(1, int(self.set_page), 2):
            url = base_url + '&page=' + str(page)
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
            comment_interface = 'https://club.jd.com/comment/productPageComments.action?productId={goods_id}&score={score_type}&sortType=5&page={comment_page}&pageSize=10&isShadowSku=0&fold=1'.format(
                goods_id=str(goods_id), score_type=0, comment_page=0)

            yield scrapy.Request(comment_interface, callback=self.parse_comments, meta={'item': item})

    def parse_comments(self, response):
        item = response.meta['item']
        comment_item = GoodsComment()
        result = json.loads(response.text)
        # 提取评论相关数据
        comment_item['comment_num'] = jsonpath(result, '$..commentCountStr')[0]
        comment_item['good_comment_rate'] = jsonpath(result, '$..goodRate')[0]
        comment_item['negative_comment_rate'] = jsonpath(result, '$..poorRate')[0]
        comments = result['comments']
        comment_array = []
        for i in range(0, len(comments)):
            comment_array.append(comments[i]['content'])
        comment_item['comments_content'] = comment_array
        item['comment'] = dict(comment_item)
        yield item
