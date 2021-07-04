import argparse
import asyncio
import hashlib
import html
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import aiohttp

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
        self.data_path = Path(data_dir, 'user_' + self.uid + '.txt')

    async def upload_to_temp_storage(self, filename, data):
        async with self.session.post('https://{0}/PutTemporaryStorage?filename={1}'.format(self.host, filename),
                                     data=data) as response:
            return await response.text()

    async def fetch(self, action, param):
        async with self.session.post(self.soap_url, headers={
            'User-Agent': 'ksoap2-android/2.6.0+',
            'SOAPAction': 'http://webservice.myi.cn/wmstudyservice/wsdl/' + action,
            'Content-Type': 'text/xml;charset=utf-8',
            'Accept-Encoding': 'gzip',
            'Cookie': 'userguid=ffffffffffffffffffffffffffffffff'
        }, data=param_to_request_body(action, param)) as response:
            return await response.text()

    async def get_user_classes(self, password):
        if self.data_path.exists():
            with self.data_path.open(mode='r') as f:
                login_data = json.load(f)
        else:
            guid = ET.fromstring(await self.fetch('UsersGetUserGUID', {
                'lpszUserName': self.uid
            }))[1][0][0].text
            login_data = json.loads(ET.fromstring(await self.fetch('UsersGetUserInfoByGUID', {
                'szUserGUID': guid,
            }))[1][0][0].text)
            with self.data_path.open(mode='w') as f:
                json.dump(login_data, f)
        user_classes = []
        for user_class_data in login_data['classes']:
            user_classes.append(UserClass(user_class_data['guid'], user_class_data['name']))
        return user_classes

    async def get_lesson_schedule_details(self, lesson_schedule: dict):
        result = await self.fetch('GetResourceByGUID', {
            'lpszResourceGUID': lesson_schedule['resourceguid']
        })
        try:
            lesson_prepare_element = ET.fromstring(html.unescape(result))[1][0][0][0][0]
            del lesson_prepare_element.attrib['guid']
            lesson_schedule.update(lesson_prepare_element.attrib)
        except:
            return

        file_resources = []
        for ref in lesson_prepare_element[2]:
            result = await self.fetch('GetResourceByGUID', {
                'lpszResourceGUID': ref.attrib['guid']
            })
            try:
                resource = ET.fromstring(html.unescape(result))[1][0][0][0][0]
                file_resources.append({'guid': ref.attrib['guid'], 'title': resource.attrib['title'],
                                       'ext': resource.attrib['mainFileExtName'],
                                       'fileURI': resource[2].attrib['fileURI']})
            except:
                continue
        lesson_schedule['file_resources'] = file_resources


class UserClass:
    def __init__(self, guid, name):
        self.guid = guid
        self.name = name
        self.data_path = Path(data_dir, 'user_class_' + self.guid + '.txt')
        self.lesson_schedules = self.load_lesson_schedules()
        self.szReturnXML = ''
        for lesson_schedule in self.lesson_schedules:
            self.szReturnXML += lesson_schedule['guid'] + '=' + lesson_schedule['syn_timestamp'] + ';'

    def load_lesson_schedules(self):
        if self.data_path.exists():
            with self.data_path.open(mode='r') as f:
                return json.load(f)
        else:
            return []

    def save_lesson_schedules(self):
        with self.data_path.open(mode='w') as f:
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
        await asyncio.wait(tasks) if tasks else None
        self.save_lesson_schedules()


async def main(args):
    async with aiohttp.ClientSession() as session:
        username = args.username.split('@')
        us = UserSession(session, username[0], username[1])
        user_classes = await us.get_user_classes(args.password if args.password else '123456')
        tasks = []
        for user_class in user_classes:
            tasks.append(asyncio.create_task(user_class.fetch_lesson_schedules_table(us)))
        await asyncio.wait(tasks)
        tasks = [asyncio.create_task(us.upload_to_temp_storage('~TMP_{0}.html'.format(us.uid),
                                                               export.generate_index_html(
                                                                   user_classes,
                                                                   lambda x: 'https://{0}/GetTemporaryStorage?filename={1}'.format(us.host, '~TMP_user_class_' + x.guid + '.html'))))]
        for user_class in user_classes:
            tasks.append(asyncio.create_task(us.upload_to_temp_storage('~TMP_user_class_' + user_class.guid + '.html',
                                                                       export.generate_user_class_html(user_class))))
        await asyncio.wait(tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("username", help="full username")
    parser.add_argument("-p", "--password", help="password (123456 by default)")
    args = parser.parse_args()
    asyncio.run(main(args))
