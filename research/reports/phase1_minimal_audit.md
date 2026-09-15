# Phase 1 Minimal Principle Test：Policy Identifiability Audit

日期：2026-09-15  
范围：只读取已有 `results/full/raw_traces.jsonl`、汇总 CSV 和当前 generator/policy source；没有修改 benchmark，也没有重新运行实验。

## 判定

**B. NON-IDENTIFIABLE**

原始分数在一部分 episode 中不同，但两种 policy 在这个 benchmark 中没有产生任何可观测的决策差异：top-K、保留集合、eviction 序列和 q2/q3 结果全部相同。因此不能把原 Phase 1 的结果解释成“两个不同 signal 经过实验后都失败”；更准确的是：**这个 benchmark 没有把 RMM-like 和 task utility 识别成两个不同的 policy。**

## 数据范围

- 96 个 episode-budget 单元：8 个 scenario × 3 seeds × 2 capacities × 2 pressure levels。
- 每个单元各有一条 `rmm_like` 和一条 `task_utility` trace。
- capacity：8、16；pressure：2×、4×。
- 比较对象的 score 向量使用 post-use 时刻的所有 block ID；缺失分数按 0 补齐。
- Top-K 使用确定性排序（分数降序，随后按写入顺序和 block ID 打破平局），K 测试为 1、2 和 hot capacity。

## Score-level comparison

| capacity | pressure | n | mean Pearson | mean Spearman | score vectors differ |
|---:|---:|---:|---:|---:|---:|
| 8 | 2× | 24 | 0.919763 | 0.998530 | 9/24 |
| 8 | 4× | 24 | 0.919763 | 0.998530 | 9/24 |
| 16 | 2× | 24 | 0.923839 | 0.999497 | 9/24 |
| 16 | 4× | 24 | 0.923839 | 0.999497 | 9/24 |

Across all 96 cells:

- Exact normalized score vectors equal：60/96；different：36/96（37.5%）。
- Pearson：96/96 defined，mean `0.921801`，min `0.752071`，max `1.000000`。
- Spearman：96/96 defined，mean `0.999014`，min `0.995859`，max `1.000000`。

分数差异只出现在 `cross_event`、`negation_condition` 和 `related_nonidentical` 的多 evidence q1。例子：q1 的 RMM 分数可能是 `A=0.82, B=0.18`，task utility 却是 `A=0.5, B=0.5`。这是数值差异，但不是决策差异。

## Policy-level comparison

| 检查项 | 结果 |
|---|---:|
| Top-1 Jaccard = 1 | 96/96；均值 1.000 |
| Top-2 Jaccard = 1 | 96/96；均值 1.000 |
| Top-K（K=capacity）Jaccard = 1 | 96/96；均值 1.000 |
| q2/q3 前 retained hot sets 有差异 | 0/96 |
| q2 retained set 有差异 | 0/96 |
| q3 retained set 有差异 | 0/96 |
| individual eviction decisions 有差异 | 0；共对齐比较 4,152 次 eviction decision |
| eviction sequence 有差异的 episode | 0/96 |
| 存在 RMM `A>B` 且 task `B>A` 的 episode | 0/96 |
| score disagreement 改变 q2/q3 evidence recall 或 answer proxy | 0/96 |

因此不存在“信号排序不同、但最终性能刚好一样”的 A 类证据；连 eviction 决策层都没有分叉。

## Generator 和 answer model 审计

### Task utility 的结构

[`run_pilot.py`](../experiments/phase1_minimal/run_pilot.py) 中的 `q1_utility()` 把 q1 的每个 gold evidence 直接赋值为 `1/n`。它没有真正执行两次 answer model，也没有计算真实 log-probability difference；它使用的是确定性 coverage loss：删除任意一个非冗余 evidence，loss 增加相同的 `1/n`。

所以：

```text
q1 evidence = [A, B]
task utility = {A: 0.5, B: 0.5}
```

### RMM-like 的结构

[`policies.py`](../experiments/phase1_minimal/policies.py) 在 q1 后计算：

```text
rmm_signal(block) = q1 attention_weight(block) × answer_correct
```

runner 永远以 `answer_correct=True` 调用 `observe_q1()`。因此：

```text
rmm_like = q1 attention weights
```

而 generator 为每个 q1 evidence 都提供正 attention weight。RMM 和 task utility 因而都会 promotion **同一批 q1 evidence**。在单 evidence 场景中，分数向量也相同；在多 evidence 场景中只是数值/权重不同。

### 为什么 downstream 仍完全相同

`rmm_like` 和 `task_utility` 的 post-q1 promotion 循环都把所有正分数 block 放入 hot set。之后 pressure 写入使用的 score 只需要把这些 block 与大量 0 分新 block 区分开；两者保护集合相同，eviction 顺序也相同。

q2/q3 的 answer proxy 也是二值的：所有 gold evidence 都在 hot set 才是 1，否则是 0。没有 partial-answer 或连续 loss 可以暴露分数大小差异。

## 为什么 Recency/Frequency/Attention 全部饱和为 0

这不是一个有意义的“它们都很差”的结论，而是当前 benchmark 的结构结果：

1. t1 的 distractor writes 先把 q1 evidence 从 hot set 淘汰。
2. q1 的 cold query 只读取 archive，并更新 recency/frequency/attention 统计；普通 `query()` 不会把 cold evidence 重新加入 hot set。
3. 只有 `rmm_like` 和 `task_utility` 的 `observe_q1()` 会显式调用 promotion；见 [`policies.py`](../experiments/phase1_minimal/policies.py) 的 q1 分支。
4. 随后再写入 2×/4× capacity 的压力历史。由于 recency/frequency/attention 从未重新接纳 q1 evidence，它们在 q2/q3 前自然全部失去目标 evidence。

因此 full pilot 中三者的 `future_useful_retention=0` 是 admission/update 语义造成的饱和，不能解释为真实模型中 recency、frequency、attention 的一般性能上界。

## 最终判断

选择 **B. NON-IDENTIFIABLE**：

- 原始 score 在 36/96 单元不同；
- 但严格的 rank reversal 为 0；
- Top-K、promotion target、eviction sequence、retained sets 和 q2/q3 outcomes 全部相同；
- generator 又把 RMM-like 简化成 q1 attention×恒真 correctness，把 task utility 简化成均匀 coverage delta。

所以现有结果既不能支持 task utility 优于 RMM-like，也不能支持二者在真实 workload 中等价。它只说明：**当前 synthetic benchmark 没有提供辨别二者的条件。**

本审计到此停止。不修改 benchmark，不扩大实验，不进入 Phase 2 或完整 RCHAM 实现。
