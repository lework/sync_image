#!/bin/bash


hub="registry.cn-hangzhou.aliyuncs.com"
repo="$hub/kainstall"


if [ -f sync.yaml ]; then
   echo "[Start] sync......."
   cat sync.yaml custom_sync.yaml
   sudo /tmp/skopeo login -u ${HUB_USERNAME} -p ${HUB_PASSWORD} ${hub} \
   && sudo /tmp/skopeo --insecure-policy sync -a --src yaml --dest docker sync.yaml $repo \
   && sudo /tmp/skopeo --insecure-policy sync -a --src yaml --dest docker custom_sync.yaml $repo
   
   echo "[End] done."
   
else
    echo "[Error]not found sync.yaml!"
fi
