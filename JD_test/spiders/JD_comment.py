import re
import scrapy
import json
from jsonpath import jsonpath
from JD_test.items import GoodsCommentContent

from scrapy_redis.spiders import RedisSpider
from scrapy_redis.utils import bytes_to_str


class SnCommentSpider(RedisSpider):
    name = 'JD_comment'
    allowed_domains = ['jd.com']
    redis_key = 'jd_comment:start_urls'
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