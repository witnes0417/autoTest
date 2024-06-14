#!/bin/bash
# 生成 autoTest.spec 文件并打包
pyinstaller --name autoTest --onefile src/main.py \
    --add-data "./venv/lib/python3.11/site-packages/drawpyo:drawpyo" \
    --add-data "src/autoTest.sh:./" \
    --add-data "src/env.sh:./" \
    --add-data "mmlshell:./mmlshell"

# 使用生成的 autoTest.spec 文件进行打包
# pyinstaller autoTest.spec

