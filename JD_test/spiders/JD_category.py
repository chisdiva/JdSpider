import scrapy
import json
from JD_test.items import Category
# from JD_test.items import JdCategory, MediumJdCategory, SmallJdCategory

import re
import pymongo

'''
class JdCategorySpider(scrapy.Spider):
    name = 'JD_category'
    allowed_domains = ['3.cn']
    start_urls = ['https://dc.3.cn/category/get']

    def parse(self, response):
        result = json.loads(response.body.decode('GBK'))
        data_list = result['data']
        
        for data in data_list:
            item = Category()
            # 获取一级分类
            b_category = data['s'][0]
            # 获取一级分类信息
            b_category_info = b_category['n']
            item['b_category_name'], item['b_category_url'] = self.parse_category_info(b_category_info)
            # 获取二级分类的列表
            m_category_list = b_category['s']

            # 遍历二级分类，获取二级分类信息
            for m_category in m_category_list:
                m_category_info = m_category['n']
                # print("中分类：{}".format(m_category_info))
                item['m_category_name'], item['m_category_url'] = self.parse_category_info(m_category_info)
                # 获取三级分类的列表
                s_category_list = m_category['s']

                # 遍历三级分类列表，获取三级分类信息
                for s_category in s_category_list:
                    s_category_info = s_category['n']
                    # print("小分类：{}".format(s_category_info))
                    item['s_category_name'], item['s_category_url'] = self.parse_category_info(s_category_info)
                    yield item

    def parse_category_info(self, category_info):
        # 解析分类的名称和链接
        # 先按|分割，然后分别进行处理
        categorys = category_info.split('|')
        category_url = categorys[0]
        category_name = categorys[1]

        # 处理url
        if category_url.count('jd.com') == 1:
            category_url = 'https://' + category_url
        elif category_url.count('-') == 1 and re.match(r'\d+-\d+', category_url):
            category_url = 'https://channel.jd.com/{}.html'.format(category_url)
        elif category_url.count('-') == 2:
            category_url = category_url.replace('-', ',')
            category_url = 'https://list.jd.com/list.html?cat={}'.format(category_url)
        else:
            category_url = ''

        return category_name, category_url
'''


class JdCategorySpider(scrapy.Spider):
    name = 'JD_category'
    allowed_domains = ['www.jd.com']
    start_urls = ['https://www.jd.com/allSort.aspx']

    def parse(self, response):
        data_list = response.xpath('//div[@class="col"]/div[@class="category-item m"]')
        for data in data_list:
            item = Category()
            b_category_name = data.xpath('./div[@class="mt"]/h2/span/text()').get()
            # print(b_category_name)
            item['b_category_name'] = b_category_name
            # 二级和三级分类的list
            m_category_list = data.xpath('./div[@class="mc"]/div[@class="items"]/dl')
            for m_category in m_category_list:
                m_category_name = m_category.xpath('./dt/a/text()').get()
                m_category_url = m_category.xpath('./dt/a/@href').get()
                item['m_category_name'] = m_category_name
                item['m_category_url'] = self.parse_category_url(m_category_url)
                # 三级分类的list
                s_category_list = m_category.xpath('./dd/a')
                # 循环取出三级分类信息
                for s_category in s_category_list:
                    s_category_name = s_category.xpath('./text()').get()
                    s_category_url = s_category.xpath('./@href').get()
                    if self.judge_url(s_category_url):
                        item['s_category_name'] = s_category_name
                        item['s_category_url'] = self.parse_category_url(s_category_url)
                        yield item
                    else:
                        continue

    def parse_category_url(self, category_url):
        return 'https:' + category_url

    def judge_url(self, url):
        if url.startswith('//list.jd.com'):
            return True
        else:
            return False
