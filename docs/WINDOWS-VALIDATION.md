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

`validate-installer.ps1` 使用唯一临时安装目录和数据目录，静默安装后启动两次（程序本身只访问 127.0.0.1，脚本并未强制断网），检查 token、静态资源、Alembic 初始化、SQLite 备份恢复和跨启动数据保留，再静默卸载。

构建前需取得 WebView2 x64 离线安装包（约 200MB；注意微软没有常青离线直链，`LinkId=2124703` 只是约 2MB 的联网 bootstrapper）。推荐用 winget 获取固定版本，计算 SHA-256 后传给 `scripts/fetch-webview2.ps1`：

```powershell
winget download --id Microsoft.EdgeWebView2Runtime -e --architecture x64
# 从下载输出目录计算哈希后：
./scripts/fetch-webview2.ps1 -ExpectedSha256 <SHA256> -Source <下载得到的exe路径>
```

该脚本会校验哈希与文件大小并记录，`build-installer.ps1` 会在打包前再次校验。

## 自动化验证记录

- 2026-10-28（Windows 11 x64，Inno Setup 6.7.3，WebView2 156.0.4314.50，SHA256 `1C401B32…A39BEA`）：`build-installer.ps1` 产出 `dist/QuizVault-Setup.exe`，`validate-installer.ps1` 静默安装、两次冒烟启动（含跨启动数据保留检查）与静默卸载全部通过。

## 人工检查清单

以下 8 项尚无签核记录（自动化部分见上方记录）：

- 安装程序显示正确产品名且可选择桌面快捷方式。
- 首次启动、退出和再次启动均成功，未完成会话可继续。
- 普通模式提交前看不到答案；背题模式“查看答案”不产生答题记录。
- 两空及以上填空题输入框数量正确，未做题筛选可用。
- 导出备份、恢复备份和 Excel 模板下载在桌面 token 模式下成功。
- 断开网络后重复启动、刷题、备份和恢复仍可完成。
- 卸载后程序目录被移除，用户数据目录按设计保留。
