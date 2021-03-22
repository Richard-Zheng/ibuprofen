import asyncio
import aiohttp
import hashlib
import json
import argparse
import html
from pathlib import Path
from airium import Airium
import xml.etree.ElementTree as ET

import config
import export

data_dir = Path('data')
data_dir.mkdir(parents=True, exist_ok=True)

def param_to_request_body(action, param):
    res = '''<v:Envelope xmlns:v="http://schemas.xmlsoap.org/soap/envelope/" xmlns:i="http://www.w3.org/2001/XMLSchema-instance" xmlns:d="http://www.w3.org/2001/XMLSchema" xmlns:c="http://schemas.xmlsoap.org/soap/encoding/">
    <v:Header/>
    <v:Body>
        <''' + action + ''' xmlns="http://webservice.myi.cn/wmstudyservice/wsdl/" id="o0" c:root="1">'''
    for key in param:
        res += '''
            <{0} i:type="d:{1}">{2}</{0}>'''.format(key, 'string', param[key])
    res += '''
        </{0}>
    </v:Body></v:Envelope>'''.format(action)
    return res

class UserSession:
    def __init__(self, session: aiohttp.ClientSession, uid: str, host: str):
        self.session = session
        self.uid = uid
        self.host = host
        self.soap_url = 'https://{0}/wmexam/wmstudyservice.WSDL'.format(host)

    async def upload_to_temp_storage(self, filename, data):
        async with self.session.post('https://{0}/PutTemporaryStorage?filename={1}'.format(self.host, filename), data=data) as response:
            return await response.text()

    async def fetch(self, action, param):
        async with self.session.post(self.soap_url, headers={
            'User-Agent': 'ksoap2-android/2.6.0+',
            'SOAPAction': 'http://webservice.myi.cn/wmstudyservice/wsdl/' + action,
            'Content-Type': 'text/xml;charset=utf-8',
            'Cookie': 'userguid=ffffffffffffffffffffffffffffffff;username=paduser;usergroupguid=ffffffffffffffffffffffffffffffff',
            'Accept-Encoding': 'gzip'
        }, data=param_to_request_body(action, param)) as response:
            return await response.text()

    async def get_user_classes(self, password):
        login_data = json.loads(ET.fromstring(await self.fetch('UsersLoginJson', {
            'lpszUserName': self.uid,
            'lpszPasswordMD5': hashlib.md5(password.encode()).hexdigest(),
            'lpszHardwareKey': config.HARDWARE_KEY,
        }))[1][0][0].text)
        user_classes = []
        for user_class_data in login_data['classes']:
            user_classes.append(UserClass(user_class_data['guid'], user_class_data['name']))
        return user_classes

    async def get_lesson_schedule_details(self, lesson_schedule: dict):
        result = await self.fetch('GetResourceByGUID', {
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
            result = await self.fetch('GetResourceByGUID', {
                'lpszResourceGUID': ref.attrib['guid']
            })
            try:
                content = ET.fromstring(html.unescape(result))[1][0][0][0][0][2].attrib
            except:
                continue
            file_resources.append({'guid': ref.attrib['guid'],'title': ref.attrib['title'],'fileURI': content['fileURI']})
        lesson_schedule['file_resources'] = file_resources

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
        us = UserSession(session, username[0], username[1])
        user_classes = await us.get_user_classes(args.password if args.password else '123456')
        tasks = []
        for user_class in user_classes:
            tasks.append(asyncio.create_task(user_class.fetch_lesson_schedules_table(us)))
        await asyncio.wait(tasks)
        #export.StaticHtmlGenerator(user_classes).generate_all_html()
        tasks = []
        tasks.append(asyncio.create_task(us.upload_to_temp_storage('~TMP_{0}.html'.format(us.uid), export.generate_index_html(user_classes, lambda x: 'https://{0}/GetTemporaryStorage?filename={1}'.format(us.host, '~TMP_user_class_'+x.guid+'.html')))))
        for user_class in user_classes:
            tasks.append(asyncio.create_task(us.upload_to_temp_storage('~TMP_user_class_'+user_class.guid+'.html', export.generate_user_class_html(user_class))))
        await asyncio.wait(tasks)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("username", help="full username")
    parser.add_argument("-p", "--password", help="password (123456 by default)")
    args = parser.parse_args()
    asyncio.run(main(args))
