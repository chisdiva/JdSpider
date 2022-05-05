import re
import scrapy
import json
from jsonpath import jsonpath
from JD_test.items import GoodsCommentContent

from scrapy_redis.spiders import RedisSpider
from scrapy_redis.utils import bytes_to_str


class SnCommentSpider(RedisSpider):
    name = 'SN_comment'
    allowed_domains = ['suning.com']
    redis_key = 'sn_comment:start_urls'
    custom_settings = {
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'JD_test.middlewares.RandomUserAgentMiddleware': 543,
            'JD_test.middlewares.RandomProxyMiddleware': 722,
            'JD_test.middlewares.MyRetryMiddleware': 500,
        },
        'ITEM_PIPELINES':{
        'JD_test.pipelines.MongoPipeline': 300,
        # 'scrapy_save_to_qiniu.pipelines.SaveToQiniuPipeline': 30,
        'JD_test.pipelines.CommentContentPipeline': 100,
        'JD_test.pipelines.TimePipeline': 20,
    }
    }
    def __init__(self, set_comment_page=1, *args, **kwargs):
        # 参数初始化
        self.task_id = 1
        self.cluster_id = ''
        self.base_url = ''
        self.set_comment_page = int(set_comment_page)
        self.product_id = ''
        super(SnCommentSpider, self).__init__(*args, **kwargs)

    def make_request_from_data(self, data):
        try:
            url_data = json.loads(data)
        except Exception as e:
            url = bytes_to_str(data, self.redis_encoding)
            return self.make_requests_from_url(url)
        self.set_comment_page = url_data['set_comment_page']
        self.task_id = url_data['task_id']
        self.cluster_id = url_data['cluster_id']
        self.product_id = url_data['product_id']
        id_list = re.search(r"(\d+)-(\d+)", self.product_id).groups()
        first_id = id_list[0]
        second_id = id_list[1]
        return scrapy.Request(self.suning_comment_interface(first_id, second_id, self.cluster_id, 0),
                              callback=self.parse_comments_content,
                              meta={'current_page': 0, 'goods_id': self.product_id,
                                    'first_id': first_id,'second_id': second_id, 'cluster_id': self.cluster_id})

    def suning_comment_interface(self, first_id, second_id, cluster_id, comment_page):
        comment_interface = ''
        if cluster_id == "":
            comment_interface = f'https://review.suning.com/ajax/cluster_review_lists/general--0000000{second_id}-{first_id}-total-{comment_page+1}-default-10-----reviewList.htm?callback=reviewList'
        else:
            comment_interface = f'https://review.suning.com/ajax/cluster_review_lists/cluster-{cluster_id}-0000000{second_id}-{first_id}-total-{comment_page+1}-default-10-----reviewList.htm?callback=reviewList'
        return comment_interface

    def parse_comments_content(self, response):
        first_id = response.meta['first_id']
        second_id = response.meta['second_id']
        cluster_id = response.meta['cluster_id']
        goods_id = response.meta['goods_id']
        current_comment_page = response.meta['current_page']
        # 去掉json数据外的包裹函数
        result = json.loads(response.text.lstrip("reviewList(").rstrip(")"))
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
                                                        task_id=self.task_id,
                                                        prod_class='')
            yield comments_content_item
        if current_comment_page + 1 < self.set_comment_page:
            yield scrapy.Request(
                url=self.suning_comment_interface(first_id, second_id, cluster_id, current_comment_page + 1),
                callback=self.parse_comments_content,
                meta={'current_page': current_comment_page + 1,
                      'goods_id': goods_id,
                      'first_id': first_id, 'second_id': second_id, 'cluster_id': cluster_id})

