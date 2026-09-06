# 服务器 23：独立运行环境与 Data1 存储

验证于 2026-09-05 至 09-06；依据为
[首次验证报告](../../../reports/bootstrap-validation.md) 的安装、存储与运行账本，
以及现有 [安装脚本](../../../scripts/setup_server.sh) 和 [运行入口](../../../scripts/run.sh)。
版本是本次已验证组合，不表示未来最新版本。

- 连接别名：`xdlab23_yang`；代码在 `/data1/ybyang/physical-demo-lab`。
- 运行根目录：`/data1/ybyang/physical-demo-lab-runtime`。
  `venv/`、`cache/`、`tmp/`、`logs/`、`outputs/` 均在此目录下。
- 已验证：Python 3.12.13、Isaac Sim 6.0.1.0、PyTorch 2.11.0+cu128、
  驱动 595.71.05。`packages.freeze.txt` 保存精确版本；171 个包通过兼容检查。
- Mac 不执行本项目的 Isaac Sim；按用户 2026-09-06 的新约定，直接在 23 仓库开发、测试、commit 和 push，Mac 用于连接与观看结果。
- `/data0/ybyang/physical-demo-lab-runtime` 仅是迁移后保留的兼容符号链接。
  一些解释器路径可能仍依赖它；不要把该链接当作第二份 44 GB 环境，也不要随手删除。

## 安装经验

优先复用本项目已经验证的独立环境。需要重建时运行安装脚本，并把
`PHYSICAL_DEMO_RUNTIME` 指向新的 Data1 子目录；不要往别人的环境安装。
主 PyTorch wheel 固定官方来源与哈希，其余依赖按脚本所列镜像/NVIDIA 源安装。

首次安装曾因依赖元数据请求不支持 HTTP Range 而出现很慢的完整包下载。
本次采用固定官方 torch wheel + 普通依赖镜像完成安装；这是本次路径的经验，
遇到新的网络故障仍应先检查实际请求与日志，不能假设所有卡顿都来自同一原因。

已有完全相同版本的 SDK 扩展缓存可经 `scripts/reuse_extscache.py` 逐文件校验后复制。
本次校验复制 80,068 个文件、16.318 GB；来源环境只读，未复用其解释器或 PyTorch。
结果位于运行根目录 `logs/extscache-reuse.json`。

## GPU 与运行前检查

本次使用过物理 GPU 2 和 7，但编号不是空闲保证。每次先看当前 GPU 使用者和负载，
只选择空闲设备，不终止无关进程。`--gpu` 指定 RTX 渲染设备；本场景的刚体物理和
IK 缓冲区使用 CPU，防止控制数组无意落到默认 GPU 0。SDK 初始化仍可能接触其他设备。

运行必须使用新输出目录；旧的成功、失败和被中断记录均保留。Data1 使用量应按需检查，
不能通过清理别的项目或覆盖旧实验腾空间。

## 服务器不能直连 GitHub 时的安全同步

2026-09-06 初始化同步时，服务器的 HTTPS fetch 以 `GnuTLS recv error (-110)` 失败。
这只证明该次连接异常，不表示仓库不存在或访问凭据失效。不要通过整目录覆盖 `.git`
修复同步；它可能替换已有历史、引用和本地配置。

本次已验证的替代方式是：先确认两端工作区状态和共同基线，在本地用
`git bundle create <新文件> main ^<服务器已确认的提交>` 导出增量；只把该文件传到
Data1 的独立临时目录。服务器用 `git bundle verify <文件>` 检查前置提交，随后
`git fetch <文件> main`、`git merge --ff-only FETCH_HEAD`。任何基线缺失、分叉或
本地修改冲突都应停下，不使用强制重置或目录覆盖。

首次 bundle 约 19 KB，把服务器从 `48eb107` 快进到 `cc6aa4b`，之后双侧一致性、
完成检查和全部 11 项单元测试通过。本地状态 `.pipeline-state.json` 不进 Git，
只在目标不存在或已确认属于当前初始化时单独同步；它不是可移植的全局插件配置。

