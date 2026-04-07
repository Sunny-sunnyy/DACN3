# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class TikiItem(scrapy.Item):
    # define the fields for your item here like:
    name = scrapy.Field()
    # price = scrapy.Field()
    # link = scrapy.Field()
    genre = scrapy.Field()
    sold_number = scrapy.Field()
    number_review = scrapy.Field()
 
    
    pass
