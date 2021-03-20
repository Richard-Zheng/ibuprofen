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

    async def fetch(action, param):
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
            root[1][0][0][0][0].attrib.update(lesson_schedule)
            attr = root[1][0][0][0][0].attrib
        except:
            return

        file_resources = attr['file_resources'] = []
        for ref in root[1][0][0][0][0][2]:
            result = await soap.fetch(self.session, self.soap_url, 'GetResourceByGUID', {
                'lpszResourceGUID': ref.attrib['guid']
            })
            try:
                content = ET.fromstring(html.unescape(result))[1][0][0][0][0][2].attrib
            except:
                continue
            file_resources.append({'guid': ref.attrib['guid'],'title': ref.attrib['title'],'fileURI': content['fileURI']})
        return attr

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
    def __init__(self, session, guid, name, uid, soap_url):
        self.session = session
        self.guid = guid
        self.uid = uid
        self.soap_url = soap_url
        self.name = name

    def get_data_path(self):
        return Path(data_dir, 'user_class_'+self.guid+'.txt')

    async def fetch_lessons_schedules(self):
        p = self.get_data_path()
        if p.exists():
            with p.open(mode='r') as f:
                self.lessons_schedules = json.load(f)
        else:
            self.lessons_schedules = []
        await self.pull_new_schedule_records()
        with p.open(mode='w') as f:
            json.dump(self.lessons_schedules, f)

    async def pull_new_schedule_records(self):
        response = {'hasMoreData': 'true'}
        szReturnXML = generate_szReturnXML(self.lessons_schedules)
        tasks = []
        while response['hasMoreData'] == 'true':
            response = await self.get_lessons_schedule_table_data(szReturnXML)
            new_lessons_schedules = response['Record']
            szReturnXML += generate_szReturnXML(new_lessons_schedules)
            for schedule in new_lessons_schedules:
                tasks.append(asyncio.get_running_loop().create_task(self.get_lessons_schedule_details(schedule)))
            self.lessons_schedules += new_lessons_schedules
        if tasks:
            await asyncio.wait(tasks)

    async def get_lessons_schedule_details(self, schedule_record: dict):
        return_xml = await soap.request_for_text(self.session, self.soap_url, 'GetResourceByGUID', {
            'lpszResourceGUID': schedule_record['resourceguid']
        })
        if return_xml == '1168' or return_xml == '<Error code="1168" />':
            return
        root = ET.fromstring(return_xml)

        lesson_attr = root[0].attrib
        del lesson_attr['guid']
        schedule_record.update(lesson_attr)

        tmp = []
        tasks = []
        for resource_tag in root[0][2]:
            tasks.append(asyncio.get_running_loop().create_task(self.get_refrence_resource_details(resource_tag.attrib)))
            tmp.append(resource_tag.attrib)
        if tasks:
            await asyncio.wait(tasks)
        schedule_record['RefrenceResource'] = tmp
        return schedule_record

    async def get_refrence_resource_details(self, refrence_resource):
        result = await soap.fetch(self.session, self.soap_url, 'GetResourceByGUID', {
            'lpszResourceGUID': refrence_resource['guid']
        })
        try:
            root = ET.fromstring(ET.fromstring(result)[1][0][0].text)
            refrence_resource.update(root[0].find('Content').attrib)
        except:
            return

    async def get_lessons_schedule_table_data(self, szReturnXML):
        root = ET.fromstring(await soap.request_for_text(self.session, self.soap_url, 'LessonsScheduleGetTableData',{
            'lpszTableName': 'lessonsschedule',
            'lpszUserClassGUID': self.guid,
            'lpszStudentID': self.uid,
            'lpszLastSyncTime': '',
            'szReturnXML': 'enablesegment=3;' + szReturnXML,
        }))
        result_dict = root.attrib
        tmp = []
        for record in root:
            tmp.append({
                'guid': record.find('guid').text,
                'resourceguid': record.find('resourceguid').text,
                'syn_timestamp': record.find('syn_timestamp').text,
            })
        result_dict['Record'] = tmp
        return result_dict

def generate_szReturnXML(records):
    szReturnXML = ''
    for record in records:
        szReturnXML += record['guid'] + '=' + record['syn_timestamp'] + ';'
    return szReturnXML

async def main(args):
    async with aiohttp.ClientSession() as session:
        username = args.username.split('@')
        us = UserSession(session, username[0], 'https://{0}/wmexam/wmstudyservice.WSDL'.format(username[1]))
        await us.get_lesson_schedule({"guid": "bb820850d0304944ad1113375db8f81e", "resourceguid": "b02d4d3b71d7407abfe34292976c524e", "syn_timestamp": "2019-04-10 20:45:53"})
        '''#user = await get_user(session, username[0], 'https://{0}/wmexam/wmstudyservice.WSDL'.format(username[1]))
        user = await login(
            session,
            username[0],
            'https://{0}/wmexam/wmstudyservice.WSDL'.format(username[1]),
            args.password if args.password else '123456',
        )
        tasks = []
        for c in user.user_classes:
            tasks.append(asyncio.create_task(c.fetch_lessons_schedules()))
        await asyncio.wait(tasks)
        export.StaticHtmlGenerator(user).generate_all_html()'''

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("username", help="full username")
    parser.add_argument("-p", "--password", help="password (123456 by default)")
    args = parser.parse_args()
    asyncio.run(main(args))
