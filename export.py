from airium import Airium
from pathlib import Path

from user import User, UserClass

output_dir = Path('opt')
output_dir.mkdir(parents=True, exist_ok=True)

class StaticHtmlGenerator:
    def __init__(self, user: User):
        self.user = user
        self.index_html_path = Path(output_dir, 'index.html')

    @classmethod
    def get_user_class_html_path(clz, user_class: UserClass):
        return Path(output_dir, 'user_class_'+user_class.guid+'.html')

    def generate_all_html(self):
        with self.index_html_path.open(mode='w', encoding='utf-8') as f:
            f.write(generate_index_html(self.user))
        for c in self.user.user_classes:
            with self.get_user_class_html_path(c).open(mode='w', encoding='utf-8') as f:
                f.write(generate_html(c))

def generate_index_html(user: User):
    a = Airium()
    a('<!DOCTYPE html>')
    with a.html(lang="zh-Hans"):
        with a.head():
            a.meta(charset="utf-8")
            a.title(_t='ibuprofen')
        with a.body():
            for user_class in user.user_classes:
                with a.p():
                    with a.a(href='user_class_' + user_class.guid  + '.html'):
                        a(user_class.name)
    return str(a)

def generate_html(user_class: UserClass):
    a = Airium()
    a('<!DOCTYPE html>')
    with a.html(lang="zh-Hans"):
        with a.head():
            a.meta(charset="utf-8")
            a.title(_t=user_class.name)
        with a.body():
            for record in reversed(user_class.lessons_schedules):
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
