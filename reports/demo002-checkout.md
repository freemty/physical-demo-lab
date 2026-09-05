# demo002 超市收银：基础版验证

2026-09-06。[运行前任务规格](../docs/specs/demo002-checkout.md)。

结果：seed 0、1、2 三个独立进程均完成，返回码 0；9 个商品全部经由传送带接触搬运、
夹爪摩擦提起、扫描区检测、装袋释放。每次三个不同 SKU 各计一次，合计 1,560 模拟分。
三次均首轮通过，没有隐藏重跑；另有一次故意的一步预算失败，不纳入成功样本。

范围是已知位姿、已知 SKU 的停带脚本基线，不是视觉条码识别，不涉及真实支付，
不是学习策略或完整参考视频复刻。价格和扫描范围是本项目预先设定的模拟规则。

## 运行证据

数据根目录为 `/data1/ybyang/physical-demo-lab-runtime/outputs/demo002/`。

| 运行 | 目录 | 返回码 / 结果 |
| --- | --- | --- |
| seed 0，录像 | `seed0-attempt1/` | 0，通过 |
| seed 1 | `eval-1-2/seed-1/` | 0，通过 |
| seed 2 | `eval-1-2/seed-2/` | 0，通过 |
| 一步预算负向检查 | `negative-step-budget/` | 2，步数不足，独立审计同样拒绝 |

每次同级 `.process.json` 记录实际调用和进程返回码，`.console.log` 保留 stdout/stderr。
各目录包含源码快照、场景、初始条件、每个控制物理步的前后物体状态、关节/末端与目标、
阶段和扫码事件、receipt.json、result.json、final.png。失败也保留同等可取得的证据。

[独立审计](demo002-audit.json) 从连续轨迹重新计算扫描区占用 12 帧、SKU 去重、金额、
最大提起量、传送带搬运和最终装袋物理状态，并检查源码快照及实际进程退出。
三次均通过。控制器、共享记录器、任务验证器与启动器在这三次测试中未改动。

seed 0 录像 `seed0-attempt1/video.mp4` 为实际渲染：960×720、30 fps、约 73 秒。
4,379 个控制物理步、72.983 仿真秒，控制循环墙钟约 164.88 秒（不含启动）。
已查看初始画面、约 14 秒的实际扫码、约 22 秒的装袋和最终释放画面。
本地成片在 `outputs/checkout/video.mp4`，原始完整轨迹仍留在 Data1。

## 可复用经验与运行方式

复用了第一项的传送带防休眠、CPU 控制缓冲区、真实摩擦抓取和显式退出码。
新增经验见 [扫描、记账与独立进程状态](../docs/knowhow/toolchain/checkout-and-process-evidence.md)。
没有为了通过结果而改动已声明的扫描/物理阈值，也未改写原流水线 demo 的源码或历史结果。

```bash
python3 scripts/run_task.py checkout --gpu 7 --seed 0 \
  --output /data1/ybyang/physical-demo-lab-runtime/outputs/demo002/new-run
```

先确认指定 GPU 空闲，输出目录必须不存在。新启动器与审计器是按任务显式接入的接口，
不能把没有实现独立语义审计的其他任务当作自动通过。
