# Environment Report

检查日期：2026-09-14

| 项目 | 结果 |
|---|---|
| OS | macOS 26.6.2 arm64 |
| CPU | Apple M5，10 logical CPUs |
| Memory | 16 GiB unified memory |
| Disk | 工作区所在卷约 605 GiB 可用 |
| Python | 系统 Python 3.14.7；研究运行时 Python 3.12.14 |
| NumPy | 2.4.2 |
| Pandas | 可用 |
| Pillow | 可用 |
| PyTorch | 未安装 |
| Transformers | 未安装 |
| Ollama | `/usr/local/bin/ollama`，服务可运行 |
| Existing model | `ornith-agent:latest`，Ollama 显示 7.6 GB |
| Network | `gh` 已认证；本 Pilot 不需网络下载 |
| GPU | Apple Silicon GPU 可由本机 Ollama 使用；未把硬件加速计作研究结论 |

## 约束

本阶段没有下载超过 5GB 的新模型，没有收费 API，没有系统级修改，没有 sudo，没有删除数据，也没有开始大规模训练。小型本地模型调用用于 Pilot，原始模型输出全部保存。

## 可复现性

环境报告只记录检查到的环境，不代表 `ornith-agent` 的训练来源或语义能力。模型名称、压缩 prompt、回答 prompt、参数、上下文上限和运行时间写入 Pilot manifest。
