# 城堡：有界驱动目标与原生接触证据

2026-09-06。依据 [开发账本](../../../reports/demo009-castle20-development.md)、
服务器 Data1 `outputs/castle-isaac` 中保留的 V4/V5/V6 轨迹与 SDK 本地源码。
这条经验针对 20 件城堡；不外推到 200/1000 件或任意 Franka 工作区。

## 先区分端点可达与当前路径收敛

旧 V4 在第三块下探时残差 27.173 mm，前两块完成。复算 FK 与原生末态一致，
有界数值逆解存在，但需要改变多个关节。没有证据将其归因为单一关节限位，
也不能从独立端点逆解推断整段无碰撞可执行。

V5/V6 用较低阻尼 Jacobian 目标、相对实际关节位置的最大目标误差，
以及最多 3 秒的段末收敛等待。仍通过原生有限驱动器运动，
不在运行中重置机器人或物体，不提高驱动力，不放宽物理 verifier。
V5 三块与 V6 全 20 块通过；这只支持组合修改有效，不拆分单项因果。

## 从物体与接触记录验证抬升

手部目标高度和 `lift` 阶段名不足以证明物体被抓起。
审计流式检查每个原生步的对象身份、有限状态、物体相对初态抬升，
及同一时刻左右手指的非零法向力。V6 所有 20 件均有至少 80 mm 抬升
和双指受力的原生样本，最终仍须检查实际支撑、脱手、位置姿态速度和连续时间。

SDK `RigidPrim.get_contact_force_data` 返回法向标量及 normals，实际记录中存在负号。
因此载荷存在性用有限非零幅值，不能只筛 `force > 0`。
首版零抬升误报回执保留，修订另存，并有负号/零力单元测试。
这不是重新解释力方向，更不等于已经记录了完整摩擦力或证明全路径碰撞安全。

## 冻结自己的 verifier 与运行时

每次审计加载该次 `source/demos/castle_verify.py`，先核对 manifest 哈希，
不能用后来修改的 live verifier 替代。240 Hz 原生步、60 Hz 控制步和
30 Hz 视频分别核对；这里是记录状态上的 oracle 回放，不是动作重执行。

城堡使用独立 `castle_runtime.py`，避免改变已完成 demo 的公共运行时指纹。
GPU UUID 屏蔽下逻辑 physics CUDA 0 与 renderer 物理卡编号不同；
用实际进程组占卡记录核验，不能仅凭参数声称隔离。
已有 GPU 1 完整运行和 GPU 7 短负向隔离证据；每个后续运行仍需独立监控。

## 重现入口与范围

在服务器主仓库运行 runtime 下的 Python：
`/data1/ybyang/physical-demo-lab-runtime/venv/bin/python`。
`scripts/run_castle_task.py` 要求新输出路径，保留控制日志、进程退出和资源监控；
`scripts/audit_castle.py OUTPUT --receipt NEW_JSON` 产生独立只增回执。
参数与全部失败路径见开发账本。多种子和视频验收未结束前，不标记整个 demo 完成。
