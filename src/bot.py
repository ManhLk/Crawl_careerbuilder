from time import sleep
import requests
from bs4 import BeautifulSoup
import re
from captcha_solver import predict
from captcha_solver.predict import pred
import os

class CareerBuilderBot(object):
    def __init__(self, username, password):
        self.client = requests.session()
        self.headers = {
                'authority': 'careerbuilder.vn',
                'cache-control': 'max-age=0',
                'sec-ch-ua': '"Chromium";v="94", "Google Chrome";v="94", ";Not A Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Linux"',
                'upgrade-insecure-requests': '1',
                'origin': 'https://careerbuilder.vn',
                'content-type': 'application/x-www-form-urlencoded',
                'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-user': '?1',
                'sec-fetch-dest': 'document',
                'referer': 'https://careerbuilder.vn/vi/employers',
                'accept-language': 'en-US,en;q=0.9,vi;q=0.8',
                }
        self.login(username,password)

    def preprocessing(self, text):
        text = str(text)
        replace_list = ['\n', '\r', '\t']
        for item in replace_list:
            text = text.replace(item, '')
        return ' '.join(text.split())

    def pass_captcha(self, url):
        print('Solving captcha image.......')
        while True:
            resp = self.client.get(url, headers= self.headers)
            soup = BeautifulSoup(resp.text)
            # image path
            img_url = soup.find('img', {'class': 'img_code'})['src']
            img_name = img_url.split('/')[-1]
            img_path = f'captcha_image/{img_name}'
            with open(img_path, 'wb') as f:
                f.write(requests.get(img_url).content)
            
            # read captcha
            captcha = predict.pred(img_path)

            # key captcha
            key_captcha = soup.find('input', {'name': 'key_captcha'})['value']

            # body
            data = {"captcha": captcha, "key_captcha": key_captcha}
            resp = self.client.post(url, data, headers= self.headers)
            url = resp.url
            if 'verifycaptcha' not in url:
                os.rename(img_path, img_path.replace(img_name, f'{captcha}.png'))
                print('Solved success !!!')
                return resp
    
    def login(self, username, password):
        login_url = 'https://careerbuilder.vn/vi/employers/login'
        resp = self.client.get(login_url, headers=self.headers)
        soup = BeautifulSoup(resp.text)
        csrf_token = soup.find("input",{"name":"csrf_token_login" })['value']
        resp = self.client.post(login_url, data={"username":username, "password": password, "csrf_token_login": csrf_token}, headers=self.headers)
    
    def search(self, keyword, page_num=1):
        search_url = f'https://careerbuilder.vn/vi/tim-ung-vien/tu-khoa/{keyword}/sort/date_desc/page/{page_num}'
        resp = self.client.get(search_url,headers=self.headers)
        soup = BeautifulSoup(resp.text)
        list_a = soup.find_all("a", {"class": "job-title"})
        num_records = int(soup.select('p.success>strong:nth-child(1)')[0].text.strip().replace(",",''))
        hrefs = [a['href'] for a in list_a if a['href']]
        return {'cv_hrefs': hrefs, 'num_records':num_records}
    
    def parse_cv(self, cv_href):
        resp = self.client.get(cv_href, headers=self.headers)
        soup = BeautifulSoup(resp.text)
        if 'verifycaptcha' in resp.url:
            resp = self.pass_captcha(resp.url)
            soup = BeautifulSoup(resp.text)

        cv_detail_url = soup.find("iframe")['src']
        type = cv_detail_url[-5:]
        if type == '.html':
            cv = {}
            resp = self.client.get(cv_detail_url, headers=self.headers)
            soup = BeautifulSoup(resp.text)
            cv['title'] = soup.find('div',{'class': 'name'}).h4.text
            cv['fullname'] = soup.find('div',{'class': 'name'}).h2.text
            contents = [element for element in soup.find('div', {'class': 'content'}).children if element != '\n']
            status = ''
            for part in contents:
                if part.name == 'h3':
                    status = self.preprocessing(part.text).lower()
                else:
                    if status == 'personal profile' or status == 'thông tin cá nhân':
                        # Personal profile
                        profile = {}
                        for li in part.find_all('li'):
                            li = li.text
                            end_key = li.find(':')
                            if end_key != -1:
                                key = self.preprocessing(li[:end_key])
                                profile[key] = self.preprocessing(li[end_key+1:])
                        cv['profile'] = profile
                    elif status == 'career information' or status == 'thông tin nghề nghiệp':
                        # Career Information
                        career = {}
                        for li in part.find_all('li'):
                            li = li.text
                            end_key = li.find(':')
                            if end_key != -1:
                                key = self.preprocessing(li[:end_key])
                                career[key] = self.preprocessing(li[end_key+1:])
                        cv['career'] = career
                    elif status == 'objectives' or status == 'mục tiêu nghề nghiệp':
                        cv['objective'] = self.preprocessing(part.text)
                    elif status == 'experience' or status == 'kinh nghiệm làm việc':
                        try:
                            exp = {}
                            title = part.find('div', {'class': 'title'}).text
                            title = self.preprocessing(title)
                            endtime = title.find(':')
                            exp['time'] = title[:endtime]
                            end_position = title.find('-', endtime) 
                            exp['position'] = title[endtime+1:end_position] 
                            exp['company'] = title[end_position+1:]
                            exp['detail'] = part.find('div', {'class': 'content_fck'}).text
                            if 'experience' in cv:
                                cv['experience'].append(exp)
                            else:
                                cv['experience'] = [exp]
                        except:
                            continue
                    elif status == 'education' or status == 'học vấn':
                        try:
                            edu = {}
                            title = str(part.find('div', {'class': 'title'}))
                            start_time = title.find('>') + 1
                            end_time = title.find('<', start_time)
                            edu['time'] = title[start_time:end_time]
                            start_level = title.find('>', end_time)
                            end_level =title.find('-', start_level)
                            edu['level'] = title[start_level + 1:end_level].strip()
                            end_school = title.find('<', end_level)
                            edu['school'] = title[end_level+1 : end_school].strip()
                            edu['detail'] = part.find('div', {'class': 'content_fck'}).text
                            if 'education' in cv:
                                cv['education'].append(edu)
                            else:
                                cv['education'] = [edu]
                        except:
                            continue
                    elif status == 'other certificates' or status== 'chứng chỉ khác':
                        try:
                            item_certificate = {}
                            title = str(part.find('div', {'class': 'title'}))
                            # name certificate
                            start_name = title.find('>') + 1
                            end_name = title.find('<', start_name) 
                            item_certificate['name'] = title[start_name: end_name]
                            # organization
                            start_org = title.find('>', end_name)
                            end_org = title.find('<',start_org)
                            item_certificate['organization'] = title[start_org+1: end_org]
                            
                            item_certificate['time'] = part.find('div', {'class': 'content_fck'}).text

                            if 'certificate' in cv:
                                cv['certificate'].append(item_certificate)
                            else:
                                cv['certificate'] = [item_certificate]
                        except:
                            continue

            cv['skill'] = [self.preprocessing(li.text) for li in soup.find('ul', {'class': 'skill'}).find_all('li')]
            cv['url_cv'] = cv_detail_url
            # Download image
            image_name = cv_detail_url.split('/')[-1][:-5]
            image_url = soup.find('img')['src']
            with open(f'avatars/{image_name}.jpg', 'wb') as f:
                f.write(requests.get(image_url).content)
            return {'type': 'html', 'data': cv}
        else:
            return {'type': 'pdf', 'data': None}


        ## Parse



