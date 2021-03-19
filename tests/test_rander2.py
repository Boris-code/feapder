import feapder


class XueQiuSpider(feapder.Spider):
    __custom_setting__ = dict(
        REDISDB_IP_PORTS="localhost:6379", REDISDB_USER_PASS="", REDISDB_DB=0
    )

    def start_requests(self):
        for i in range(10):
            yield feapder.Request("https://news.qq.com/#{}".format(i), render=True)

    def parse(self, request, response):
        print(response.cookies.get_dict())
        print("response.url ", response.url)

        article_list = response.xpath('//div[@class="detail"]')
        for article in article_list:
            title = article.xpath("string(.//a)").extract_first()
            print(title)


if __name__ == "__main__":
    XueQiuSpider(
        thread_count=10, redis_key="feapter:test_rander", delete_keys=True
    ).start()
