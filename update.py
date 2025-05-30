import json
import os
import random
import re
import time
from itertools import product

import requests
from github import Github
from lxml import html

user_agents_file_name = 'user-agents.json'
user_agents_file_path = os.path.join(
    os.path.dirname(__file__), user_agents_file_name)

_os_field_include_patterns = [
    re.compile(r'^windows nt \d+\.\d+$', flags=re.IGNORECASE),
    re.compile(r'^macintosh$', flags=re.IGNORECASE),
    re.compile(r'^linux (x86_64|i686)$', flags=re.IGNORECASE),
]
_os_field_exclude_patterns = [
    re.compile(r'\bwindows mobile\b', flags=re.IGNORECASE),
    re.compile(r'\bxbox\b', flags=re.IGNORECASE),
    re.compile(r'\biphone\b', flags=re.IGNORECASE),
    re.compile(r'\bipad\b', flags=re.IGNORECASE),
    re.compile(r'\bipod\b', flags=re.IGNORECASE),
    re.compile(r'\bandroid\b', flags=re.IGNORECASE),
]

_saved_user_agents = None


def get_saved_user_agents():
    global _saved_user_agents

    if _saved_user_agents is None:
        with open(user_agents_file_path, 'r') as f:
            _saved_user_agents = json.load(f)

    return _saved_user_agents


def get_latest_user_agents():
    user_agents = []
    base_url = 'https://www.whatismybrowser.com/guides/the-latest-user-agent/'
    session = requests.Session()
    session.get('https://www.whatismybrowser.com')
    for browser in ('chrome', 'firefox', 'safari', 'edge'):
        time.sleep(1)
        response = session.get(
            ''.join((base_url, browser)),
            headers={'User-Agent': get_saved_user_agents()[-1]},
        )
        if response.status_code >= 400:
            print(response.text)
            response.raise_for_status()

        elems = html.fromstring(response.text).cssselect('td li span.code')

        browser_uas = []
        for elem in elems:
            ua = elem.text_content().strip()
            if not ua.startswith('Mozilla/5.0 ('):
                continue
            browser_uas.append(ua)

        for ua in browser_uas:
            os_type = ua[len('Mozilla/5.0 ('):ua.find(')')].lower()
            os_fields = [p.strip() for p in os_type.split(';')]

            if any(p.match(f) for p, f in product(
                    _os_field_exclude_patterns, os_fields)):
                continue

            if any(p.match(f) for p, f in product(
                    _os_field_include_patterns, os_fields)):
                user_agents.append(ua)

    return user_agents


def json_dump(obj):
    return json.dumps(obj, indent=4).strip() + '\n'


def update_files_on_github(new_user_agents_json):
    gh = Github(os.environ['GITHUB_TOKEN'])
    repo = gh.get_repo(os.environ['GITHUB_REPOSITORY'])
    branch='main'
    f = repo.get_contents(user_agents_file_name, ref=branch)
    repo.update_file(
        f.path,
        message=f'Update {user_agents_file_name} on {branch} branch',
        content=new_user_agents_json,
        sha=f.sha,
        branch=branch,
    )


if __name__ == '__main__':
    old_user_agents = get_saved_user_agents()
    old_user_agents_json = json_dump(old_user_agents)
    print(f'old_user_agents = {old_user_agents_json}')
    assert len(old_user_agents) >= 4

    new_user_agents = get_latest_user_agents()
    new_user_agents_json = json_dump(new_user_agents)
    print(f'new_user_agents = {new_user_agents_json}')
    assert len(new_user_agents) >= 4

    if old_user_agents_json != new_user_agents_json:
        update_files_on_github(new_user_agents_json)