import os
import yaml
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.yaml')
SYNC_FILE = os.path.join(BASE_DIR, 'sync.yaml')

config = None
with open(CONFIG_FILE, 'r') as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
        exit(1)

print(config)


def get_tags(repo, image):
    tag_url = "https://{repo}/v2/{image}/tags/list".format(repo=repo, image=image)
    tag_list = tag_release_list = []
    try:
        tag_rep = requests.get(url=tag_url)
        tag_req_json = tag_rep.json()
        tag_list = tag_req_json['tags']
    except Exception as e:
        print(e)

    for index, tag in enumerate(tag_list):
        if '-' not in tag:
            tag_release_list.append(tag)
    print(tag_release_list)

    minor_data = {}
    for tag in tag_release_list:
        t1, t2, t3 = tag.split('.')
        key = t1 + '.' + t2
        if key not in minor_data:
            minor_data[key] = [int(t3)]
        else:
            minor_data[key].append(int(t3))

    print(minor_data)

    max_minor_list = []
    for i in minor_data:
        max_minor_list.append(i + '.' + str(max(minor_data[i])))

    print(max_minor_list)

    max_minor_list.sort(key=lambda s: list(map(int, s.replace('v', '').split('.'))), reverse=True)

    return max_minor_list[:config['last']]



skopeo_sync_data = {}

for repo in config['images']:
    if repo not in skopeo_sync_data:
        skopeo_sync_data[repo] = {'images': {}}
    for image in config['images'][repo]:
        skopeo_sync_data[repo]['images'][image] = get_tags(repo, image)

print(skopeo_sync_data)

with open(SYNC_FILE, 'w+') as f:
    yaml.safe_dump(skopeo_sync_data, f, default_flow_style=False)
