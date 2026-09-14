# 研究仓库档案：v0.1

留档日期：2026-09-14。仓库已建立在本任务工作区。

## 架构与思想

- [仓库 README](../README.md)
- [架构设计 v0.1](../docs/architecture-v0.1.md)
- [实验假设 H1–H5](../docs/experiment-hypotheses.md)
- [思想与版本记录](../docs/design-history.md)
- [后续完整实验计划](research_plan.md)

![架构图 v0.1](architecture-v0.1.png)

[SVG 版本](architecture-v0.1.svg) · [Mermaid 源码](../docs/figures/architecture-v0.1.mmd) · [SVG / PNG 绘图脚本](../scripts/render_architecture.py)

## 已运行的预实验

- [结果解读与复现方法](compression_probe/README.md)
- [实验代码](compression_probe/probe.py)
- [汇总 CSV](compression_probe/summary.csv)
- [完整 JSON 报告](compression_probe/report.json)
- [逐题原始记录](compression_probe/per_query.csv)
- [具体失败轨迹](compression_probe/error_trace.json)
- [文件校验与重复运行核对](compression_probe/manifest.json)

当前结果只覆盖无训练的合成向量导航，语义压缩、状态重建和完整模型架构仍待验证。归档前已重新运行，非时间结果一致；本次结果文件保留原始测量值。

## 版本操作

在仓库根目录查看历史与本次标记：

```bash
git log --oneline --decorate
git show architecture-v0.1
```

后续设计发生实质变化时，另存 `docs/architecture-v0.2.md`，在思想记录中解释变更并提交。新实验输出到新的目录，保留本次结果。

绘图脚本使用标准库生成 SVG；需要 PNG 时额外使用 Pillow，并通过 `--font` 指定本机中文字库。实验本身只依赖 NumPy。
