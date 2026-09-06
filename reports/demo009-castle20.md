# demo009：20 件 Isaac 城堡完成报告

2026-09-06。固定版本 seeds 0–5 首轮 **6/6 完整通过**，每轮 20/20 件均有原生双指受力抬升、最终脱手支撑及连续稳定证据。六条全程视频均完整解码，逐条查看最终画面；没有把开发首跑算入这六次。200/1000 件仍暂停。

## 已验证范围

单 Franka、已知物体状态、固定 20 件蓝图与小幅散放初态扰动，脚本控制器通过有限关节驱动与接触摩擦逐块搭建。episode 时钟开始后不重写机器人或积木状态；启动时的机器人初始化不算执行动作。没有附着/吸附替代抓取。原目标、尺寸、质量和物理成功条件未放宽。

六轮均通过各自源码快照中的 verifier 回放；20 件各有抬升至少 80 mm 且左右手指同时非零有限法向力的原生样本。位置、姿态、速度、支撑、脱手与持续时间另由物理 verifier 判定。所记录过滤接触的非手指穿透样本均为零，不据此声称全空间零碰撞。原生接触最大穿透跨六轮不超过 0.886 mm。

| seed | 240 Hz 原生步 / 60 Hz 控制步 | 连续稳定秒 | 30 Hz 视频帧 / 秒 | 进程 |
| --- | --- | --- | --- | --- |
| 0 | 105644 / 26411 | 11.2333 | 13206 / 440.2000 | 0 |
| 1 | 105720 / 26430 | 11.2708 | 13215 / 440.5000 | 0 |
| 2 | 105756 / 26439 | 11.0250 | 13220 / 440.6667 | 0 |
| 3 | 105552 / 26388 | 11.2333 | 13194 / 439.8000 | 0 |
| 4 | 105500 / 26375 | 11.1208 | 13188 / 439.6000 | 0 |
| 5 | 106020 / 26505 | 10.9875 | 13253 / 441.7667 | 0 |

回执：[seed 0](demo009-seed0-audit.json)、[seed 1](demo009-seed1-audit.json)、[seed 2](demo009-seed2-audit.json)、[seed 3](demo009-seed3-audit.json)、[seed 4](demo009-seed4-audit.json)、[seed 5](demo009-seed5-audit.json)。
独立审计是记录状态上的 oracle 重算，不是重新执行动作。六轮资源监控均无终止原因；只覆盖采样到的自身进程组 CUDA 上下文。

## 版本、原始证据与复现

环境：Python 3.12.13 / Isaac Sim 6.0.1.0 / Torch 2.11.0+cu128。
行为源文件冻结为 `e6d2b9f` 的版本；之后 `e3993f1` 只增加测试。八个实现文件的当前 SHA-256 记录在 [完成账本](../docs/demos.json)，与六次运行快照一致。固定 PGS、4 velocity iterations、50000 控制步；每实例墙钟上限 5400 秒，实际完成约 29–32 分钟。GPU 1/7 最多两实例，不以增加物理预算换通过。

原始根：`/data1/ybyang/physical-demo-lab-runtime/outputs/castle-isaac`。
`final-v6-seed0` 至 `final-v6-seed5` 保留 source、manifest、invocation、scene、240 Hz physics/contacts、60 Hz trajectory、events、result、audit 和 video；同名前缀旁保留 console/process/gpu 记录。大文件不重复放进 Git。

以下示例需要先确认 GPU 1 空闲，并使用从未存在的新输出路径；换 seed 时逐项记录全部结果，不覆盖失败：

```bash
cd /data1/ybyang/physical-demo-lab
/data1/ybyang/physical-demo-lab-runtime/venv/bin/python scripts/run_castle_task.py block_castle \
  --output /data1/ybyang/physical-demo-lab-runtime/outputs/castle-isaac/reproduction-new-seed0 \
  --gpu 1 --wall-seconds 5400 --seed 0 --solver PGS --velocity-iterations 4 \
  --parts 20 --width 640 --height 480 --max-steps 50000
/data1/ybyang/physical-demo-lab-runtime/venv/bin/python scripts/audit_castle.py \
  /data1/ybyang/physical-demo-lab-runtime/outputs/castle-isaac/reproduction-new-seed0 \
  --receipt /data1/ybyang/physical-demo-lab-runtime/outputs/castle-isaac/reproduction-new-seed0/audit-v1.json
```

## 失败、负向与复用经验

旧 V4 只完成 2/20；V5 是前三块部分验证；V6 开发首跑完整通过，但不计入正式六轮。全部路径、FK 对照、有界控制组合修改及带符号法向力审计修订保留在 [开发账本](demo009-castle20-development.md)，不归因于未经消融的单个参数。

[一步预算负向](demo009-negative-audit.json)：退出 2，零抬升、完整装配 false；
[散放初态](demo009-loose-audit.json)：6 秒稳定测试通过，但完整装配仍 false。
14 项城堡测试包含负号受力、零力、单指重复和非有限值拒绝；全项目 51 项测试通过。
复用经验见 [有界驱动与原生抬升证据](../docs/knowhow/debug-solutions/castle-bounded-control-and-lift-evidence.md)。

这次完成不等于任意蓝图生成、200/1000 件扩展、视觉闭环、学习策略泛化或 MuJoCo/Isaac 等价。
[真实最终截图](../docs/previews/demo009-castle20.png) 来自 seed 0 原生 final.png，字节一致，来源见 [预览清单](../docs/previews/manifest.json)。
