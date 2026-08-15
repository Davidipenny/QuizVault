# Windows 发布验收

## 自动检查

在干净的 Windows 10 或 Windows 11 x64 环境中执行：

```powershell
./scripts/setup.ps1
cd web
pnpm test
pnpm build
pnpm run test:e2e:install
pnpm test:e2e
cd ..
./scripts/build-installer.ps1
./scripts/validate-installer.ps1
```

`validate-installer.ps1` 使用唯一临时安装目录和数据目录，静默安装后在无外部网络请求的模式下启动两次，检查 token、静态资源、Alembic 初始化、SQLite 备份恢复和跨启动数据保留，再静默卸载。

构建前必须从 WebView2 官方离线链接取得 x64 安装程序，并将发布时固定的 SHA-256 传给 `scripts/fetch-webview2.ps1`。该脚本记录已验证哈希，`build-installer.ps1` 会在打包前再次校验。

## 人工检查清单

- 安装程序显示正确产品名且可选择桌面快捷方式。
- 首次启动、退出和再次启动均成功，未完成会话可继续。
- 普通模式提交前看不到答案；背题模式“查看答案”不产生答题记录。
- 两空及以上填空题输入框数量正确，未做题筛选可用。
- 导出备份、恢复备份和 Excel 模板下载在桌面 token 模式下成功。
- 断开网络后重复启动、刷题、备份和恢复仍可完成。
- 卸载后程序目录被移除，用户数据目录按设计保留。
