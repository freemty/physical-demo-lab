# LabMate 初始化与经验收尾流程验收

日期：2026-09-06。范围：项目初始化、已有经验回填、后续完成检查；本次没有新跑一个仿真 demo。

使用已安装 LabMate 0.11.0 的 `init-project`、`update-docs` 与 `update-project-skill`
流程。项目参数为 `general / both`、`physical-demo-lab`、robotics simulation；
计算环境仍是服务器 23，运行根目录仍在 Data1。

- 初始化先 plan，再 apply、check；无现有指令冲突。骨架创建 14 个路径，追加 `.gitignore`。
- 补充项目规则、双侧 project-skill、八项进度表、四篇 knowhow/收尾文档和文档入口。
  原始实验报告、视频、成功/失败运行目录和模拟器代码均未改动。
- 再次 apply 的 15 项全部 skip，确认初始化不会覆盖已填好的项目知识。
- LabMate check：missing 0、errors 0；项目技能格式检查与双侧镜像检查通过。
- `scripts/check_project.sh`：11 项单元测试通过（9 项收尾检查 + 2 组物理验证器测试）。
  本地文档链接检查无缺失。
- `check_closeout.py --demo demo001` 接受已有基础版记录；
  `--demo demo002` 返回 1，说明未开始项不能通过完成验收。
  测试同时验证了缺经验、缺报告、实现指纹过期、路径越界和重复 ID 会被拒绝。

当前进度仍为：仅 `demo001` 的限定基础版完成，其余七项未开始。
下个建议推进项为 `demo002` 超市收银；初始化本身没有自动启动它。

运行约定见 [收尾流程](../docs/knowhow/runbooks/demo-closeout.md)。文档更新是每次执行者的
必需步骤，检查器只验证记录完整性与实现指纹，不能自动核实经验真假。本次没有安装全局
Stop hook、后台自动写作、定时任务或分支保护，也未更改任一 host 的全局插件配置。
