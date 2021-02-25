import aiohttp
import asyncio
import xml.etree.ElementTree as ET

async def fetch(session, soap_url, action, param):
    async with session.post(soap_url, headers={
        'User-Agent': 'ksoap2-android/2.6.0+',
        'SOAPAction': 'http://webservice.myi.cn/wmstudyservice/wsdl/' + action,
        'Content-Type': 'text/xml;charset=utf-8',
        'Cookie': 'userguid=ffffffffffffffffffffffffffffffff;username=paduser;usergroupguid=ffffffffffffffffffffffffffffffff',
        'Accept-Encoding': 'gzip'
    }, data=param_to_request_body(action, param)) as response:
        return await response.text()

async def request_for_text(session, soap_url, action, param):
    return ET.fromstring(await fetch(session, soap_url, action, param))[1][0][0].text

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
