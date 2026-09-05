# 服务器 23：独立运行环境与 Data1 存储

验证于 2026-09-05 至 09-06；依据为
[首次验证报告](../../../reports/bootstrap-validation.md) 的安装、存储与运行账本，
以及现有 [安装脚本](../../../scripts/setup_server.sh) 和 [运行入口](../../../scripts/run.sh)。
版本是本次已验证组合，不表示未来最新版本。

- 连接别名：`xdlab23_yang`；代码在 `/home/ybyang/code/projects/physical-demo-lab`。
- 运行根目录：`/data1/ybyang/physical-demo-lab-runtime`。
  `venv/`、`cache/`、`tmp/`、`logs/`、`outputs/` 均在此目录下。
- 已验证：Python 3.12.13、Isaac Sim 6.0.1.0、PyTorch 2.11.0+cu128、
  驱动 595.71.05。`packages.freeze.txt` 保存精确版本；171 个包通过兼容检查。
- Mac 不执行本项目的 Isaac Sim；它用于代码编辑与观看导回的结果。
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