## 当前开发与发布约定

用户 2026-09-06 明确要求直接在 23 的项目仓库开发，把关键 TODO 留在仓库文档，
并在 23 commit、push。工作树为 `/data1/ybyang/physical-demo-lab`；
[项目 TODO](../../TODO.md) 是行动入口，`docs/demos.json` 仍仅记录有证据的物理完成范围。

每轮先检查远程工作树和当前提交；只改授权范围。报告、经验、待办和双端项目知识
更新完后，在 23 执行完成检查和测试，按文件路径暂存本轮改动、提交并推送。
遇到分叉、无关修改或认证问题时保留现场；不强推、不替换 `.git`，也不改回本地代推。

本轮只读连接检查中，原 HTTPS 路由在 25 秒限时内未返回；同仓库 SSH 的
`git ls-remote` 成功返回 `e9e391c7050ee50299326054bc1b43a31c5a7e2a`。
这是当次连通性证据，不证明 HTTPS 永久不可用。本轮可使用同一仓库的 SSH URL
进行服务器端推送；不需要复制凭据或改全局 Git 配置。上节增量 bundle 是历史同步
经验，不是当前“服务器开发、服务器推送”要求的默认替代方案。

## 2026-09-06：主仓库整体迁至 Data1

用户要求将整个 repo 放在 `/data1/ybyang/` 下。本次已将主工作树及完整 `.git`
从 `/home/ybyang/code/projects/physical-demo-lab` 移到
`/data1/ybyang/physical-demo-lab`；旧路径仅为指向新位置的兼容符号链接，
不是保留在 home 分区的第二份仓库。当前文档和项目知识使用新路径；
[首次验证报告](../../../reports/bootstrap-validation.md) 中的旧路径是历史执行记录，未重写。

迁移前主仓库占 2744 KiB（约 2.7 MiB，含约 1.8 MiB 的 Git 元数据）；
home 分区 98% 已用，Data1 约有 2.7 TiB 可用。因此本次仅将约 2.7 MiB 移出 home，
不是释放几十 GB，也不会减少服务器总数据量。环境和产物早已在
`/data1/ybyang/physical-demo-lab-runtime`：本次可读目录统计约 55 GiB，
其中一个 SDK 截图目录无读取权限，故该数值不是完整精确总量；未更改其权限或内容。

安全与验证记录：

- 主仓库迁移前为干净的 `9988144`；只移动到此前不存在的目标，不合并或覆盖其他目录。
- 已存在的关联工作树 `/data1/ybyang/physical-demo-lab-runtime/worktrees/isaac-ports-20260906`
  留在原位，分支 `codex/isaac-ports`、提交 `e2bed49` 和其未提交改动均保留。
  执行 `git worktree repair` 后，两份工作树仍可解析，未暂存或提交该工作树的开发内容。
- 在更新本文档前，两份工作树的 tracked/nonignored 文件内容汇总校验均与迁移前相同；
  主工作树为 `82a22d12508cd3d8528d5246301f12ee1c08edbd925f6c8de68f778b363dc41b`，
  关联工作树为 `2dd211736593aaaa169b2dc4cd511226e715ebdccd579c45837744da9ff06502`。
  校验方式为按 `git ls-files --cached --others --exclude-standard -z` 输出顺序，
  汇总各文件 SHA-256 后再计算 SHA-256；Git 对象另经 `git fsck --full` 检查。
- 新路径下 37 项测试、六项完成记录与双端项目知识一致性检查通过；
  两个运行入口的 `--help` 正常。本次未重新执行物理仿真，也未改旧结果或原始运行路径。
- 旧链接不应当被当作需再迁移的仓库副本。若将来移除兼容入口，应先核对关联工作树
  和历史启动路径；如需回迁，先停止相关任务并核验两边状态，不直接覆盖现有目录。
