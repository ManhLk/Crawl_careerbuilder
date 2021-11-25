from src import CareerBuilderBot
from pymongo import MongoClient


if __name__ == '__main__':
    cli = MongoClient(host='localhost:27017')
    clo = cli.CV.audit_career 

    username = 'asg42679@boofx.com'
    password = 'CIST2o20'
    bot = CareerBuilderBot(username, password)

    keyword = 'Kiểm toán nội bộ'
    num_records = bot.search(keyword, 1)['num_records']
    pages = round(num_records/20) + 1
    for i in range(1, pages):
        try:
            print(f'Crawlding page {i} ................')
            cv_hrefs = bot.search(keyword, i)['cv_hrefs']
            for cv_href in cv_hrefs:
                try:
                    cv = bot.parse_cv(cv_href)
                    if cv['type'] == 'html' and clo.find_one({'url_cv': cv['data']['url_cv']}) == None:
                        clo.insert_one(cv['data'])
                        print(cv['data']['fullname'])
                except:
                    continue
        except:
            continue


