import os
import re
import yaml
import requests
from distutils.version import LooseVersion

# 基本配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.yaml')
SYNC_FILE = os.path.join(BASE_DIR, 'sync.yaml')
CUSTOM_SYNC_FILE = os.path.join(BASE_DIR, 'custom_sync.yaml')


def is_exclude_tag(tag):
    """
    排除tag
    :param tag:
    :return:
    """
    excludes = ['alpha', 'beta', 'rc', 'dev', 'test', 'amd64', 'ppc64le', 'arm64', 'arm', 's390x', 'SNAPSHOT', 'debug', 'master', 'latest', 'main']

    for e in excludes:
        if e.lower() in tag.lower():
            return True
        if str.isalpha(tag):
            return True
        if len(tag) >= 40:
            return True
        
    # 处理带有 - 字符的 tag
    if re.search("-\d$", tag, re.M | re.I):
        return False
    # v20231011-8b53cabe0
    if re.search("-\w{9}", tag, re.M | re.I):
        return False
    if '-' in tag:
        return True
    
    return False


def get_repo_aliyun_tags(image):
    """
    获取 aliyuncs repo 最新的 tag
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


def get_repo_gcr_tags(image, limit=5, host="k8s.gcr.io"):
    """
    获取 gcr.io repo 最新的 tag
    :param host:
    :param image:
    :param limit:
    :return:
    """

    hearders = {
        'User-Agent': 'docker/19.03.12 go/go1.13.10 git-commit/48a66213fe kernel/5.8.0-1.el7.elrepo.x86_64 os/linux arch/amd64 UpstreamClient(Docker-Client/19.03.12 \(linux\))'
    }

    tag_url = "https://{host}/v2/{image}/tags/list".format(host=host, image=image)

    tags = []
    tags_data = []
    manifest_data = []

    try:
        tag_rep = requests.get(url=tag_url, headers=hearders)
        tag_req_json = tag_rep.json()
        manifest_data = tag_req_json['manifest']
    except Exception as e:
        print('[Get tag Error]', e)
        return tags

    for manifest in manifest_data:
        sha256_data = manifest_data[manifest]
        sha256_tag = sha256_data.get('tag', [])
        if len(sha256_tag) > 0:
            # 排除 tag
            if is_exclude_tag(sha256_tag[0]):
                continue
            tags_data.append({
                'tag': sha256_tag[0],
                'timeUploadedMs': sha256_data.get('timeUploadedMs')
            })
    tags_sort_data = sorted(tags_data, key=lambda i: i['timeUploadedMs'], reverse=True)

    # limit tag
    tags_limit_data = tags_sort_data[:limit]

    image_aliyun_tags = get_repo_aliyun_tags(image)
    for t in tags_limit_data:
        # 去除同步过的
        if t['tag'] in image_aliyun_tags:
            continue

        tags.append(t['tag'])

    print('[repo tag]', tags)
    return tags


def get_repo_quay_tags(image, limit=5):
    """
    获取 quay.io repo 最新的 tag
    :param image:
    :param limit:
    :return:
    """

    hearders = {
        'User-Agent': 'docker/19.03.12 go/go1.13.10 git-commit/48a66213fe kernel/5.8.0-1.el7.elrepo.x86_64 os/linux arch/amd64 UpstreamClient(Docker-Client/19.03.12 \(linux\))'
    }

    tag_url = "https://quay.io/api/v1/repository/{image}/tag/?onlyActiveTags=true&limit=100".format(image=image)

    tags = []
    tags_data = []
    manifest_data = []

    try:
        tag_rep = requests.get(url=tag_url, headers=hearders)
        tag_req_json = tag_rep.json()
        manifest_data = tag_req_json['tags']
    except Exception as e:
        print('[Get tag Error]', e)
        return tags

    for manifest in manifest_data:
        name = manifest.get('name', '')

        # 排除 tag
        if is_exclude_tag(name):
            continue

        tags_data.append({
            'tag': name,
            'start_ts': manifest.get('start_ts')
        })

    tags_sort_data = sorted(tags_data, key=lambda i: i['start_ts'], reverse=True)

    # limit tag
    tags_limit_data = tags_sort_data[:limit]

    image_aliyun_tags = get_repo_aliyun_tags(image)
    for t in tags_limit_data:
        # 去除同步过的
        if t['tag'] in image_aliyun_tags:
            continue

        tags.append(t['tag'])

    print('[repo tag]', tags)
    return tags


def get_repo_elastic_tags(image, limit=5):
    """
    获取 elastic.io repo 最新的 tag
    :param image:
    :param limit:
    :return:
    """
    token_url = "https://docker-auth.elastic.co/auth?service=token-service&scope=repository:{image}:pull".format(
        image=image)
    tag_url = "https://docker.elastic.co/v2/{image}/tags/list".format(image=image)

    tags = []
    tags_data = []
    manifest_data = []

    hearders = {
        'User-Agent': 'docker/19.03.12 go/go1.13.10 git-commit/48a66213fe kernel/5.8.0-1.el7.elrepo.x86_64 os/linux arch/amd64 UpstreamClient(Docker-Client/19.03.12 \(linux\))'
    }

    try:
        token_res = requests.get(url=token_url, headers=hearders)
        token_data = token_res.json()
        access_token = token_data['token']
    except Exception as e:
        print('[Get repo token]', e)
        return tags

    hearders['Authorization'] = 'Bearer ' + access_token

    try:
        tag_rep = requests.get(url=tag_url, headers=hearders)
        tag_req_json = tag_rep.json()
        manifest_data = tag_req_json['tags']
    except Exception as e:
        print('[Get tag Error]', e)
        return tags

    for tag in manifest_data:
        # 排除 tag
        if is_exclude_tag(tag):
            continue
        tags_data.append(tag)

    tags_sort_data = sorted(tags_data, key=LooseVersion, reverse=True)

    # limit tag
    tags_limit_data = tags_sort_data[:limit]

    image_aliyun_tags = get_repo_aliyun_tags(image)
    for t in tags_limit_data:
        # 去除同步过的
        if t in image_aliyun_tags:
            continue

        tags.append(t)

    print('[repo tag]', tags)
    return tags


def get_repo_ghcr_tags(image, limit=5):
    """
    获取 ghcr.io repo 最新的 tag
    :param image:
    :param limit:
    :return:
    """
    token_url = "https://ghcr.io/token?service=ghcr.io&scope=repository:{image}:pull".format(
        image=image)

    tag_url = "https://ghcr.io/v2/{image}/tags/list".format(image=image)

    tags = []
    tags_data = []

    hearders = {
        'User-Agent': 'docker/19.03.12 go/go1.13.10 git-commit/48a66213fe kernel/5.8.0-1.el7.elrepo.x86_64 os/linux arch/amd64 UpstreamClient(Docker-Client/19.03.12 \(linux\))'
    }

    try:
        token_res = requests.get(url=token_url, headers=hearders)
        token_data = token_res.json()
        print("token_data", token_url, token_data)
        access_token = token_data['token']
    except Exception as e:
        print('[Get repo token]', e)
        return tags

    hearders['Authorization'] = 'Bearer ' + access_token

    try:
        tag_rep = requests.get(url=tag_url, headers=hearders)
        tag_req_json = tag_rep.json()
        manifest_data = tag_req_json['tags']
    except Exception as e:
        print('[Get tag Error]', e)
        return tags

    for tag in manifest_data:
        # 排除 tag
        if is_exclude_tag(tag):
            continue
        tags_data.append(tag)

    tags_sort_data = sorted(tags_data, key=LooseVersion, reverse=True)

    # limit tag
    tags_limit_data = tags_sort_data[:limit]

    image_aliyun_tags = get_repo_aliyun_tags(image)
    for t in tags_limit_data:
        # 去除同步过的
        if t in image_aliyun_tags:
            continue

        tags.append(t)

    print('[repo tag]', tags)
    return tags


def get_docker_io_tags(image, limit=5):
    hearders = {
        'User-Agent':
        'docker/19.03.12 go/go1.13.10 git-commit/48a66213fe kernel/5.8.0-1.el7.elrepo.x86_64 os/linux arch/amd64 UpstreamClient(Docker-Client/19.03.12 \(linux\))'
    }
    namespace_image = image.split('/')
    tag_url = "https://hub.docker.com/v2/namespaces/{username}/repositories/{image}/tags".format(
        username=namespace_image[0], image=namespace_image[1])
    print(tag_url)

    tags = []
    tags_data = []
    manifest_data = []

    try:
        tag_rep = requests.get(url=tag_url, headers=hearders)
        tag_req_json = tag_rep.json()
        manifest_data = tag_req_json['results']
    except Exception as e:
        print('[Get tag Error]', e)
        return tags
    for tag in manifest_data:
        name = tag.get('name', '')

        # 排除 tag
        if is_exclude_tag(name):
            continue

        tags_data.append(name)

    tags_sort_data = sorted(tags_data, key=LooseVersion, reverse=True)

    # limit tag
    tags_limit_data = tags_sort_data[:limit]

    image_aliyun_tags = get_repo_aliyun_tags(namespace_image[1])
    for t in tags_limit_data:
        # 去除同步过的
        if t in image_aliyun_tags:
            continue

        tags.append(t)
    return tags


def get_repo_tags(repo, image, limit=5):
    """
    获取 repo 最新的 tag
    :param repo:
    :param image:
    :param limit:
    :return:
    """
    tags_data = []
    if repo == 'gcr.io':
        tags_data = get_repo_gcr_tags(image, limit, "gcr.io")
    elif repo == 'k8s.gcr.io':
        tags_data = get_repo_gcr_tags(image, limit, "k8s.gcr.io")
    elif repo == 'registry.k8s.io':
        tags_data = get_repo_gcr_tags(image, limit, "registry.k8s.io")
    elif repo == 'quay.io':
        tags_data = get_repo_quay_tags(image, limit)
    elif repo == 'docker.elastic.co':
        tags_data = get_repo_elastic_tags(image, limit)
    elif repo == 'ghcr.io':
        tags_data = get_repo_ghcr_tags(image, limit)
    elif repo == "docker.io":
        tags_data = get_docker_io_tags(image, limit)
    return tags_data


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
        if config['images'][repo] is None:
            continue
        for image in config['images'][repo]:
            print("[image] {image}".format(image=image))
            sync_tags = get_repo_tags(repo, image, config['last'])
            if len(sync_tags) > 0:
                skopeo_sync_data[repo]['images'][image] = sync_tags
               # skopeo_sync_data[repo]['images'][image].append('latest')
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
        if custom_sync_config[repo]['images'] is None:
            continue
        for image in custom_sync_config[repo]['images']:
            image_aliyun_tags = get_repo_aliyun_tags(image)
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
