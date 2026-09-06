# 送餐视觉样板

2026-09-06，最终展示实现 `b844024`。彩色餐厅、包装、送餐车外壳、灯光与三个镜头已完成，
真实仿真视频为 1280×720、30 fps、1487 帧、49.567 s，完整解码通过。
本地副本：`outputs/restaurant-showcase/video.mp4`。原灰白基线视频完整保留。

## 实测而非换图

最终运行位于 `/data1/ybyang/physical-demo-lab-runtime/outputs/demo006-showcase/final-1/`，
seed 0，2974 物理步/49.5667 s，外部进程返回 0，原九项送餐谓词全部通过。
[独立审计](demo006-showcase-audit.json) 同时确认：

- 原入口、车体、验证器、姿态 helper、记录器与启动器的已验证指纹未改变。
- 373 个新增显示图元不带碰撞/刚体 API；装饰前后原物理属性表完全相等。
- 与原 `demo006/development-2` 的 2974 帧逐一比较，控制命令、机器人状态、
  物体步前/步后状态、阶段、物理步及仿真时钟全部精确一致。
- 三个相机事件对应装餐、行驶、最终停车阶段；没有倍速、跳过执行或生成式视频。

这是最终外观的一次完整 seed 0 验证，不冒称三种外观初态验证；原物理基线的三种初态
证据仍在 [原报告](demo006-restaurant.md)。开发短预算和早期画面另见
[开发记录](demo006-showcase-development.md)。

2026-09-06 文档复核补充：现有审计脚本的总通过标记尚未纳入基线比较结果；
本报告的“一致”依据是审计文件中明确的 2974/2974 和
`baseline_trajectory_comparison.all_physical_fields_exact: true`，
不只是进程返回 0。详见 [已知缺口与复用检查](../docs/knowhow/toolchain/simulation-presentation-layer.md)。
该缺口已进入 [待办](../docs/TODO.md)，本轮未修改代码或新增仿真结果。

## 展示变化与边界

使用木色、青绿、暖白与珊瑚色包装，明确表面颜色、粗糙度和金属度；补充柜台木条、地砖、
餐具、植物、挂画与细椅腿。旧底盘/物体的碰撞、质量、驱动不改；外壳、包装盖与布景不可交互，
不会因此获得液体、餐具操作或真实餐厅碰撞能力。仍是固定臂装餐、独立车送至桌边，不含卸餐。

主光改从房间开放前侧照入，环境光 650、主光 1000，颜色按 sRGB 转线性值输入。
装餐镜头聚焦抓取区域，行驶镜头保留完整路径，停车近景突出两件餐品。
相机切换有渲染读回延迟，缩略图在新镜头 12 步后保存；没有额外推进物理时钟。
实际查看装餐预览、行驶全景及最终近景；这是抽样人工视觉检查，不是逐帧人工检查。

37 项项目测试与原六项收尾检查通过。新展示文件指纹：

| 文件 | SHA-256 |
| --- | --- |
| `demos/restaurant_appearance.py` | `11af42944b8a05f9614b69ec6b6da0d8d91a61b10cbf5fc85056ba959b3c90ee` |
| `demos/restaurant_showcase.py` | `24b7353f34b3d53e715411948317b42f5e9f4449266be013065570b476cb02d3` |
| `scripts/run_showcase_task.py` | `5647969e150b40fc3a47f7d7f062bce63cbe62dc5e1ff8a31215818bf7df4a7c` |

```bash
python3 scripts/run_showcase_task.py --seed 0 --gpu 6 --width 1280 --height 720 --output <新目录>
python3 scripts/audit_showcase_task.py --runs <新目录> --baseline <原基线目录> --output <新审计文件>
```

LabMate 将本次发现整理为 [仿真展示层经验](../docs/knowhow/toolchain/simulation-presentation-layer.md)。
本次交付的是送餐样板；其他五项的外观尚未统一，第七项草稿仍暂停、第八项未开始。
