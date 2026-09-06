# 项目文档与逐项进度

这里是每个 demo 开始前查经验、结束后写回经验的入口。LabMate 0.11.0
已按 `general / both` 初始化；采用工程型骨架，不引入尚未需要的论文、训练或 viewer 模板。

[查看 README 图片 Gallery](../README.md#demo-gallery)：七项已验证基础版的真实截图与报告入口。

## 当前任务

本轮已完成：[20 件 Isaac 城堡](../reports/demo009-castle20.md)，固定版本六种子 6/6；
200/1000 件暂停。具体关卡列在 [项目 TODO](TODO.md)。

| ID | 任务类别 | 当前状态 |
| --- | --- | --- |
| demo001 | 流水线颜色分拣 | 基础版已验证并归档；已知位姿、停带抓取 |
| demo002 | 超市收银 | 基础版已验证并归档；三种初态、模拟扫描与装袋 |
| demo003 | 齿轮拼装 | 基础版已验证并归档；三种初态插轴、落座、释放 |
| demo004 | 双臂搭积木 | 基础版已验证并归档；双臂轮流搭桥、持续支撑 |
| demo005 | 灵巧手拧瓶盖 | 基础版已验证并归档；单手、等效螺纹、三质量初态 |
| demo006 | 餐厅服务 | 基础版已验证并归档；固定臂装餐、独立轮式车送达 |
| demo007 | 双臂拼乐高 | 几何/规格草稿保留，未执行；送餐样板已交付，待继续 |
| demo008 | 人形机器人室内行走 | 未开始 |
| demo009 | 20 件 Isaac 城堡 | 已完成；固定版本六种子 6/6，逐件抬升、脱手稳定与视频检查通过 |

机器可检查的状态与已验证范围在 [demos.json](demos.json)。编号沿用本项目提出的
先流水线、收银、齿轮、积木、瓶盖的实施顺序，其余三类列为后续候选；不是原作者的发帖顺序，
也不意味着这些任务都已排好最终技术方案。一次只推进一个，方案或难度变化时明确调整顺序。

送餐样板已交付：[实际视频与验证报告](../reports/demo006-restaurant-showcase.md)。
这不代表用户已验收外观方向，也不代表其他五项已完成外观升级；原六项物理范围保持不变。

后续关键工作、优先级建议、依赖和完成条件统一见 [项目 TODO](TODO.md)。
按用户 2026-09-06 的约定，在 23 的 `/data1/ybyang/physical-demo-lab` 直接开发、测试、commit 和 push；
Mac 只作为连接与结果查看端。不得从另一份临时仓库静默覆盖远程开发进度。

参考范围来自 2026-09-05 对用户指定的
[小红书主页](https://www.xiaohongshu.com/user/profile/667d2c7d0000000007007c52)
的标题和封面检查，共八类演示。未取得完整视频或原作者源码；这里是任务类别清单，
不证明原作者采用何种控制方式，也不是逐动作复刻规格。开始每个任务时须明确可取得的参考范围。

## 先读什么

- 环境和存储：[服务器 23 与 Isaac Sim](knowhow/infrastructure/server23-isaac-sim.md)。
- 已验证的调试经验：[传送带休眠与仿真退出](knowhow/debug-solutions/conveyor-and-teardown.md)。
- 结果与证据：[轨迹、验证器与复用边界](knowhow/toolchain/evidence-and-verification.md)。
- 每次完成时：[demo 收尾流程](knowhow/runbooks/demo-closeout.md)。
- 第一项实测：[完整验证报告](../reports/bootstrap-validation.md) 和
  [独立审计结果](../reports/audit-final.json)。
- 第二项实测：[收银报告](../reports/demo002-checkout.md) 与
  [扫描/进程证据经验](knowhow/toolchain/checkout-and-process-evidence.md)。
- 第三项实测：[齿轮报告](../reports/demo003-gears.md) 与
  [几何干涉/完整姿态经验](knowhow/debug-solutions/gear-seating-and-pose.md)。
- 第四项实测：[双臂积木报告](../reports/demo004-dual-blocks.md) 与
  [参与/持续支撑证据](knowhow/toolchain/dual-arm-support-evidence.md)。
- 第五项实测：[开盖报告](../reports/demo005-bottle-cap.md)、
  [包含失败的开发账本](../reports/demo005-bottle-cap-development.md) 与
  [Allegro 安装/接触/时钟经验](knowhow/debug-solutions/allegro-mount-contact-clock.md)。
- 第六项实测：[送餐报告](../reports/demo006-restaurant.md)、[开发账本](../reports/demo006-restaurant-development.md) 与
  [移动载具证据](knowhow/toolchain/mobile-carrier-evidence.md)。
- 第九项实测：[20 件城堡开发账本](../reports/demo009-castle20-development.md)，
  [有界控制与原生接触审计](knowhow/debug-solutions/castle-bounded-control-and-lift-evidence.md)。
- 展示层：[送餐样板开发记录](../reports/demo006-showcase-development.md) 与
  [材质、灯光、镜头和复用验收清单](knowhow/toolchain/simulation-presentation-layer.md)。

## 写到哪里

任务范围与验收条件放 `docs/specs/`；每次重要阶段的结果和失败账本放 `reports/`；
可复用的环境、调试和操作经验放 `docs/knowhow/`。长期稳定的新发现再进入两个 host 的
`project-skill` 简短地图。原始视频、逐步轨迹、安装缓存仍留在服务器 Data1，不进入 Git。

维护目标是“每完成一项，下一项能直接复用已验证的经验”。不是每次重复整份日志，
也不是把未经验证的猜测写成事实。没有新增经验时，在该次报告明确写出复用了哪些既有条目，
不要为了通过检查编造新结论。
