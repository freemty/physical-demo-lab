# 搭积木最小流程：Blender → Isaac → 专家轨迹

[English Getting Started](../../GETTING_STARTED.md) ·
[直接打开示例](../../examples/castle20/README.md) ·
[已验证的物理结果](../../reports/demo009-castle20.md)

这个入口只做一件事：生成 20 块城堡的 Blender 场景，把同一份物理蓝图导入 Isaac，
让 Franka 从散块开始实际搭建，再保存完整轨迹和关键阶段。

## 先选使用方式

只想看场景：克隆后直接打开 `examples/castle20/castle.blend`，
在 Blender 的 Scene 下拉框切换 Goal、Loose、Exploded，无需插件或自动执行脚本。
也可以查看 [已有关键轨迹样本](../../examples/castle20/trajectory/README.md)。

想重新生成场景：需要 Python 3.10+ 和 Blender 4.5 LTS，不需要 Isaac 或模型 API。
想生成新的机器人轨迹：需要 Linux x86_64、NVIDIA RTX 显卡和 Isaac 环境；Mac 只查看产物。

当前不是把任意 `.blend` 文件自动变成机器人任务。积木身份、尺寸、质量、散放位置、
目标位置与支撑关系在同一份 JSON 蓝图中；Blender 生成场景并一起导出它，
Isaac 将 JSON 编译成 USD/PhysX。视觉倒角和灯光不作为碰撞几何导入。
手动修改 Blender 网格不会自动同步回仿真蓝图。

## 1. 安装与检查

仓库若仍为私有，需要先取得访问权限。在仿真机器上执行：

```bash
git clone https://github.com/freemty/physical-demo-lab.git
cd physical-demo-lab
export PHYSICAL_DEMO_RUNTIME="$PWD/.runtime"
```

先安装 [uv](https://docs.astral.sh/uv/getting-started/installation/)、
[Blender 4.5 LTS](https://www.blender.org/download/lts/4-5/)、
系统 `ffmpeg`/`ffprobe`，并确认 NVIDIA 驱动正常。
阅读 [硬件要求](https://docs.isaacsim.omniverse.nvidia.com/6.0.1/installation/requirements.html)：
headless 不代表不需要 RTX 显卡。完整启动器目前只支持 Linux x86_64。

本项目验证组合为 Ubuntu 22.04、Python 3.12.13、Isaac Sim 6.0.1.0、
PyTorch 2.11.0+cu128、RTX 5880 Ada / 驱动 595.71.05；不把这张卡写成最低配置。
环境/缓存建议先预留 60 GB，每条完整轨迹另留约 2 GB。首次还需联网获取 NVIDIA 机器人资产。

读过并接受 [NVIDIA EULA](https://docs.omniverse.nvidia.com/platform/latest/common/NVIDIA_Omniverse_License_Agreement.html) 后：

```bash
export OMNI_KIT_ACCEPT_EULA=YES
bash scripts/setup_castle.sh
export BLENDER_BIN=blender
python3 scripts/castle.py doctor --gpu 0
```

Blender 不在 PATH 时，把 `BLENDER_BIN` 改为实际可执行文件的绝对路径。
安装器不会改已有 `venv/`，不会往其他训练环境装依赖。
检查失败先看报错；不要因为预检通过就认为 GPU 空闲或仿真已成功。

只用 Blender 的用户跳过 Isaac 安装，设置 `BLENDER_BIN` 后进入下一步。
例如 Mac 的常见路径为 `/Applications/Blender.app/Contents/MacOS/Blender`；
本轮实际生成和重新打开验证在 Linux 完成，未把它写成 Mac 实测。

## 2. 生成 Blender 场景

```bash
python3 scripts/castle.py build --output outputs/castle20-design --render
```

输出 `castle.blend`、`scene_spec.json`、三张布局图片和 `blender-audit.json`。
检查会重新打开保存的 Blender 文件，核对三种布局、独立积木数量、几何尺寸等。
不需要图片时去掉 `--render`。

## 3. 导入并试跑

用 `nvidia-smi` 确认空闲 GPU；下例 0 只是示例编号。

```bash
python3 scripts/castle.py run --design outputs/castle20-design \
  --output outputs/castle20-loose-0 --mode loose --gpu 0
```

这是六秒散放稳定性检查。输出包括原生 USD、状态与视频；
退出 0 只表示本项初态检查通过，不表示机器人搭好了城堡。

## 4. 生成完整专家轨迹

```bash
python3 scripts/castle.py run --design outputs/castle20-design \
  --output outputs/castle20-seed0 --seed 0 --gpu 0
```

当前使用已知状态脚本控制器，不需要训练或 LLM API。
此前六个种子均实际完成 20 块装配，每轮约 440 秒模拟运动，在记录机器上约 29–32 分钟墙钟时间。
不是把积木逐帧摆到目标位置，也不把 Blender 布局切换当作机器人轨迹。

每次必须用新目录。失败、退出和资源监控都保留；不覆盖旧运行，不终止无关 GPU 任务。

## 5. 审计并导出关键阶段

```bash
python3 scripts/castle.py audit --run outputs/castle20-seed0 \
  --receipt outputs/castle20-seed0-audit.json
python3 scripts/castle.py export --run outputs/castle20-seed0 \
  --output outputs/castle20-seed0-keyframes
```

审计要求完整 20 件装配、逐件真实双指受力抬升、物理回放一致、正确进程结果及全片解码。
最后仍需查看视频。散放或预摆终态即使稳定，也会被这个完整装配入口拒绝。

关键阶段包内有 `keyframes.json`、`waypoints.csv`、`events.json` 和带哈希的导出清单。
位置是米，四元数顺序是 wxyz；机械臂转动关节是弧度、夹爪移动关节是米。
完整字段见 [输出说明](castle-outputs.md)。

关键点是从实际执行记录摘出的稀疏视图，不是重新生成的运动，
也不是可直接下发真实机器人的控制程序。完整 `trajectory.jsonl` 与原生物理记录仍是主证据。

更多排错见 [英文 Getting Started](../../GETTING_STARTED.md#troubleshooting)。
200/1000 块、任意蓝图、视觉策略、Lego 卡扣和真实机器人不在这个最小例子的验收范围内。
