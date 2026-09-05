# physical-demo-lab

Isaac Sim 机器人仿真 demo；每次运行保留源码版本、场景、控制命令、逐帧物理状态、验证结果和视频。

第一个任务是 Franka 流水线颜色分拣：传送带通过接触摩擦送件，暂停后由平行夹爪抓取，再放入对应颜色的箱子。物体不使用位置重写、附着约束或隐形吸附。

项目已用 LabMate 初始化。后续逐项进度、经验入口与收尾流程见
[项目文档](docs/README.md)。每个 demo 在交付前必须更新验证报告和相关 knowhow，
通过完成检查；当前已完成流水线与收银的基础版，其余进度以项目文档为准。

## 当前范围

- 控制：已知物体位姿和颜色标签的脚本状态机 + differential IK。
- 物理：PhysX 刚体、传送带表面速度、平行夹爪接触摩擦。
- 场景：程序生成的传送带、支架、箱体，NVIDIA Franka Panda 资产。
- 随机化：箱子尺寸、质量、初始位置；未引入视觉识别、策略训练或动态不停带抓取。
- 已在服务器 23 的 Isaac Sim 6.0.1.0 跑通：10 个种子的最终结果均通过，30 个箱子完成分拣；其中 seed 7 曾在退出阶段异常，修复后重跑通过。完整范围与失败记录见 [首次验证报告](reports/bootstrap-validation.md)，不是固定版本的一次性 10/10 基准成绩。

## 环境和运行

目标环境：Ubuntu 22.04、Python 3.12、Isaac Sim 6.0.1.0、PyTorch 2.11.0、RTX GPU。完整依赖安装在数据盘独立目录，不复用其他项目的环境。

```bash
bash scripts/setup_server.sh
bash scripts/run.sh --gpu 2 --seed 0 --objects 3 \
  --output /data1/ybyang/physical-demo-lab-runtime/outputs/seed-0-first
```

`PHYSICAL_DEMO_RUNTIME` 可覆盖默认数据盘路径；`UV_BIN` 可覆盖 uv 的路径。输出目录必须不存在，失败尝试也保留，重跑需使用新目录。

中间数据统一位于 `/data1/ybyang/physical-demo-lab-runtime`：`venv/` 环境、`cache/` 下载与渲染缓存、`tmp/` 临时文件、`logs/` 安装记录、`outputs/` 仿真结果。普通依赖默认使用清华 PyPI 镜像（可用 `PYTHON_PACKAGE_INDEX` 覆盖），PyTorch 主包仍使用固定哈希的官方 wheel，Isaac Sim 使用 NVIDIA 源。

`--gpu` 是物理渲染 GPU 的序号，运行前请用 `nvidia-smi` 检查是否空闲。场景的刚体动力学在 CPU 上计算，GPU 用于 RTX 渲染。首次加载 NVIDIA 资产可能需要网络。

运行会按 NVIDIA 文档设置 `OMNI_KIT_ACCEPT_EULA=YES`；使用者应阅读 [NVIDIA Omniverse EULA](https://docs.omniverse.nvidia.com/platform/latest/common/NVIDIA_Omniverse_License_Agreement.html)。安装的软件及 NVIDIA 模型资产遵循各自许可证，不随本仓库再分发。

## 可审计输出

每次运行生成：

- `manifest.json`：参数、版本、源码哈希、Git 版本、物体初始条件和限制。
- `source/`：该次执行的完整 demo、验证器和运行脚本快照；不能只靠可能有未提交修改的 Git 版本号追溯。
- `scene.usda`：程序构建的 USD 场景，机器人引用仍依赖 NVIDIA 资产源。
- `trajectory.jsonl`：每个控制步的目标、关节和末端状态、物体状态。
- `events.jsonl`：状态转换与物体位置，便于定位失败阶段。
- `result.json`：各物体的验证项及总结果；失败返回非零退出码。
- `video.mp4`、`preview.png`、`final.png`：真实仿真渲染，不是生成视频。

完整命令、显卡快照和 stdout/stderr 保存在同级的 `<输出目录>.console.log`。使用 `python3 scripts/evaluate.py --root <新目录> --gpu 2` 可启动 10 个独立进程的 seed 测试；无论成功或失败，都保留各次输出。

服务器存在相同版本的 SDK 时，可选择 `scripts/reuse_extscache.py` 校验并复制三个扩展缓存发行包。它只读原环境，逐文件检查 RECORD 哈希，不复制原环境的解释器或训练依赖；常规安装不需要此步骤。

成功必须同时满足：正确颜色箱、完整物体在箱内、低线速度和角速度、实际提起超过 8 cm、传送带搬运超过 5 cm、夹爪已打开并远离物体。

```bash
python3 -m unittest discover -s tests -v
```

## 依据与边界

参考用户选定的流水线短视频封面构思任务；没有取得完整视频轨迹，不能声称逐动作复刻。后续可以在相同记录接口上加入视觉、运动规划、更多任务及多 seed 测试。

- [Isaac Sim 官方安装文档](https://docs.isaacsim.omniverse.nvidia.com/6.0.1/installation/install_python.html)
- [Franka 机械臂接口与示例](https://github.com/isaac-sim/IsaacSim/tree/main/source/extensions/isaacsim.robot.experimental.manipulators.examples/isaacsim/robot/experimental/manipulators/examples/franka)
- [PhysX 表面速度定义](https://docs.omniverse.nvidia.com/kit/docs/usdrt.scenegraph/7.5.0/api/classusdrt_1_1_physx_schema_physx_surface_velocity_a_p_i.html)
