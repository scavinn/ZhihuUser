# -*- coding: utf-8 -*-
import scrapy, json
from ZhihuUser.items import ZhihuuserItem


class ZhihuSpider(scrapy.Spider):
    name = 'zhihu'
    allowed_domains = ['www.zhihu.com']
    start_urls = ['http://www.zhihu.com/']

    custom_settings = {
        'DEFAULT_REQUEST_HEADERS': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
            'authorization': 'oauth c3cef7c66a1843f8b3a9e6a1e3160e20'
        },
        'DOWNLOAD_DELAY': 1.5
    }

    # ==========思路：分别获取一个大V"他关注的人"、"关注他的人"，然后获取用户字段信息，获取url_token进行递归遍历==============

    start_user = 'excited-vczh'

    follows_url = 'https://www.zhihu.com/api/v4/members/{user}/followees?include={include}&offset={offset}&limit={limit}'
    follows_query = 'data[*].answer_count,articles_count,gender,follower_count,is_followed,is_following,badge[?(type=best_answerer)].topics'

    followers_url = 'https://www.zhihu.com/api/v4/members/{user}/followers?include={include}&offset={offset}&limit={limit}'
    followers_query = 'data[*].answer_count,articles_count,gender,follower_count,is_followed,is_following,badge[?(type=best_answerer)].topics'

    user_url = 'https://www.zhihu.com/api/v4/members/{user}?include={include}'
    user_query = 'allow_message,is_followed,is_following,is_org,is_blocking,employments,answer_count,follower_count,articles_count,gender,badge[?(type=best_answerer)].topics'

    def start_requests(self):
        '''
        请求三个url：①"他关注的人"的url；②用户url；③"关注他的人"的url
        :return:
        '''
        yield scrapy.Request(
            self.follows_url.format(user=self.start_user, include=self.follows_query, offset=0, limit=20),
            callback=self.parse_follows)
        yield scrapy.Request(self.user_url.format(user=self.start_user, include=self.user_query),
                             callback=self.parse_user)
        yield scrapy.Request(
            self.followers_url.format(user=self.start_user, include=self.followers_query, offset=0, limit=20),
            callback=self.parse_followers)

    def parse_follows(self, response):
        '''
        ①遍历excited-vczh"他关注的人"，获取用户的url_token，放到user_url中进行请求
        ②获取下一页"他关注的人"，重复①
        :param response:
        :return:
        '''
        results = json.loads(response.text)
        if 'data' in results.keys():
            for result in results.get('data'):  # data下有好几个数据，需要用for进行遍历
                yield scrapy.Request(self.user_url.format(user=result.get('url_token'), include=self.user_query),
                                     callback=self.parse_user)

        if 'paging' in results.keys() and results.get('paging').get('is_end') == False:
            next_page = results.get('paging').get('next')
            yield scrapy.Request(next_page, callback=self.parse_follows)

    def parse_followers(self, response):
        '''
        ①遍历excited-vczh"关注他的人"，获取用户的url_token，放到user_url中进行请求
        ②获取下一页"他关注的人"，重复①
        :param response:
        :return:
        '''
        results = json.loads(response.text)
        if 'data' in results.keys():
            for result in results.get('data'):
                yield scrapy.Request(self.user_url.format(user=result.get('url_token'), include=self.user_query),
                                     callback=self.parse_user)

        if 'paging' in results.keys() and results.get('paging').get('is_end') == False:
            next_page = results.get('paging').get('next')
            yield scrapy.Request(next_page, callback=self.parse_followers)

    def parse_user(self, response):
        '''
        ①遍历爬取xcited-vczh"他关注的人"和"关注他的人"的用户的字段信息；
        ②获取"他关注的人"每个用户的url_token，请求follow_url进行递归爬取；
        ③获取"关注他的人"每个用户的url_token，请求follower_url进行递归爬取
        :param response:
        :return:
        '''
        result = json.loads(response.text)
        item = ZhihuuserItem()
        # item有fields属性，直接输出了Field所有的名称，并以集合形式返回(用于json格式)
        for field in item.fields:
            if field in result.keys():
                item[field] = result.get(field)
        yield item

        yield scrapy.Request(
            url=self.follows_url.format(user=result.get('url_token'), include=self.follows_query, offset=0, limit=20),
            callback=self.parse_follows)
        yield scrapy.Request(
            url=self.followers_url.format(user=result.get('url_token'), include=self.followers_query, offset=0,
                                          limit=20), callback=self.parse_followers)
