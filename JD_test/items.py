# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

'''
class JdCategory(scrapy.Item):
    b_category_name = scrapy.Field()
    b_category_url = scrapy.Field()


class JdCategory_m(scrapy.Item):
    m_category_name = scrapy.Field()
    m_category_url = scrapy.Field()
    # 所属的一级分类
    related_b_category = scrapy.Field()


class JdCategory_s(scrapy.Item):
    s_category_name = scrapy.Field()
    s_category_url = scrapy.Field()
    related_m_category = scrapy.Field()
    
'''


class Category(scrapy.Item):
    b_category_name = scrapy.Field()
    # b_category_url = scrapy.Field()
    m_category_name = scrapy.Field()
    m_category_url = scrapy.Field()
    s_category_name = scrapy.Field()
    s_category_url = scrapy.Field()


class JdGoodsItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    id = scrapy.Field()
    name = scrapy.Field()
    price = scrapy.Field()
    comment = scrapy.Field()


class GoodsComment(scrapy.Item):
    comment_num = scrapy.Field()
    good_comment_rate = scrapy.Field()
    negative_comment_rate = scrapy.Field()
    comments_content = scrapy.Field()
