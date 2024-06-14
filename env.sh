#!/bin/bash
shopt -s expand_aliases

# 定义仓库地址
# export VERSION=2.0.11
export CI_IP="172.168.100.38"
export CI_USER="root"
export CI_PASS="123456"
export REMOTE_DIR="/home/liulanjia/CI/repo"
# cpri，ecpri ,docsis 三种模式
export MODEL="cpri"
export PKG_NAME=nrpackage
export PKG_ROOT=/mnt/data/verupg/test

export WORK_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export GIT_URL="git@172.168.100.29:product/gnbversion.git"
export CURL_URL="http://172.168.100.29/product/gnbversion/-/blob/main/V2.0.10/cpri-nrpackage-${VERSION}-centos8.tar.gz?ref_type=heads"

export UNZIP_PKG_NAME=""
export REMOTE_PKG="$REMOTE_DIR/$UNZIP_PKG_NAME"
# 包文件
export PKG_DIR="$PKG_ROOT/$MODEL"
export PKG_PATH="$PKG_ROOT/$MODEL/nrpackage"
export INIT_SCRIPT="$PKG_PATH/bu/startup.sh"
export MML_TOOL_PATH="$PKG_ROOT/mml/mmlshell"
export CONFIG_FILE_TTI="$PKG_PATH/bu/gNB/etc/gNodeB_TTITrace_Configuration.cfg"
# 可指定
export MML_SCRIPT="$PKG_ROOT/mml/$MODEL-test.txt"

SSHOPT="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

# 版本包：
# cpri-nrpackage-2.0.11-centos8.tar.gz  ecpri-nrpackage-2.0.11-centos8.tar.gz  onuloader-2.0.11.tar.gz

remote_cmd() {
  local IP=$CI_IP
  local PORT=22
  local CMD=$1
  local USER=$CI_USER
  local PASSWORD=$CI_PASS

  # 组合命令
  SSH_CMD="sshpass -p $PASSWORD ssh $SSHOPT -p $PORT $USER@$IP '$CMD; echo \$?'"

  # 使用 sshpass 执行命令并捕获输出
  OUTPUT=$(eval $SSH_CMD)
  
  # 分离命令输出和状态码
  CMD_STATUS=$(echo "$OUTPUT" | tail -n 1 | tr -d '\r')
  RESULT=$(echo "$OUTPUT" | sed '$d')

  # 设置全局变量 status
  if [ "$CMD_STATUS" -eq 0 ]; then
    cmd_status=0
  else
    cmd_status=$CMD_STATUS
  fi

  # 返回结果
  echo "$RESULT"
  return $CMD_STATUS
}

check_remote_pkg() {
  echo "Checking remote packages..."
  remote_pkg_list=$(remote_cmd "find $REMOTE_DIR -name '${MODEL}*'")
  echo "Remote package list: $remote_pkg_list"
  
  matching_pkg=$(echo "$remote_pkg_list" | grep "$PKG_NAME")
  echo "Matching package: $matching_pkg"

  if [ -n "$matching_pkg" ]; then
    export REMOTE_PKG=$matching_pkg
    export UNZIP_PKG_NAME=$(basename "$REMOTE_PKG")
    export VERSION=$(echo "$UNZIP_PKG_NAME" | awk -F '-' '{print $3}')
    echo "Package $REMOTE_PKG found on remote server with version $VERSION."
  else
    echo "Package ${PKG_NAME}-${MODEL} not found on remote server."
    exit 1
  fi
}

init_env(){
  check_remote_pkg
  export PKG_DIR="$PKG_ROOT/$MODEL"
  export PKG_PATH="$PKG_ROOT/$MODEL/nrpackage"
  export INIT_SCRIPT="$PKG_PATH/bu/startup.sh"
  export MML_TOOL_PATH="$PKG_ROOT/mml/mmlshell"
  export CONFIG_FILE_TTI="$PKG_PATH/bu/gNB/etc/gNodeB_TTITrace_Configuration.cfg"
}

init_env

