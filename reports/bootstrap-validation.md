# 首次环境与流水线分拣验证

验证日期：2026-09-05 至 2026-09-06（Asia/Shanghai）。

## 结果与范围

已在服务器 23 完成独立环境安装和 Franka 颜色分拣 demo。最终选定的 seed 0–9 共 10 次运行、30 个物体通过物理验证，进程均正常返回。验证时发生过修复与重跑：这不是固定版本、无重试的 10/10 基准成绩，也不支持泛化能力结论。

控制器读取已知物体位姿与颜色标签，使用脚本状态机和 differential IK。传送带通过 PhysX 表面速度与接触摩擦移动箱子，到抓取位置后停带。夹爪靠摩擦抓取，不重写箱子位置、不附着箱子。随机化仅覆盖初始位置、4.4–5 cm 尺寸、35–65 g 质量；三个物体颜色顺序为红、蓝、红。

成功要求：颜色箱正确、旋转后的物体完整落在箱内、处于箱底和箱沿之间、线速度低于 0.025 m/s、角速度低于 0.35 rad/s、曾提起超过 8 cm、曾由传送带搬运超过 5 cm、夹爪打开并已撤离。

## 安装与存储

- 代码：`/home/ybyang/code/projects/physical-demo-lab`。
- 数据根目录：`/data1/ybyang/physical-demo-lab-runtime`，本次结束约 44 GB。
- 独立环境：`venv/`；Python 3.12.13、Isaac Sim 6.0.1.0、PyTorch 2.11.0+cu128。
- 系统：Ubuntu 22.04，NVIDIA 驱动 595.71.05，RTX 5880 Ada。测试使用空闲的物理 GPU 2 或 7，刚体动力学和控制缓冲区在 CPU 上。
- 下载、Kit/RTX/CUDA 缓存、临时文件、安装日志和仿真输出均放在上述 Data1 根目录。原 `/data0/ybyang/physical-demo-lab-runtime` 仅保留指向 Data1 的兼容符号链接，不存放第二份环境。
- `uv pip check`：171 个已安装包兼容；精确包列表保存在数据根目录的 `packages.freeze.txt`。

为了避免重复下载，安装时从服务器已有 SDK 中只读复制了三个完全相同版本的扩展缓存发行包；逐文件验证 RECORD SHA-256，80,068 个文件共 16.318 GB。没有复用旧解释器、旧 PyTorch 或修改旧环境。校验记录为数据根目录的 `logs/extscache-reuse.json`。普通依赖、固定哈希的官方 PyTorch wheel 和 NVIDIA SDK 安装来源见 `scripts/setup_server.sh`。

## 本次运行账本

以下路径均相对数据根目录的 `outputs/`。

| 运行 | 结果 | 证据位置 |
| --- | --- | --- |
| 单物体初测 | 失败：停带时休眠的箱子未被后续表面速度唤醒 | `smoke-001/` |
| 单物体修复验证 | 通过：关闭箱子的休眠阈值后，真实搬运并提起 | `smoke-002/` |
| seed 0，三物体，完整录像 | 物理通过，进程返回 0 | `three-001/` |
| seed 1–4，各三物体 | 4/4 通过，返回码均为 0 | `eval-seeds-1-4/summary.json` |
| seed 5、6，各三物体 | 2/2 通过，返回码均为 0 | `eval-seeds-5-9/summary.json` |
| seed 7 首次三物体运行 | 物理结果为真，但退出挂起；人工终止自己的进程，返回 143，整次运行记失败 | `eval-seeds-5-9/seed-7/`、该批次 `summary.json` |
| seed 8、9，各三物体 | 使用退出修复，2/2 通过，返回码均为 0 | `eval-seeds-5-9/summary.json` |
| seed 7 重跑 | 使用退出修复，通过，返回码为 0 | `eval-seed7-retry/summary.json` |
| 强制步数不足的负向检查 | `success=false`、`step_budget_exhausted`，实际返回 2 | `exit-gate-001/` |

seed 7 失败日志含渲染器 `Out of resource descriptors!`，物体分拣已完成但完整退出未完成。修复在刷完轨迹、结果、图像和视频后使用 SDK 的 standalone 快速退出接口，并显式传递退出码；不再重新进入 stop/render 回调。此前默认快速退出还可能把失败抹成返回码 0，负向检查确认了非零失败码得到保留。该修复不构成所有渲染器资源问题已解决的保证。

原失败输出未覆盖；重跑使用独立目录。三物体运行共 11 次，10 次正常成功、1 次退出故障。最终每个 seed 选取一次正常成功结果；预备的两个单物体测试和负向检查不纳入此计数。

## 独立复核与录像

[audit-final.json](audit-final.json) 对最终 10 个 seed 逐一复核：

- 运行时源码快照与记录的 SHA-256 一致。
- 每个控制物理步的编号与仿真时间连续，帧数与结果一致。
- 从记录的最终物体状态重新计算所有物理检查，与原结果一致。

该审计检查的是轨迹与物理证据，不单独检查进程退出。进程正常完成另由各批次 `summary.json` 的返回码确认；seed 0 的返回码由当次启动进程直接确认。

最终集合包含两个源码快照版本：`8c6c6be` 和 `3cbf2ed`。两者控制逻辑相同，后者增加异常打印、退出监控与退出码修复。因此审计中的 `single_controller_hash=false` 实际表示完整 demo 源文件哈希不同，不能解释成一次固定源码的全量评测。

seed 0 录像为 `three-001/video.mp4`：实际仿真渲染，960×720、30 fps、57.33 秒；记录 3,439 个控制物理步，仿真约 57.32 秒，控制循环墙钟约 129.92 秒（不含启动）。对应 `preview.png`、`final.png`、`manifest.json`、`trajectory.jsonl`、`events.jsonl`、场景和源码快照均在同一目录。完整 stdout/stderr 位于其同级 `.console.log`。

验证器两组单元测试通过，包括成功样例和九项失败条件。每次运行的实际参数和源文件仍以独立输出目录为准。

## 复跑

在服务器的代码目录中运行；输出目录必须不存在。先确认 GPU 空闲：

```bash
bash scripts/run.sh --gpu 2 --seed 0 --objects 3 \
  --output /data1/ybyang/physical-demo-lab-runtime/outputs/seed-0-next
```

批量复跑使用 `python3 scripts/evaluate.py --root <新的完整目录> --gpu 2`。录像与大体积轨迹不进入 Git；仓库保留程序、报告与小型审计结果。

尚未实现视觉识别、动态不停带抓取、学习策略或复杂障碍规划。任务参考的是用户选定的流水线短视频封面，没有完整原视频动作轨迹，不能声称逐动作复刻。
