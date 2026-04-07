import scrapy
from scrapy import item
from ..items import TikiItem
from ..storage import  urls
class TikiScrapSpider(scrapy.Spider):
    name = 'tiki'
    start_urls = urls

    def parse(self, response):
        items  = TikiItem()
        # all_div_tiki = response.css('div')
        # name   = response.css('.name span').css('::text').extract()
        name   = response.xpath("//h1[@class='title']/text()").extract()
        # price  = response.css('.price-discount__price').css('::text').extract()
        genre  = response.xpath("//a[@data-view-index='3']/text()").extract()
        sold_number = response.xpath("//div[@data-view-id='pdp_quantity_sold']/text()").extract()
        number_review = response.xpath("//a[@class='number']/text()").extract()
        # linkf   = response.xpath("//a[@class='product-item']/@href").extract()
        
        # name_1 = ["/"  + item for item in name ]
    
        # items['name'] = list(map(( lambda x: '/' + x), name))


    


        items['sold_number'] = sold_number
        items['number_review'] = number_review
        items['name'] = name
        items['genre'] = genre
        # items['price'] = price

        



        yield items
       

