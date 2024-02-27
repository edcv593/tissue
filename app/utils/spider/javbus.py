import random
import re

import requests
from lxml import etree
from urllib.parse import urljoin

from app.schema import VideoDetail, VideoActor, SubscribeScrape
from app.utils.spider.spider import Spider
from app.utils.spider.spider_exception import SpiderException


class JavbusSpider(Spider):
    host = "https://www.javbus.com/"
    name = 'Javbus'

    def get_info(self, num: str):

        url = urljoin(self.host, num)
        response = self.session.get(url, allow_redirects=False)

        html = etree.HTML(response.text)

        meta = VideoDetail()
        meta.num = num

        title_element = html.xpath("//h3")
        if title_element:
            title = title_element[0].text
            meta.title = title
        else:
            raise SpiderException('未找到番号')

        premiered_element = html.xpath("//span[text()='發行日期:']")
        if premiered_element:
            meta.premiered = premiered_element[0].tail.strip()

        runtime_element = html.xpath("//span[text()='長度:']")
        if runtime_element:
            runtime = runtime_element[0].tail.strip()
            runtime = runtime.replace("分鐘", "")
            meta.runtime = runtime

        director_element = html.xpath("//span[text()='導演:']/../a")
        if director_element:
            director = director_element[0].text
            meta.director = director

        studio_element = html.xpath("//span[text()='製作商:']/../a")
        if studio_element:
            studio = studio_element[0].text
            meta.studio = studio

        publisher_element = html.xpath("//span[text()='發行商:']/../a")
        if publisher_element:
            publisher = publisher_element[0].text
            meta.publisher = publisher

        series_element = html.xpath("//span[text()='系列:']/../a")
        if series_element:
            series = series_element[0].text
            meta.series = series

        tag_elements = html.xpath("//span[@class='genre']//a[contains(@href,'genre')]")
        if tag_elements:
            tags = [tag.text for tag in tag_elements]
            meta.tags = tags

        actor_elements = html.xpath("//span[@class='genre']//a[contains(@href,'star')]")
        if actor_elements:
            actors = []
            for element in actor_elements:
                actor_url = element.get('href')
                actor_code = actor_url.split("/")[-1]
                actor_avatar = urljoin(self.host, f'/pics/actress/{actor_code}_a.jpg')
                actor = VideoActor(name=element.text, thumb=actor_avatar)
                actors.append(actor)
            meta.actors = actors

        cover_element = html.xpath("//a[@class='bigImage']")
        if cover_element:
            cover = cover_element[0].get("href")
            meta.cover = urljoin(self.host, cover)

        meta.website.append(url)

        return meta

    def get_video(self, url: str):
        response = self.session.get(url, allow_redirects=False).text

        params = {'lang': 'zh', 'floor': random.Random().randint(100, 1000)}

        gid = re.search(r'var gid = (\w+);', response)
        params['gid'] = gid.group(1)

        uc = re.search(r'var uc = (\w+);', response)
        params['uc'] = uc.group(1)

        img = re.search(r'var img = \'(.+)\';', response)
        params['img'] = img.group(1)

        response = self.session.get(urljoin(self.host, '/ajax/uncledatoolsbyajax.php'), params=params,
                                    allow_redirects=True, headers={'Referer': self.host})
        html = etree.HTML(f'<table>{response.text}</table>', parser=etree.HTMLParser(encoding='utf-8'))

        result = []
        table = html.xpath("//tr")
        for item in table:
            parts = item.xpath("./td[1]/a")
            if not parts:
                continue

            video = SubscribeScrape()
            video.website = self.name
            video.url = url
            video.name = parts[0].text.strip()
            video.magnet = parts[0].get('href')

            title = parts[0].text.strip()
            if '无码' in title or '破解' in title:
                video.is_uncensored = True

            for tag in parts[1:]:
                if tag.text == '高清':
                    video.is_hd = True
                if tag.text == '字幕':
                    video.is_zh = True

            size_element = item.xpath("./td[2]/a")[0]
            video.size = size_element.text.strip()

            publish_date_element = item.xpath("./td[3]/a")[0]
            video.publish_date = publish_date_element.text.strip()

            result.append(video)
        return result
