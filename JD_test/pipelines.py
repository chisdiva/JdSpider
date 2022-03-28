# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter

import pymongo
from itemadapter import ItemAdapter
from JD_test.spiders.JD_category import JdCategorySpider
from JD_test.spiders.JD_book import JdBookSpider


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
            s_url = item['s_category_url']
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
            self.collection = self.db['Goods']

    def process_item(self, item, spider):
        if isinstance(spider, JdBookSpider):

            data = ItemAdapter(item).asdict()
            self.collection.update_one({'id': data['id']}, {'$set': data}, True)
            # self.collection.insert_one(data)
        return item

    def close_spider(self, spider):
        if isinstance(spider, JdBookSpider):
            self.client.close()
