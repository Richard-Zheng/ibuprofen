import asyncio
import aiohttp
import hashlib
import json
import argparse
from pathlib import Path
from airium import Airium
import xml.etree.ElementTree as ET

import soap
import config

data_dir = Path('data')
output_dir = Path('opt')
data_dir.mkdir(parents=True, exist_ok=True)
output_dir.mkdir(parents=True, exist_ok=True)

class User:
    def __init__(self, session: aiohttp.ClientSession, uid: str, soap_url: str, user_classes: list):
        self.session = session
        self.uid = uid
        self.soap_url = soap_url
        self.user_classes = user_classes
        self.data_path = Path(data_dir, 'user_'+self.uid+'.txt')
        self.index_html_path = Path(output_dir, 'index.html')

    def generate_index_html(self):
        a = Airium()
        a('<!DOCTYPE html>')
        with a.html(lang="zh-Hans"):
            with a.head():
                a.meta(charset="utf-8")
                a.title(_t='ibuprofen')
            with a.body():
                for user_class in self.user_classes:
                    with a.p():
                        with a.a(href='user_class_' + user_class.guid  + '.html'):
                            a(user_class.name)
        return str(a)

    def generate_all_html(self):
        with self.index_html_path.open(mode='w', encoding='utf-8') as f:
            f.write(self.generate_index_html())
        for c in self.user_classes:
            with c.html_path.open(mode='w', encoding='utf-8') as f:
                f.write(c.generate_html())

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
        self.html_path = Path(output_dir, 'user_class_'+self.guid+'.html')

    def generate_html(self):
        a = Airium()
        a('<!DOCTYPE html>')
        with a.html(lang="zh-Hans"):
            with a.head():
                a.meta(charset="utf-8")
                a.title(_t=self.name)
            with a.body():
                for record in reversed(self.lessons_schedules):
                    if not 'title' in record:
                        continue
                    with a.p():
                        a(record['title'])
                        with a.i(style="font-size:3px;"):
                            a(record['guid'])
                    for resource in record['RefrenceResource']:
                        if not 'fileURI' in resource:
                            continue
                        with a.a(href=resource['fileURI']):
                            a(resource['title'])
                        a.br()
        return str(a)

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
        #user = await get_user(session, username[0], 'https://{0}/wmexam/wmstudyservice.WSDL'.format(username[1]))
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
        user.generate_all_html()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("username", help="full username")
    parser.add_argument("-p", "--password", help="password (123456 by default)")
    args = parser.parse_args()
    asyncio.run(main(args))
