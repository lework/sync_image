import os
import yaml
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.yaml')
SYNC_FILE = os.path.join(BASE_DIR, 'sync.yaml')
CUSTOM_SYNC_FILE = os.path.join(BASE_DIR, 'custom_sync.yaml')

config = None
with open(CONFIG_FILE, 'r') as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
        exit(1)

print('[config]', config)


def get_aliyun_tags(image):
    image_name = image.split('/')[-1]
    hearders = {
        'User-Agent': 'docker/19.03.12 go/go1.13.10 git-commit/48a66213fe kernel/5.8.0-1.el7.elrepo.x86_64 os/linux arch/amd64 UpstreamClient(Docker-Client/19.03.12 \(linux\))'
    }
    token_url = "https://dockerauth.cn-hangzhou.aliyuncs.com/auth?scope=repository:kainstall/{image}:pull&service=registry.aliyuncs.com:cn-hangzhou:26842".format(
        image=image_name)
    token_res = requests.get(url=token_url, headers=hearders)
    token_data = token_res.json()
    access_token = token_data['token']
    tag_url = "https://registry.cn-hangzhou.aliyuncs.com/v2/kainstall/{image}/tags/list".format(image=image_name)
    hearders['Authorization'] = 'Bearer ' + access_token
    tag_res = requests.get(url=tag_url, headers=hearders)
    tag_data = tag_res.json()
    print('[aliyun tag]: ', tag_data)
    return tag_data.get('tags', [])


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
    # print(tag_release_list)

    minor_data = {}
    for tag in tag_release_list:
        tag_split = tag.split('.')
        try:
            t1 = tag_split[0]
        except Exception:
            t1 = ''
        try:
            t2 = tag_split[1]
        except Exception:
            t2 = ''
        try:
            t3 = tag_split[2]
        except Exception:
            t3 = ''
        key = t1 + '.' + t2
        try:
            t3 = int(t3)
        except Exception:
            continue
        if key not in minor_data:
            minor_data[key] = [t3]
        else:
            minor_data[key].append(t3)

    # print(minor_data)

    max_minor_list = []
    for i in minor_data:
        max_minor_list.append(i + '.' + str(max(minor_data[i])))

    # print(max_minor_list)

    max_minor_list.sort(key=lambda s: list(map(int, s.replace('v', '').split('.'))), reverse=True)
    new_tags = max_minor_list[:config['last']]
    print('[new tag]', new_tags)

    tags = []
    image_aliyun_tags = get_aliyun_tags(image)

    for tag in new_tags:
        if tag not in image_aliyun_tags:
            tags.append(tag)
    return tags


skopeo_sync_data = {}

for repo in config['images']:
    if repo not in skopeo_sync_data:
        skopeo_sync_data[repo] = {'images': {}}
    for image in config['images'][repo]:
        print("[image] {image}".format(image=image))
        sync_tags = get_tags(repo, image)
        if len(sync_tags) > 0:
            skopeo_sync_data[repo]['images'][image] = sync_tags
        else:
            print('[{image}] no sync tag.'.format(image=image))

print('[sync data]', skopeo_sync_data)

with open(SYNC_FILE, 'w+') as f:
    yaml.safe_dump(skopeo_sync_data, f, default_flow_style=False)




print()

custom_sync_config = None
with open(CUSTOM_SYNC_FILE, 'r') as stream:
    try:
        custom_sync_config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
        exit(1)

print('[custom_sync config]', custom_sync_config)

custom_skopeo_sync_data = {}

for repo in custom_sync_config:
    if repo not in custom_skopeo_sync_data:
        custom_skopeo_sync_data[repo] = {'images': {}}
    for image in custom_sync_config[repo]['images']:
        image_aliyun_tags = get_aliyun_tags(image)
        for tag in custom_sync_config[repo]['images'][image]:
            if tag in image_aliyun_tags:
                continue
            if image not in custom_skopeo_sync_data[repo]['images']:
                custom_skopeo_sync_data[repo]['images'][image] = [tag]
            else:
                custom_skopeo_sync_data[repo]['images'][image].append(tag)


print('[custom_sync data]', custom_skopeo_sync_data)

with open(CUSTOM_SYNC_FILE, 'w+') as f:
    yaml.safe_dump(custom_skopeo_sync_data, f, default_flow_style=False)
