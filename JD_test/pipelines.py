# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

# useful for handling different item types with a single interface
import datetime
import math
import time

import pymongo
from itemadapter import ItemAdapter
from JD_test.spiders.JD_category import JdCategorySpider
from JD_test.spiders.JD_product import JdProductSpider

from JD_test.items import GoodsItem, GoodsCommentContent

from scrapy.pipelines.images import ImagesPipeline


class CategoryPipeline:
    def __init__(self, mongo_host, mongo_port, mongo_db, mongo_username, mongo_pwd, mongo_authsource):
        self.mongo_host = mongo_host
        self.mongo_port = mongo_port
        self.mongo_db = mongo_db
        self.mongo_username = mongo_username
        self.mongo_pwd = mongo_pwd
        self.mongo_authsource = mongo_authsource
        # self.mongo_collection = mongo_collection

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_host=crawler.settings.get('MONGO_HOST'),
            mongo_port=crawler.settings.get('MONGO_PORT'),
            mongo_db=crawler.settings.get('MONGO_DBNAME'),
            mongo_username=crawler.settings.get('MONGO_USERNAME'),
            mongo_pwd=crawler.settings.get('MONGO_PASSWORD'),
            mongo_authsource=crawler.settings.get('MONGO_AUTHSOURCE')
            # mongo_collection=crawler.settings.get('MONGO_DOCNAME')
        )

    def open_spider(self, spider):
        if isinstance(spider, JdCategorySpider):
            self.client = pymongo.MongoClient(host=self.mongo_host, port=self.mongo_port, username=self.mongo_username,
                                              password=self.mongo_pwd, authSource=self.mongo_authsource)
            self.db = self.client[self.mongo_db]
            self.collection = self.db['Category']

    def process_item(self, item, spider):
        if isinstance(spider, JdCategorySpider):
            # if s_url.startswith('https://list.jd.com')
            data = dict(item)
            # self.collection.update_one({'id': data['id']}, {'$set': data}, True)
            self.collection.insert_one(data)
        return item

    def close_spider(self, spider):
        if isinstance(spider, JdCategorySpider):
            self.client.close()


class TimePipeline:
    def process_item(self, item, spider):
        if isinstance(item, GoodsItem):
            item['crawl_time'] = math.floor(time.time())
        return item


class CommentContentPipeline:
    # ?????????????????????????????????????????????
    def process_item(self, item, spider):
        if isinstance(item, GoodsCommentContent):
                if item['userClient'] == 2 or item['userClient'] == 6:
                    item['userClient'] = 'ios'
                elif item['userClient'] == 4 or item['userClient'] == 5:
                    item['userClient'] = 'android'
                else:
                    item['userClient'] = 'pc'
        return item



class MongoPipeline:
    def __init__(self, mongo_host, mongo_port, mongo_db, mongo_username, mongo_pwd, mongo_authsource):
        self.mongo_host = mongo_host
        self.mongo_port = mongo_port
        self.mongo_db = mongo_db
        self.mongo_username = mongo_username
        self.mongo_pwd = mongo_pwd
        self.mongo_authsource = mongo_authsource
        # self.mongo_collection = mongo_collection

    @classmethod
    def from_crawler(cls, crawler):

        return cls(
            mongo_host=crawler.settings.get('MONGO_HOST'),
            mongo_port=crawler.settings.get('MONGO_PORT'),
            mongo_db=crawler.settings.get('MONGO_DBNAME'),
            mongo_username=crawler.settings.get('MONGO_USERNAME'),
            mongo_pwd=crawler.settings.get('MONGO_PASSWORD'),
            mongo_authsource=crawler.settings.get('MONGO_AUTHSOURCE'),
            # mongo_collection=crawler.settings.get('MONGO_DOCNAME')
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(host=self.mongo_host, port=self.mongo_port, username=self.mongo_username,
                                          password=self.mongo_pwd, authSource=self.mongo_authsource)
        self.db = self.client[self.mongo_db]
        # collist = self.db.list_collection_names()
        self.goodsCollection = self.db['Goods']
        self.commentCollection = self.db['Comments_Content']

    def process_item(self, item, spider):
        # ?????????????????????????????????
        if isinstance(item, GoodsItem):
            data = ItemAdapter(item).asdict()
            # self.goodsCollection.update_one({'id': data['id'], 'task_id': data['task_id']},
            #                                 {'$set': data},
            #                                 True)
            self.goodsCollection.insert_one(data)
        elif isinstance(item, GoodsCommentContent):
            data = ItemAdapter(item).asdict()
            # self.commentCollection.update_one({'comment_id': data['comment_id']},
            #                                   {'$set': data},
            #                                   True)
            self.commentCollection.insert_one(data)
        # self.collection.insert_one(data)
        return item

    def close_spider(self, spider):
        self.client.close()
