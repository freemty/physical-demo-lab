# demo003：齿轮插轴验证账本

2026-09-06。规格见 [任务定义](../docs/specs/demo003-gears.md)。最终三个独立 seed
均通过原始物理判定与 [独立审计](demo003-audit.json)，该基础版完成。

## 范围与实现

Franka 通过实际夹持轮毂，移动具有中心孔的复合刚体齿轮，再插入固定轴并释放。
脚本使用已知零件位姿和 IK；没有改写零件位置、抓取附着或学习策略。
矩形近似齿具有明显装配间隙，不是精密渐开线齿轮，也没有受载传动测试。
参考仅覆盖原作者标题/封面，不是完整原视频的逐动作复刻。

## 尝试账本

所有输出根目录为服务器 23 的 `/data1/ybyang/physical-demo-lab-runtime/outputs/demo003/`。
每次均保留独立源码快照、调用、场景、逐步状态与外部进程返回码。

| 运行 | 源码提交 | 观察结果 |
| --- | --- | --- |
| `seed0-attempt1` | `4df4400` | 返回 2。成功提起 28.5 cm，但终态高度高出目标 11.8 mm，姿态倾斜与齿相位失败；不能算装配成功。 |
| `seed0-attempt2` | `fc6107e` | 返回 1。进入 align 后 NumPy float32 姿态值无法写入 JSON，中止；没有最终物理判定。 |
| `seed0-attempt3` | `b5958b5` | 返回 0，全部八项物理检查通过。1,420 步、23.667 仿真秒，完整视频 710 帧。 |
| `eval-1-2/seed-1` | `b5958b5` | 返回 0；全部检查与独立审计通过。 |
| `eval-1-2/seed-2` | `b5958b5` | 返回 0；全部检查与独立审计通过。 |
| `negative-step-budget` | `b5958b5` | 强制一步预算返回 2；没有搬起、对中或落座；负向审计返回失败。 |

第一轮轨迹中，above_axle 阶段零件接近竖直，插入阶段才明显倾斜。
几何审查还发现齿顶半径 43.5 mm 与邻轮齿根半径 37 mm 之和超过原 80 mm 中心距。
修订将中心距改为 81.5 mm、矩形齿宽 5 mm 改为 3 mm，并增加完整姿态反馈。
这些改动共同进入第二、三次运行，不能把后续结果只归因于单一改动。

记录器本身未改变，避免使已完成的收银验证失效。第二次问题在任务入口将命令值显式
转换成 Python float 修复；异常的堆栈与中断轨迹仍保留在原目录。

## 验证与重放

最终三次使用同一入口、几何、验证器、记录器及启动器字节版本。
最终 XY 偏差约 1.50–1.55 mm，根节点高度均为 0.730000 m；齿相位误差
0.00287–0.00341 rad，均满足运行前阈值。审计重新从 1,420 个连续物理帧计算
最大提起高度、最终位置姿态、速度及夹爪释放距离，并核对源码快照与真实返回码。
它不是仅复制 `result.json` 中的 true。

```bash
python3 scripts/run_task.py gear_assembly --seed 0 --gpu 7 --output <全新输出目录>
python3 scripts/evaluate_task.py gear_assembly --seeds 1 2 --gpu 7 --root <全新批次目录>
python3 scripts/audit_task.py --runs <seed0目录> <seed1目录> <seed2目录> --output <新审计文件>
```

本地视频检查：960×720、30 fps、23.667 秒；抽查 7 秒夹持提起、16 秒插入及最终
释放画面。未逐帧人工检查整段视频。上述运行的全量媒体和轨迹在 Data1，
便于查看的 seed 0 视频保存在本地 `outputs/gears/video.mp4`。

最终 3/3 是修订后的多初态验证，不是首次尝试 3/3；另有一次物理失败和一次
记录器输入类型异常。19 项单元测试含几何失败判定与完整四元数修正检查。

复用了 [进程证据流程](../docs/knowhow/toolchain/checkout-and-process-evidence.md)
和 [独立环境](../docs/knowhow/infrastructure/server23-isaac-sim.md)，新增
[齿轮落座与姿态经验](../docs/knowhow/debug-solutions/gear-seating-and-pose.md)。
