import argparse
import http
import re
from pathlib import Path

site_dir = Path('site')
src_js_pattern = re.compile(r'<script[^>]src="[^>]*"></script>')
extract_src_pattern = re.compile(r'<script[^>]src="([^>]*)"></script>')


def fill_js_element(html_content: str, base_path: Path):
    for js_element in src_js_pattern.findall(html_content):
        with Path(base_path, extract_src_pattern.findall(js_element)[0]).open(mode='r', encoding='utf-8') as js_file:
            html_content = html_content.replace(js_element, '<script>\n' + js_file.read() + '</script>')
    return html_content


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("hostname")

    for html_path in site_dir.glob("*.html"):
        with html_path.open(mode='r', encoding='utf-8') as f:
            connection = http.client.HTTPSConnection(parser.parse_args().hostname, port=8003)
            data = fill_js_element(f.read(), site_dir).encode('utf-8')
            print(data)
            connection.request('POST', '/PutTemporaryStorage?filename=test.html', body=data)
