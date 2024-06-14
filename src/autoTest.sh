#!/bin/bash
# check 环境是否满足要求
source ./env.sh

echo $VERSION
g_remote=1

# 定义函数
kill_sure() {
  local program_name=$1
  local wait_time=$2
  local interval=1
  local elapsed_time=0

  # 检查参数是否传入
  if [[ -z "$program_name" || -z "$wait_time" ]]; then
    echo "Usage: kill_sure program_name wait_time"
    exit 1
  fi

  # 使用ps和grep获取进程PID并杀死进程
  pids=$(ps aux | grep "$program_name" | grep -v grep | awk '{print $2}')
  if [[ -z "$pids" ]]; then
    echo "No process named $program_name found."
    exit 1
  fi

  for pid in $pids; do
    kill -9 "$pid"
  done

  # 不断循环等待进程结束
  while pgrep "$program_name" > /dev/null; do
    sleep $interval
    elapsed_time=$((elapsed_time + interval))

    # 检查是否超时
    if [ "$elapsed_time" -ge "$wait_time" ]; then
      echo "Error: Timeout after waiting $wait_time seconds for $program_name to terminate."
      exit 1
    fi
  done

  echo "$program_name terminated successfully."
}

check() {
  if ! command -v sshpass &> /dev/null; then
    echo "sshpass is not installed. Please install it and try again."
    exit 1
  fi

  rm -rf "$ROOT"
  mkdir -p "$ROOT" "$PKG_DIR" "$PKG_PATH"
  cp -rf "$WORK_DIR/mml" "$ROOT/"
}

judge_quit(){
  if [ $? -ne 0 ]; then
    exit 1
  fi
}

# change_option函数
change_option() {
    local config_file=$1
    local key=$2
    local val=$3

    # 使用sed命令修改配置文件中的键值对
    sed -i -E "s/^(${key} *= *).*/\1${val}/" "$config_file" 
    judge_quit
}
# 示例调用方法
# change_option "GNB_TTI_TRACE_COMM_MODE" "1"
# change_option "GNB_TTI_TRACE_TIMER_CFG_DURATION" "2000"


# 查看msg 中是否包含某些值
runMml() {
    cmds=$1
    result=$($MML_TOOL_PATH/mmlshell -c "$cmds")
    echo "$result"
}

load_mml() {
    local configfile=$1
    local cmds
    local result

    # 检查配置文件是否存在
    if [[ -f "$configfile" ]]; then
        # 使用cat命令将文件内容加载到cmds变量中
        cmds=$(cat "$configfile")
    else
        echo "$configfile does not exist. Exiting."
        exit 1
    fi

    # 执行所有命令并捕获输出
    result=$(runMml "$cmds")
    echo "$result" > $WORK_DIR/cmd.log
    echo "$result"

    # 返回执行结果
    return 0
}


# 参数处理
for arg in "$@"; do
  case $arg in
    --version=*)
      VERSION="${arg#*=}"
      shift
      ;;
    --mmlfile=*)
      MML_SCRIPT="${arg#*=}"
      shift
      ;;
    --model=*)
      MODEL="${arg#*=}"
      if [[ "$MODEL" != "cpri" && "$MODEL" != "ecpri" && "$MODEL" != "docsis" ]]; then
        echo "Invalid model: $MODEL. Allowed values are cpri, ecpri, docsis."
        exit 1
      fi
      MML_SCRIPT="$ROOT/mml/${MODEL}-test.txt"
      shift
      ;;    
    --local)
      g_remote=0
      shift
      ;;
    --paswd=*)
      CI_PASS="${arg#*=}"
      shift
      ;;
    --vlan=*)
      VLAN="${arg#*=}"
      shift
      ;;
    upgrade)
      ACTION="upgrade"
      shift
      ;;
    startup)
      ACTION="startup"
      shift
      ;;
    *)
      echo "Invalid argument: $arg"
      exit 1
      ;;
  esac
done

if [[ -z "$ACTION" ]]; then
  echo "No action specified. Use 'upgrade' or 'startup'."
  exit 1
fi



case $ACTION in
  upgrade)
    # 准备环境
    check
    # 下载镜像
    if [[ $g_remote -eq 1 ]]; then
      sshpass -p $CI_PASS scp $SSHOPT "$CI_USER@$CI_IP:$REMOTE_PKG" "$PKG_DIR"
      if [ $? -ne 0 ]; then
        curl -o "$PKG_NAME" "$CURL_URL"
        if [ $? -ne 0 ]; then
          git clone $GIT_URL
        else 
          echo "镜像获取失败"
          exit 1
        fi
      fi
    fi

    rm -rf $PKG_PATH
    tar -xf "$PKG_DIR/$UNZIP_PKG_NAME" -C "$PKG_DIR" || exit 1

    if [[ ! -d "$PKG_PATH" ]]; then
      echo "$PKG_PATH does not exist. Exiting."
      exit 1
    fi

    echo "镜像已获取。"
    ;;
  startup)
    # before start
    if [[ "$MODEL" == "ecpri" ]]; then
      change_option $CONFIG_FILE_TTI GNB_SREF_SSB_MAX_TX_POWER -22
    fi
    echo "Running startup actions..."
    ### check and kill
    kill_sure startup.sh 5
    # start
    nohup bash "$INIT_SCRIPT" > $WORK_DIR/startup.log 2>&1 &

    # after start
    ## load mml config
    cd "$MML_TOOL_PATH"
    load_mml $MML_SCRIPT

    case "$MODEL" in
      ecpri)
        echo "Processing ecpri model specific configurations..."
        # Add ecpri specific configuration commands here
        ;;
      *)
        echo "No additional configuration needed for model: $MODEL"
        ;;
    esac

    echo "Configuration completed."
    ;;
  *)
    echo "Invalid action: $ACTION"
    exit 1
    ;;
esac

