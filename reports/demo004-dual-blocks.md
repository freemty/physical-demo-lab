# demo004：双臂积木桥验证账本

2026-09-06。依据 [运行前规格](../docs/specs/demo004-dual-blocks.md)。三个独立初态、
九件积木均通过物理判定与 [独立审计](demo004-audit.json)，该基础版完成。

## 范围与证据

两只 Franka 顺序共用中央工作区：左臂放左柱，右臂放右柱，左臂放横梁。
闲置臂保持外侧停靠位；每个动态零件仅通过夹爪摩擦、接触和重力移动。
没有零件位姿重写、隐藏固定连接、同时双臂持物或手递手。观测是已知物体状态，
不是视觉或学习策略。参考仅为用户所选标题和封面，不能声称完整原视频复刻。

所有输出根目录为服务器 23 的 `/data1/ybyang/physical-demo-lab-runtime/outputs/demo004/`。

| 运行 | 实现 | 结果 |
| --- | --- | --- |
| `seed0-attempt1` | `fa06f94` | 返回 0；3,360 步、56 仿真秒，双臂参与、三件落位和支撑均通过。 |
| `negative-step-budget` | `c1ddcea` | 一步预算返回 2；双臂未搬运、积木未搭起；负向审计不通过。 |
| `eval-1-2/seed-1` | `c1ddcea` | 返回 0；物理判定、三秒逐帧稳定性与独立审计通过。 |
| `eval-1-2/seed-2` | `c1ddcea` | 返回 0；物理判定、三秒逐帧稳定性与独立审计通过。 |

两提交的物理入口、验证器、共享记录器和启动器相同；后一个提交仅增加独立双臂审计分支。
每次保留源码快照、实际调用、场景、逐步状态、视频/图像、外部进程状态。
本项没有实际物理失败或控制修订；故意的一步预算负向用例单独列出，不混入成功率。
22 项项目测试通过，包含缺少一臂、缺少支柱、横梁悬空、未提起和未释放的负向判定。

审计不采信状态机的“左/右臂参与”标签，而从实际关节、手与零件距离、实时提起高度
重新判定双方参与。从终态阶段舍去第一秒后，对余下三秒的每个物理帧检查支撑、位置、
速度、姿态和双爪撤离。没有接触力传感器；本次支撑证据是几何覆盖、高度及重力下稳定。

首轮视频为 960×720、30 fps、56 秒，共 1,680 帧。抽查 24 秒右臂搬柱、
41/44 秒左臂搬梁和最终三件搭桥画面；不是逐帧人工审核整段视频。
便于查看的本地副本为 `outputs/dual-blocks/video.mp4`，全量证据留在 Data1。

复现：

```bash
python3 scripts/run_task.py dual_blocks --seed 0 --gpu 7 --output <新目录>
python3 scripts/evaluate_task.py dual_blocks --seeds 1 2 --gpu 7 --root <新批次目录>
python3 scripts/audit_task.py --runs <各运行目录> --output <新审计文件>
```

复用了 [齿轮姿态与几何审查](../docs/knowhow/debug-solutions/gear-seating-and-pose.md)
和 [共享记录/退出码](../docs/knowhow/toolchain/checkout-and-process-evidence.md)。
新增 [双臂参与与持续支撑](../docs/knowhow/toolchain/dual-arm-support-evidence.md)。
