# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import datetime
import time

from itemadapter import ItemAdapter

import pymongo
from itemadapter import ItemAdapter
from JD_test.spiders.JD_category import JdCategorySpider
from JD_test.spiders.JD_product import JdBookSpider

from JD_test.items import JdGoodsItem, GoodsCommentContent
from subprocess import CREATE_NO_WINDOW

class CategoryPipeline:
    def __init__(self, mongo_host, mongo_port, mongo_db):
        self.mongo_host = mongo_host
        self.mongo_port = mongo_port
        self.mongo_db = mongo_db
        #self.mongo_collection = mongo_collection

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_host=crawler.settings.get('MONGO_HOST'),
            mongo_port=crawler.settings.get('MONGO_PORT'),
            mongo_db=crawler.settings.get('MONGO_DBNAME'),
            #mongo_collection=crawler.settings.get('MONGO_DOCNAME')
        )

    def open_spider(self, spider):
        if isinstance(spider, JdCategorySpider):
            self.client = pymongo.MongoClient(host=self.mongo_host, port=self.mongo_port)
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


class JdTestPipeline:
    def __init__(self, mongo_host, mongo_port, mongo_db):
        self.mongo_host = mongo_host
        self.mongo_port = mongo_port
        self.mongo_db = mongo_db
        #self.mongo_collection = mongo_collection


    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_host=crawler.settings.get('MONGO_HOST'),
            mongo_port=crawler.settings.get('MONGO_PORT'),
            mongo_db=crawler.settings.get('MONGO_DBNAME'),
            #mongo_collection=crawler.settings.get('MONGO_DOCNAME')
        )

    def open_spider(self, spider):
        if isinstance(spider, JdBookSpider):
            self.client = pymongo.MongoClient(host=self.mongo_host, port=self.mongo_port)
            self.db = self.client[self.mongo_db]
            collist = self.db.list_collection_names()
            '''
            self.goodsCollectionName = spider.col_name + '_商品'
            self.commentCollectionName = spider.col_name + '_评论'
            if spider.sp_id is not None:
                self.goodsCollectionName = spider.sp_id + '_' + self.goodsCollectionName
                self.commentCollectionName = spider.sp_id + '_' + self.commentCollectionName
            self.goodsCollection = self.db[self.goodsCollectionName]
            self.commentCollection = self.db[self.commentCollectionName]
            '''
            self.goodsCollection = self.db['Goods']
            self.commentCollection = self.db['Comments']

    def process_item(self, item, spider):
        if isinstance(spider, JdBookSpider):
            # 商品表和评论表分别存储
            if isinstance(item, JdGoodsItem):
                data = ItemAdapter(item).asdict()
                print('存储商品')
                self.goodsCollection.update_one({'id': data['id'], 'task_id': data['task_id']},
                                                {'$set': data},
                                                True)
            elif isinstance(item, GoodsCommentContent):
                data = ItemAdapter(item).asdict()
                if 'crawl_time' not in data:
                    data['crawl_time'] = time.time()
                print('存储评论')
                self.commentCollection.update_one({'id': data['id'], 'task_id': data['task_id']},
                                                  {'$set': data},
                                                  True)
            # self.collection.insert_one(data)
        return item

    def close_spider(self, spider):
        if isinstance(spider, JdBookSpider):
            self.client.close()
