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


class GoodsItem(scrapy.Item):
    # define the fields for your item here\:
    id = scrapy.Field()  # 商品id
    cluster = scrapy.Field()  # 苏宁clusterId
    name = scrapy.Field()  # 商品名称
    price = scrapy.Field()  # 商品价格
    shop = scrapy.Field()  # 商品店铺
    comment_info = scrapy.Field()  # 商品的评论情况
    prod_class = scrapy.Field()  # 商品所属的集合
    task_id = scrapy.Field()  # 爬取任务的id
    image_urls = scrapy.Field()  # 图片链接
    images = scrapy.Field()  # 图片存储后信息
    source = scrapy.Field()  # 商品来源
    crawl_time = scrapy.Field() # 抓取时间


class GoodsComment(scrapy.Item):
    comment_num = scrapy.Field()  # 评论数量
    good_comment_rate = scrapy.Field()  # 好评率
    negative_comment_rate = scrapy.Field()  # 差评率


class GoodsCommentContent(scrapy.Item):
    goods_id = scrapy.Field()  # 商品id
    comment_id = scrapy.Field()  # 评论id
    comment_content = scrapy.Field()  # 评论内容
    score = scrapy.Field()  # 分数
    create_time = scrapy.Field()  # 创建时间
    isPlus = scrapy.Field()  # 是否会员
    userClient = scrapy.Field()  # 来源客户端
    task_id = scrapy.Field() # 任务id
    prod_class = scrapy.Field()  # 任务名称
    crawl_time = scrapy.Field() # 抓取时间

