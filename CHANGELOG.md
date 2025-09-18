# Changelog

## v0.2.0

- 新增 GitHub Actions 工作流，云编译 Windows 可执行文件（PyInstaller）
- UI：日志级别下拉开关；椰子云密码输入掩码；启动自动置顶与聚焦
- 自动接码：增加 YZY 返回调试日志（可由 UI 控制等级）
- 修复自动接码 lambda 作用域异常（exc 清理问题）
- 申诉提交：
  - 新增提交对话框、字段持久化与文件选择
  - 提交前校验“申诉手机号”是否可提交
  - 记录提交事件并展示“最近申诉手机号”列
  - 历史详情持久化到 `data/submissions.json`

