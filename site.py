import argparse
import asyncio
import os.path
import re
from pathlib import Path

import aiohttp

site_dir = Path('site')
src_js_pattern = re.compile(r'<script[^>]src="[^>]*"></script>')
extract_src_pattern = re.compile(r'<script[^>]src="([^>]*)"></script>')


def fill_js_element(html_content: str, base_path: Path):
    for js_element in src_js_pattern.findall(html_content):
        with Path(base_path, extract_src_pattern.findall(js_element)[0]).open(mode='r', encoding='utf-8') as js_file:
            html_content = html_content.replace(js_element, '<script>\n' + js_file.read() + '</script>')
    return html_content


async def upload_to_temp_storage(session, url, data):
    async with session.post(url, data=data) as response:
        return await response.text()


async def main(args):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for html_path in site_dir.glob("*.html"):
            with html_path.open(mode='r', encoding='utf-8') as f:
                filename = os.path.split(f.name)[1]
                url = 'https://{0}:{1}/PutTemporaryStorage?filename={2}'.format(args.hostname, args.port, filename)
                tasks.append(asyncio.create_task(session.post(url, data=fill_js_element(f.read(), site_dir).encode('utf-8'))))
        await asyncio.wait(tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("hostname")
    parser.add_argument("-p", "--port", default='8003')
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(args))
