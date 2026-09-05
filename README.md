# physical-demo-lab

Isaac Sim 机器人仿真 demo；每次运行保留源码版本、场景、控制命令、逐帧物理状态、验证结果和视频。

第一个任务是 Franka 流水线颜色分拣：传送带通过接触摩擦送件，暂停后由平行夹爪抓取，再放入对应颜色的箱子。物体不使用位置重写、附着约束或隐形吸附。

## 当前范围

- 控制：已知物体位姿和颜色标签的脚本状态机 + differential IK。
- 物理：PhysX 刚体、传送带表面速度、平行夹爪接触摩擦。
- 场景：程序生成的传送带、支架、箱体，NVIDIA Franka Panda 资产。
- 随机化：箱子尺寸、质量、初始位置；未引入视觉识别、策略训练或动态不停带抓取。
- 初版代码已完成，端到端运行结果以 `reports/` 和每次输出的 `result.json` 为准。不能把状态机走完等同于成功。

## 环境和运行

目标环境：Ubuntu 22.04、Python 3.12、Isaac Sim 6.0.1.0、PyTorch 2.11.0、RTX GPU。完整依赖安装在数据盘独立目录，不复用其他项目的环境。

```bash
bash scripts/setup_server.sh
bash scripts/run.sh --gpu 1 --seed 0 --objects 3 \
  --output /data1/ybyang/physical-demo-lab-runtime/outputs/seed-0-first
```

`PHYSICAL_DEMO_RUNTIME` 可覆盖默认数据盘路径；`UV_BIN` 可覆盖 uv 的路径。输出目录必须不存在，失败尝试也保留，重跑需使用新目录。

`--gpu` 是物理渲染 GPU 的序号，运行前请用 `nvidia-smi` 检查是否空闲。场景的刚体动力学在 CPU 上计算，GPU 用于 RTX 渲染。首次加载 NVIDIA 资产可能需要网络。

运行会按 NVIDIA 文档设置 `OMNI_KIT_ACCEPT_EULA=YES`；使用者应阅读 [NVIDIA Omniverse EULA](https://docs.omniverse.nvidia.com/platform/latest/common/NVIDIA_Omniverse_License_Agreement.html)。安装的软件及 NVIDIA 模型资产遵循各自许可证，不随本仓库再分发。

## 可审计输出

每次运行生成：

- `manifest.json`：参数、版本、源码哈希、Git 版本、物体初始条件和限制。
- `scene.usda`：程序构建的 USD 场景，机器人引用仍依赖 NVIDIA 资产源。
- `trajectory.jsonl`：每个控制步的目标、关节和末端状态、物体状态。
- `events.jsonl`：状态转换与物体位置，便于定位失败阶段。
- `result.json`：各物体的验证项及总结果；失败返回非零退出码。
- `video.mp4`、`preview.png`、`final.png`：真实仿真渲染，不是生成视频。

成功必须同时满足：正确颜色箱、完整物体在箱内、低线速度和角速度、实际提起超过 8 cm、传送带搬运超过 5 cm、夹爪已打开并远离物体。

```bash
python3 -m unittest discover -s tests -v
```

## 依据与边界

参考用户选定的流水线短视频封面构思任务；没有取得完整视频轨迹，不能声称逐动作复刻。后续可以在相同记录接口上加入视觉、运动规划、更多任务及多 seed 测试。

- [Isaac Sim 官方安装文档](https://docs.isaacsim.omniverse.nvidia.com/6.0.1/installation/install_python.html)
- [Franka 机械臂接口与示例](https://github.com/isaac-sim/IsaacSim/tree/main/source/extensions/isaacsim.robot.experimental.manipulators.examples/isaacsim/robot/experimental/manipulators/examples/franka)
- [PhysX 表面速度定义](https://docs.omniverse.nvidia.com/kit/docs/usdrt.scenegraph/7.5.0/api/classusdrt_1_1_physx_schema_physx_surface_velocity_a_p_i.html)
