import feapder


class XueQiuSpider(feapder.AirSpider):
    def start_requests(self):
        for i in range(10):
            yield feapder.Request("https://news.qq.com/", render=True)

    def parse(self, request, response):
        print(response.browser)
        print(response)

        article_list = response.xpath('//div[@class="detail"]')
        for article in article_list:
            title = article.xpath("string(.//a)").extract_first()
            print(title)


if __name__ == "__main__":
    XueQiuSpider(thread_count=10).start()
