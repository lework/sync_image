import os
import yaml
import requests

# 基本配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.yaml')
SYNC_FILE = os.path.join(BASE_DIR, 'sync.yaml')
CUSTOM_SYNC_FILE = os.path.join(BASE_DIR, 'custom_sync.yaml')


def get_aliyun_tags(image):
    """
    获取阿里云镜像最新的tag
    :param image:
    :return:
    """
    image_name = image.split('/')[-1]
    tags = []

    hearders = {
        'User-Agent': 'docker/19.03.12 go/go1.13.10 git-commit/48a66213fe kernel/5.8.0-1.el7.elrepo.x86_64 os/linux arch/amd64 UpstreamClient(Docker-Client/19.03.12 \(linux\))'
    }
    token_url = "https://dockerauth.cn-hangzhou.aliyuncs.com/auth?scope=repository:kainstall/{image}:pull&service=registry.aliyuncs.com:cn-hangzhou:26842".format(
        image=image_name)
    try:
        token_res = requests.get(url=token_url, headers=hearders)
        token_data = token_res.json()
        access_token = token_data['token']
    except Exception as e:
        print('[Get repo token]', e)
        return tags

    tag_url = "https://registry.cn-hangzhou.aliyuncs.com/v2/kainstall/{image}/tags/list".format(image=image_name)
    hearders['Authorization'] = 'Bearer ' + access_token

    try:
        tag_res = requests.get(url=tag_url, headers=hearders)
        tag_data = tag_res.json()
        print('[aliyun tag]: ', tag_data)
    except Exception as e:
        print('[Get tag Error]', e)
        return tags

    tags = tag_data.get('tags', [])
    return tags


def get_repo_tags(repo, image, limit=5):
    """
    获取 repo 最新的 tag
    :param repo:
    :param image:
    :param limit:
    :return:
    """
    tag_url = "https://{repo}/v2/{image}/tags/list".format(repo=repo, image=image)

    tags = []
    tags_data = []
    manifest_data = []

    try:
        tag_rep = requests.get(url=tag_url)
        tag_req_json = tag_rep.json()
        manifest_data = tag_req_json['manifest']
    except Exception as e:
        print('[Get tag Error]', e)
        return tags

    for manifest in manifest_data:
        sha256_data = manifest_data[manifest]
        sha256_tag = sha256_data.get('tag', [])
        if len(sha256_tag) > 0:
            tags_data.append({
                'tag': sha256_tag[0],
                'timeUploadedMs': sha256_data.get('timeUploadedMs')
            })
    tags_sort_data = sorted(tags_data, key=lambda i: i['timeUploadedMs'], reverse=True)

    # limit tag
    tags_limit_data = tags_sort_data[:limit]

    image_aliyun_tags = get_aliyun_tags(image)
    for t in tags_limit_data:
        # 去除同步过的
        if t['tag'] in image_aliyun_tags:
            continue
        # 去除 alpha
        if 'alpha' in t['tag']:
            continue
        # 去除 beta
        if 'beta' in t['tag']:
            continue
        # 去除 rc
        if 'rc' in t['tag']:
            continue
        tags.append(t['tag'])

    print('[repo tag]', tags)
    return tags


def generate_dynamic_conf():
    """
    生成动态同步配置
    :return:
    """

    print('[generate_dynamic_conf] start.')
    config = None
    with open(CONFIG_FILE, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            print('[Get Config]', e)
            exit(1)

    print('[config]', config)

    skopeo_sync_data = {}

    for repo in config['images']:
        if repo not in skopeo_sync_data:
            skopeo_sync_data[repo] = {'images': {}}
        for image in config['images'][repo]:
            print("[image] {image}".format(image=image))
            sync_tags = get_repo_tags(repo, image, config['last'])
            if len(sync_tags) > 0:
                skopeo_sync_data[repo]['images'][image] = sync_tags
            else:
                print('[{image}] no sync tag.'.format(image=image))

    print('[sync data]', skopeo_sync_data)

    with open(SYNC_FILE, 'w+') as f:
        yaml.safe_dump(skopeo_sync_data, f, default_flow_style=False)

    print('[generate_dynamic_conf] done.', end='\n\n')



def generate_custom_conf():
    """
    生成自定义的同步配置
    :return:
    """

    print('[generate_custom_conf] start.')
    custom_sync_config = None
    with open(CUSTOM_SYNC_FILE, 'r') as stream:
        try:
            custom_sync_config = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            print('[Get Config]', e)
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

    print('[generate_custom_conf] done.', end='\n\n')


generate_dynamic_conf()
generate_custom_conf()
