from airium import Airium
from pathlib import Path
import time

output_dir = Path('opt')
output_dir.mkdir(parents=True, exist_ok=True)

def generate_index_html(user_classes: dict, user_class_to_href):
    a = Airium()
    a('<!DOCTYPE html>')
    with a.html(lang="zh-Hans"):
        with a.head():
            a.meta(charset="utf-8")
            a.title(_t='ibuprofen ' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        with a.body():
            for user_class in user_classes:
                with a.p():
                    with a.a(href=user_class_to_href(user_class)):
                        a(user_class.name)
    return str(a)

def generate_user_class_html(user_class):
    a = Airium()
    a('<!DOCTYPE html>')
    with a.html(lang="zh-Hans"):
        with a.head():
            a.meta(charset="utf-8")
            a.title(_t=user_class.name)
        with a.body():
            for record in reversed(user_class.lesson_schedules):
                if not 'title' in record:
                    continue
                with a.p():
                    a(record['title'])
                    with a.i(style="font-size:3px;"):
                        a(record['guid'])
                if not 'file_resources' in record:
                    continue
                for resource in record['file_resources']:
                    if not 'fileURI' in resource:
                        continue
                    with a.a(href=resource['fileURI']):
                        a(resource['title'])
                    a.br()
    return str(a)
