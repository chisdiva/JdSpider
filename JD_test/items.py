# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

'''
class JdCategory(scrapy.Item):
    b_category_name = scrapy.Field()
    m_category = scrapy.Field()


class MediumJdCategory(scrapy.Item):
    m_category_name = scrapy.Field()
    m_category_url = scrapy.Field()
    # 所属的一级分类
    s_category = scrapy.Field()


class SmallJdCategory(scrapy.Item):
    s_category_name = scrapy.Field()
    s_category_url = scrapy.Field()
'''


class Category(scrapy.Item):
    """
    b_category_name : 一级分类名称
    m_category_name : 二级分类名称
    m_category_url : 二级分类url
    s_category_name : 三级分类名称
    s_category_url : 三级分类url
    """
    b_category_name = scrapy.Field()
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
    shop = scrapy.Field()
    comment_info = scrapy.Field()
    brand = scrapy.Field()
    prod_class = scrapy.Field()
    task_id = scrapy.Field()
    crawl_time = scrapy.Field()


class GoodsComment(scrapy.Item):
    comment_num = scrapy.Field()
    good_comment_rate = scrapy.Field()
    negative_comment_rate = scrapy.Field()


class GoodsCommentContent(scrapy.Item):
    id = scrapy.Field()
    task_id = scrapy.Field()
    comments_content = scrapy.Field()
    crawl_time = scrapy.Field()
    prod_class = scrapy.Field()
