import time
from pathlib import Path

from airium import Airium

pdf_convertable_exts = ["doc", "docx", "ppt", "pptx"]
index_to_subject_name = {
    "0": "语文",
    "1": "数学",
    "2": "英语",
    "3": "物理",
    "4": "化学",
    "5": "历史",
    "6": "地理",
    "7": "政治",
    "8": "生物",
    "100": "课外资源",
    "101": "课堂实录",
    "102": "重要通知",
}


def generate_index_html(user_classes: list, user_class_to_href):
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
            with a.div(id='subject-filter'):
                with a.label():
                    a.input(checked='checked', onchange='changeSubjectFilterAll(this.checked)', type='checkbox')
                    a("全选")
                for key in index_to_subject_name:
                    with a.label():
                        a.input(checked='checked', name='category', onchange='onSubjectCheckboxChange()', type='checkbox',
                                value=key)
                        a(index_to_subject_name[key])
            with a.div(id='user-login'):
                a.label(for_='user-id', _t='用户名:')
                a.input(id='user-id', type='text')
                a.input(onclick='login(document.getElementById("user-id").value)', type='submit', value='登录')
            with a.ul():
                for record in reversed(user_class.lesson_schedules):
                    if not 'title' in record:
                        continue

                    with a.li(klass='lesson-schedule', **{'data-subject': record['numberSubject']}):
                        a.p(klass='lesson-schedule-title', _t=record['title'])
                        if not 'file_resources' in record:
                            continue
                        with a.ul():
                            for resource in record['file_resources']:
                                if not 'fileURI' in resource:
                                    continue
                                with a.li(klass='resource', **{'data-guid': resource['guid']}):
                                    with a.a(href=resource['fileURI']):
                                        a(resource['title'])
                                    if resource['ext'] in pdf_convertable_exts:
                                        a.br()
                                        with a.i():
                                            with a.a(href=resource['fileURI'].replace(resource['ext'], 'pdf')):
                                                a('PDF')
                                    a.br()
                                    a.button(onclick='getAnswerSheet(this)', _t='答题卡')
            a.script(src='https://cdn.jsdelivr.net/gh/Richard-Zheng/ibuprofen/site/scripts/soap.js'):
            a.script(src='https://cdn.jsdelivr.net/gh/Richard-Zheng/ibuprofen/site/scripts/api.js'):
            a.script(src='https://cdn.jsdelivr.net/gh/Richard-Zheng/ibuprofen/site/scripts/user-class-page-script.js'):
    return str(a)
