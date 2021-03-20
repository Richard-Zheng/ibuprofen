import asyncio
import aiohttp
import hashlib
import json
import argparse
import html
from pathlib import Path
from airium import Airium
import xml.etree.ElementTree as ET

import soap
import config
import export

data_dir = Path('data')
data_dir.mkdir(parents=True, exist_ok=True)

class UserSession:
    def __init__(self, session: aiohttp.ClientSession, uid: str, soap_url: str):
        self.session = session
        self.uid = uid
        self.soap_url = soap_url

    async def fetch(self, action, param):
        async with self.session.post(self.soap_url, headers={
            'User-Agent': 'ksoap2-android/2.6.0+',
            'SOAPAction': 'http://webservice.myi.cn/wmstudyservice/wsdl/' + action,
            'Content-Type': 'text/xml;charset=utf-8',
            'Cookie': 'userguid=ffffffffffffffffffffffffffffffff;username=paduser;usergroupguid=ffffffffffffffffffffffffffffffff',
            'Accept-Encoding': 'gzip'
        }, data=soap.param_to_request_body(action, param)) as response:
            return await response.text()

    async def get_user_classes(self, password):
        login_data = json.loads(ET.fromstring(await soap.fetch(self.session, self.soap_url, 'UsersLoginJson', {
            'lpszUserName': self.uid,
            'lpszPasswordMD5': hashlib.md5(password.encode()).hexdigest(),
            'lpszHardwareKey': config.HARDWARE_KEY,
        }))[1][0][0].text)
        user_classes = []
        for user_class_data in login_data['classes']:
            user_classes.append(UserClass(user_class_data['guid'], user_class_data['name']))
        return user_classes

    async def get_lesson_schedule_details(self, lesson_schedule: dict):
        result = await soap.fetch(self.session, self.soap_url, 'GetResourceByGUID', {
            'lpszResourceGUID': lesson_schedule['resourceguid']
        })
        root = ET.fromstring(html.unescape(result))
        try:
            del root[1][0][0][0][0].attrib['guid']
            lesson_schedule.update(root[1][0][0][0][0].attrib)
        except:
            return

        file_resources = []
        for ref in root[1][0][0][0][0][2]:
            result = await soap.fetch(self.session, self.soap_url, 'GetResourceByGUID', {
                'lpszResourceGUID': ref.attrib['guid']
            })
            try:
                content = ET.fromstring(html.unescape(result))[1][0][0][0][0][2].attrib
            except:
                continue
            file_resources.append({'guid': ref.attrib['guid'],'title': ref.attrib['title'],'fileURI': content['fileURI']})
        lesson_schedule['file_resources'] = file_resources

class User:
    def __init__(self, session: aiohttp.ClientSession, uid: str, soap_url: str, user_classes: list):
        self.session = session
        self.uid = uid
        self.soap_url = soap_url
        self.user_classes = user_classes
        self.data_path = Path(data_dir, 'user_'+self.uid+'.txt')

async def get_user(session: aiohttp.ClientSession, uid: str, soap_url: str):
    user = User(session, uid, soap_url, [])
    guid = await soap.request_for_text(session, soap_url, 'UsersGetUserGUID', {'lpszUserName': uid})
    info = await soap.request_for_text(session, soap_url, 'UsersGetUserInfoByGUID', {'szUserGUID': guid})
    if info:
        i = json.loads(info)
        for user_class_data in i['classes']:
            user.user_classes.append(UserClass(session, user_class_data['guid'], user_class_data['name'], uid, soap_url))
    return user

async def login(session: aiohttp.ClientSession, uid: str, soap_url: str, password: str):
    user = User(session, uid, soap_url, [])
    p = user.data_path
    if p.exists():
        with p.open(mode='r') as f:
            user.login_data = json.load(f)
    else:
        login_data_text = await soap.request_for_text(session, soap_url, 'UsersLoginJson', {
            'lpszUserName': uid,
            'lpszPasswordMD5': hashlib.md5(password.encode()).hexdigest(),
            'lpszHardwareKey': config.HARDWARE_KEY,
        })
        with p.open(mode='w') as f:
            f.write(login_data_text)
        user.login_data = json.loads(login_data_text)
    for user_class_data in user.login_data['classes']:
        user.user_classes.append(UserClass(session, user_class_data['guid'], user_class_data['name'], uid, soap_url))
    return user

class UserClass:
    def __init__(self, guid, name):
        self.guid = guid
        self.name = name
        self.lesson_schedules = self.load_lesson_schedules()
        self.szReturnXML = generate_szReturnXML(self.lesson_schedules)

    def get_data_path(self):
        return Path(data_dir, 'user_class_'+self.guid+'.txt')

    def load_lesson_schedules(self):
        p = self.get_data_path()
        if p.exists():
            with p.open(mode='r') as f:
                return json.load(f)
        else:
            return []

    def save_lesson_schedules(self):
        with self.get_data_path().open(mode='w') as f:
            json.dump(self.lesson_schedules, f)

    async def fetch_lesson_schedules_table(self, us: UserSession):
        response_attr = {'hasMoreData': 'true'}
        tasks = []
        while response_attr['hasMoreData'] == 'true':
            result = html.unescape(await us.fetch('LessonsScheduleGetTableData', {
                'lpszTableName': 'lessonsschedule',
                'lpszUserClassGUID': self.guid,
                'lpszStudentID': us.uid,
                'lpszLastSyncTime': '',
                'szReturnXML': 'enablesegment=3;' + self.szReturnXML,
            }))
            root = ET.fromstring(result)
            response_attr = root[1][0][0][0].attrib
            for record in root[1][0][0][0]:
                self.szReturnXML += record[0].text + '=' + record[9].text + ';'
                lesson_schedule = {
                    "guid": record[0].text,
                    "resourceguid": record[4].text,
                    "syn_timestamp": record[9].text
                }
                self.lesson_schedules.append(lesson_schedule)
                tasks.append(asyncio.create_task(us.get_lesson_schedule_details(lesson_schedule)))
        await asyncio.wait(tasks)
        self.save_lesson_schedules()

def generate_szReturnXML(records):
    szReturnXML = ''
    for record in records:
        szReturnXML += record['guid'] + '=' + record['syn_timestamp'] + ';'
    return szReturnXML

async def main(args):
    async with aiohttp.ClientSession() as session:
        username = args.username.split('@')
        us = UserSession(session, username[0], 'https://{0}/wmexam/wmstudyservice.WSDL'.format(username[1]))
        user_classes = await us.get_user_classes(args.password if args.password else '123456')
        tasks = []
        for user_class in user_classes:
            tasks.append(user_class.fetch_lesson_schedules_table(us))
        await asyncio.wait(tasks)
        export.StaticHtmlGenerator(user_classes).generate_all_html()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("username", help="full username")
    parser.add_argument("-p", "--password", help="password (123456 by default)")
    args = parser.parse_args()
    asyncio.run(main(args))
