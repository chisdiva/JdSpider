import scrapy

class DangSpider(scrapy.Spider):
    name = 'dang'
    allowed_domains = ['jd.com']
    start_urls = ['https://list.jd.com/list.html?tid=1014398&page=1', 'https://list.jd.com/list.html?tid=1014398&page=3',
                  'https://list.jd.com/list.html?tid=1014398&page=5', 'https://list.jd.com/list.html?tid=1014398&page=7']

    def parse(self, response):
        li_list = response.xpath('//*[@id="J_goodsList"]/ul/li')
        for li in li_list:
            goods_id = li.xpath('./@data-sku').get()
            names = li.xpath('.//div[contains(@class,"p-name")]/a/em')
            name = names.xpath('string(.)').get()
            price = round(float(li.xpath('.//div[contains(@class,"p-price")]/strong/i/text()').get()), 2)
            shop = li.xpath('.//div[contains(@class,"p-shop")]/span/a/text()').get()
            # 京东的商品和图片链接可能有不同的形式，因此如果未获取到结果要尝试另一解析规则
            if shop is None:
                shop = li.xpath('.//div[contains(@class,"p-shopnum")]//a/text()').get()
            print(name)
