import os
import argparse
import shutil
from draw import DrawioParser

def check_files(script_dir, script_required_files, current_dir_required_files):
    # 检查脚本目录中的文件是否存在
    missing_script_files = [f for f in script_required_files if not os.path.isfile(os.path.join(script_dir, f))]

    # 检查当前工作目录中的文件是否存在
    missing_current_dir_files = [f for f in current_dir_required_files if not os.path.isfile(f)]

    if not missing_script_files and not missing_current_dir_files:
        print("All required files are present.")
    else:
        if missing_script_files:
            print("Missing script directory files: ", missing_script_files)
        if missing_current_dir_files:
            print("Missing current directory files: ", missing_current_dir_files)

def generate_initial_image(drawio_path, yaml_path, env_path, script_dir, output_path):
    parser = DrawioParser(file_path=drawio_path, yaml_path=yaml_path, env_path=env_path, script_dir=script_dir, output_path=output_path)
    if os.path.exists(drawio_path):
        parser.mxGraphModelParse()
        parser.mxobjParse()
    parser.add_nodelist_diagram()
    parser.add_page("plan")
    parser.draw()

def start_logic_execution(drawio_path, yaml_path, env_path,script_dir , output_path):
    parser = DrawioParser(file_path=drawio_path, yaml_path=yaml_path, env_path=env_path, script_dir=script_dir, output_path=output_path)
    parser.mxGraphModelParse()
    parser.chainParse("plan")
    parser.print_tree()
    parser.add_nodelist_diagram()
    parser.start_logic()
    parser.add_page("plan")
    parser.draw()

def prepare():
    # delete files under logs directory without destroying directory structure
    logs_dir = "./logs"
    if os.path.exists(logs_dir):
        for root, dirs, files in os.walk(logs_dir):
            for file in files:
                file_path = os.path.join(root, file)
                os.remove(file_path)
    else:
        os.makedirs(logs_dir)

"""
# 生成初始的图像
autoPlan gen [--drawio] [--yaml]
    参数:
        --drawio 指定 drawio文件
        --yaml 指定 yml文件
        默认使用执行脚本当前目录下名为default.drawio, default.yml
    逻辑：
        解析 drawio文件，找到diagram name 为 "list page"页，如果没有则在drawio文件所有页的最左边创建一个页
        在这个页里面填充yaml node，layout 使用矩阵布局
        
# 开始流程图逻辑执行判断
autoPlan start [--drawio] [--yaml]
    参数:
        --drawio 指定 drawio文件
        --yaml 指定 yml文件
        默认使用执行脚本当前目录下名为default.drawio, default.yml
    逻辑：
        从starting_nodes 开始遍历
        执行其logic 内容，获取执行成功/失败状态
        如果成功走YES分支，如果失败走NO分支，开始迭代
            如果是YES 将判断成功的node置为check_pass style, 且将status中logic部分置为fail
            如果是NO 将判断失败的node置为check_fail style, 且将status中logic置为pass
"""

def main():
    parser = argparse.ArgumentParser(description='Auto Plan Script')
    
    parser.add_argument('action', choices=['gen', 'start'], help='Action to perform: gen or start')
    parser.add_argument('--drawio', default='default.drawio', help='Specify the drawio file')
    parser.add_argument('--yaml', default='default.yml', help='Specify the yml file')
    parser.add_argument('--env', help='Specify the env.sh file')

    args = parser.parse_args()

    # 获取当前脚本文件的绝对路径
    script_path = os.path.abspath(__file__)
    # 获取脚本文件所在的目录路径
    script_dir = os.path.dirname(script_path)

    # 定义需要检查的脚本目录中的文件列表
    script_required_files = ['autoTest.sh', 'env.sh']

    # 定义需要检查的当前工作目录中的文件列表
    current_dir_required_files = [args.drawio, args.yaml]

    # 检查文件
    check_files(script_dir, script_required_files, current_dir_required_files)
    prepare()

    output_path = "./"
    if args.env:
        env_path = args.env
    elif os.path.exists('./env.sh'):
        env_path = os.path.abspath('env.sh')
    else:
        env_path = os.path.join(script_dir, 'env.sh')  # 假设环境变量文件在脚本目录中

    # 逻辑实现部分可以放在这里
    if args.action == 'gen':
        print(f"Generating initial image using {args.drawio} and {args.yaml}")
        generate_initial_image(args.drawio, args.yaml, env_path, script_dir,output_path)
    elif args.action == 'start':
        print(f"Starting logic execution using {args.drawio} and {args.yaml}")
        start_logic_execution(args.drawio, args.yaml, env_path, script_dir,output_path)

if __name__ == "__main__":
    main()

