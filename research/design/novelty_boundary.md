# RCHAM 创新边界（暂定）

## 已知不能单独主张的新颖点

以下组件分别已有公开工作：局部/sliding-window attention、压缩 memory、summary/memory tokens、层级表示、粗到细路由、landmark/raw-block fallback、KV 分层、访问次数强化、时间衰减、agent memory consolidation 和 query-agnostic KV eviction。

## 最近邻与差异

1. **Landmark Attention** 已实现 query → landmark → raw block 的内部路由。RCHAM 最小差异不能是“先找块再读原文”，而必须是多层生命周期和反馈更新。
2. **H²MT** 已公开 semantic hierarchy、bottom-up memory embedding 和 coarse-to-fine pruning。RCHAM 不能把层级树或粗到细本身作为创新；当前公开摘要没有显示召回后用 counterfactual utility 更新内部 KV tier，这一点仍需读完整配置确认。
3. **HeteroCache** 已公开 training-free heterogeneous KV budgets、hierarchical storage 和 attention drift 触发异步 retrieval。RCHAM 不能把动态缓存或异步取回作为创新；待核对的是是否有“证据证明有用”驱动的 promote/demote 闭环。
4. **R³Mem、RecMem、MemoryBank** 已在外部/agent memory 里覆盖 reversible retention、层级巩固、重复使用和遗忘。RCHAM 的差异若成立，只能落在 Transformer 内部 KV 生命周期、utility 的反事实定义和相同预算下的控制器比较。
5. **KVzip** 已做 query-agnostic KV eviction 和 context reconstruction importance。RCHAM 需要证明 post-retrieval utility 与写入前预测重要性是不同且有收益的信号。

## 可检验的最小贡献声明

> 在固定 memory/retrieval budget 和未来 query 未知的设置下，一个在读取后依据 counterfactual utility 促升、并配合衰减与 cooldown 的层级记忆控制器，是否比静态、最近性和召回次数控制器保留更多未来有用证据，同时维持更低的 churn？

这句话是可证伪的，也没有声称发明压缩、召回或层级结构。

## No-go 条件

- 若主来源中已有内部 Transformer 方法完整实现该闭环，停止使用“新架构”措辞，改做严格复现或差异化分析。
- 若 utility 标签只能依赖未来问题本身而无法在真实读取后观测，必须把研究降级为离线 oracle 分析。
- 若相同预算下 utility-conditioned 方法没有稳定优势，不能用更大模型或更高预算掩盖结论。
