# Allegro 安装链、接触报告与仿真时钟

2026-09-06；Isaac Sim 6.0.1.0，基于
[瓶盖开发账本](../../../reports/demo005-bottle-cap-development.md) 的已观察事实。
此条记录集成经验；整个任务状态以进度表及最终审计为准。

## 不把 articulation 链表首项当固定身份

官方 `allegro_hand.usd` 包含 `root_joint` 世界固定关节及 `allegro_mount`→`palm_link`
固定连接。固定基座的探针首链为 `allegro_mount`；移除世界固定后，浮动 articulation
首链变为 `palm_link`。`development-1/scene.usda` 显示腕部被错误绑定到手掌，
实际画面朝向也错误。后续按已核对的 `allegro_mount` 路径绑定，在 USD 上统一放置
整手，并保留 `hand-mount.json` 初始姿态证据；`development-3` 后实际接触旋转出现。

资产探针不能只看进程退出 0。`hand-probe2` 虽完成开合，但额外固定点与资产原关节
重复，日志有 disjoint transform 警告；后续 `hand_probe.py` 改为直接校正原固定关节锚点，
该修改后的独立探针还没有重新运行，不能写成已验证的新探针结果。

## D6 整圈旋转使用 twist 轴

第一轮用 rotZ swing 限位表示完整转角，PhysX 报 `setPyramidSwingLimit: limit invalid`。
将关节局部 X 轴旋到世界 Z 后，锁局部 transY/Z、rotY/Z，使用 rotX twist 与 transX
作为旋转和升降轴。后续运行无该错误，并记录到实际瓶盖转动。此结论只覆盖此处的
非 articulation 外接 D6 安装/导向结构，不推断任意 D6 都可加入 reduced-coordinate articulation。

## 接触查询先应用报告 API

`RigidPrim(..., contact_filter_paths=['/World/Cap'])` 在当前 SDK 不能自动为手指资产
补全 `PhysxContactReportAPI`。缺失时 physics ready 报未找到 contact report API，
随后 `get_contact_force_matrix` 的底层 view 为 None，`development-2` 退出 1。
在 play 前给被监测手指刚体显式应用该 API、阈值设 0 后，第三轮能记录每条链对盖子的
非零力矩阵。`get_contact_force_matrix(dt=实际物理步长)` 才把冲量换算为力。
这里只记录法向接触合力；不把它误称完整切向摩擦力或力矩分布。

## 物理步长不等于 app 时间线步长

`development-5` 配置物理 dt=1/120，但首条轨迹的实际 physics_steps=2、sim_time=1/60。
这是当前应用时间线仍以 60 Hz 更新的直接证据，不能按每次 app.update 就是一物理步审计。
本地 SDK `RenderingManager.set_dt` 的文档与实现明确要求渲染/时间线和
`SimulationManager.setup_simulation(dt)` 分别设置：前者同步 timeline time-codes、
loop-runner manual step 和相关 Fabric 默认值，不修改物理场景 timeStepsPerSecond。
代码在相机/渲染产品创建前设置相同 dt，并用每条轨迹实际计数和时间检查结果。
对于原本在 60 Hz 验证过的共享运行器，不因新任务而静默改动或刷新旧证据指纹。

`development-6` 实际首条为 physics_steps=1、sim_time=1/120，全部 2324 条连续；
独立审计通过。盖半圈脱扣、提离 166.94 mm，最后 5.94 秒满足双指接触与低速保持。
同期改变了耦合刚度、步进频率和驱动，不能据此声称每一项的独立改善量。

不同平台的 `atan2`/累计浮点误差可能有约 1e-15 差异；结果数值复核使用小容差，
离散成功检查和脱扣帧仍严格相等。不能把浮点完全相等当跨平台物理一致性的标准。

## TGS 与 D6：更多速度迭代不等于更准确

2026-09-06 查询 [NVIDIA Known Physics Limitations](https://docs.omniverse.nvidia.com/kit/docs/omni_physics/latest/dev_guide/guides/current_limitations.html)
的 D6 Joint Drive、TGS Velocity Iterations、Articulation Joint Drive with TGS solver 条目。
官方明确指出 TGS+D6 驱动与速度迭代的已知兼容性问题，推荐零速度迭代或尝试 PGS；
驱动达到稳态却报告非零速度时，可测试每次内部求解迭代施加外力选项。
该文档使后续候选改为全场 64/0 迭代及 `enableExternalForcesEveryIteration=True`。
尚未把此前抖动唯一归因于该问题；需要保留对照及实际速度结果后再判断本夹具的效果。

实测对照：240 Hz、64/16 的 `seed-1-240hz` 最长符合保持 0.996 s，仍失败；
240 Hz、全场 64/0 且逐迭代外力的 `seed-1-tgs-zero` 最后连续 5.9375 s 符合保持，
退出 0 且独立审计通过。两个求解设置联合更改，不分开估算其因果贡献。
没有放宽角速度 <0.5 rad/s、线速度 <0.03 m/s、双指接触或连续两秒阈值。
这也不要求修改前四项已经通过各自判据的实现；它们没有这套灵巧手外接 D6 结构。
