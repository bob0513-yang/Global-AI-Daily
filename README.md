# Global AI Daily 全球 AI 资讯日报

本项目在 Mac 本地运行：浏览器首页加载 `data/latest.json`，Python 脚本读取公开 RSS，按日期生成 JSON 日报和独立 HTML 历史页面。示例新闻来自官方发布页面，示例日期为 2025 年，避免把旧新闻伪装成今日消息。

## 本地启动

需要 Python 3.9+，不依赖第三方 Python 包。

```bash
cd /path/to/Global-AI-Daily
python3 -m http.server 8000
```

浏览器访问 <http://localhost:8000>。不要直接双击 `index.html`，浏览器的本地文件安全策略会阻止 JSON 加载。

初次使用可以载入已核实的演示日报：

```bash
python3 scripts/update_daily.py --demo
```

## 每日更新

```bash
python3 scripts/update_daily.py
```

脚本优先取最近 24 小时的 RSS 项目，若没有结果则扩展到 72 小时。来源和栏目在 `config/sources.json` 配置。联网时会尝试逐源抓取；RSS 不可用会记录警告并继续其他来源。脚本保留同日已有内容，去掉相同 URL，并写入 `data/news/YYYY-MM-DD.json`、`data/latest.json` 与 `data/archive/YYYY-MM-DD.html`。历史 JSON 不会被其他日期覆盖。

可用 `python3 scripts/update_daily.py --hours 72` 指定时间窗。单独重新生成某日独立 HTML：

```bash
python3 scripts/generate_html.py 2025-08-07
```

更新后首页默认展示 `data/latest.json`。按日期查看历史数据可打开 `data/news/YYYY-MM-DD.json`，历史 HTML 可直接打开 `data/archive/YYYY-MM-DD.html`。

## 中文翻译与摘要

未配置模型 API 时，采集结果保留原文标题，并标记中文摘要“待生成”，不伪造译文。设置兼容 OpenAI Chat Completions 的服务后，自动生成简体中文标题、摘要、亮点和影响分析：

```bash
export AI_API_KEY="你的 API 密钥"
export AI_API_BASE_URL="https://api.openai.com/v1/chat/completions"
export AI_MODEL="gpt-4o-mini"
python3 scripts/update_daily.py
```

摘要是模型生成内容，应以原始来源为准。API Key 仅通过环境变量传入，不写入项目文件。

## 自动定时运行（macOS launchd）

编辑 `~/Library/LaunchAgents/com.global-ai-daily.update.plist`，把路径替换为此项目的绝对路径：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.global-ai-daily.update</string>
  <key>ProgramArguments</key><array><string>/usr/bin/python3</string><string>/项目绝对路径/scripts/update_daily.py</string></array>
  <key>WorkingDirectory</key><string>/项目绝对路径</string>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>/tmp/global-ai-daily.log</string>
  <key>StandardErrorPath</key><string>/tmp/global-ai-daily-error.log</string>
</dict></plist>
```

加载任务：

```bash
launchctl load ~/Library/LaunchAgents/com.global-ai-daily.update.plist
```

## 数据与来源说明

演示日报在 `data/news/2025-08-07.json`，采用 OpenAI 和 Google DeepMind 官方发布页作为原文来源。实时 RSS 源可以在配置文件中增删；发布机构的 RSS 地址可能变更，失败时会显示在终端警告中。RSS 元数据本身不足以写出可靠的新闻分析，所以没有模型 API 时脚本不会编造摘要、亮点或行业影响。

## 部署到 Hostinger Web Hosting

已为普通 Web Hosting 准备静态站点包：项目根目录的 `hostinger-upload.zip`。解压后，ZIP 根层直接包含 `index.html`、`favicon.svg`、`assets/` 和 `data/`，可直接放进站点的 `public_html`。源文件也在 `hostinger-upload/` 文件夹。

1. 在 Hostinger hPanel 打开 **Websites → Manage**，选择域名对应的网站。
2. 打开 **Files → File Manager**，进入该域名的 `public_html`。
3. 上传 `hostinger-upload.zip` 并在 `public_html` 中解压。确认 `index.html` 位于 `public_html/index.html`，不要留在额外的子目录里。
4. 打开域名验证首页。测试时若看到旧版本，尝试强制刷新浏览器或清除站点缓存。

普通 Web Hosting 提供静态文件托管，但本项目的 Python RSS/翻译更新脚本不能在该套餐上作为服务器任务运行。要更新线上日报：在 Mac 上运行 `python3 scripts/update_daily.py`，然后将新生成的 `data/latest.json`、`data/editions.json`、`data/news/` 和 `data/archive/` 上传并覆盖同名文件。更新时请保留已有日期文件，确保历史日报仍可查看。需要服务器无人值守地自动运行 Python 时，需改用 VPS 或其他支持 Python 定时任务的主机。

### 全自动流程：GitHub Actions → Hostinger 自动部署

仓库已包含 `.github/workflows/daily-update.yml`：每天北京时间 08:00（UTC 00:00）运行采集脚本，将日报数据提交到 `main`，并生成只包含静态网页的 `hostinger-deploy` 分支。Hostinger 连接该静态分支，检测到新提交后自动发布。Python 脚本和 API 设置不进入网站目录。首次配置需要你在 GitHub 和 Hostinger 账户中完成授权：

1. 在 GitHub 创建一个名为 `Global-AI-Daily` 的仓库，初始化分支使用 `main`。仓库可设为 Private。
2. 在 Mac 终端运行以下命令，将本地项目推送到新仓库。把地址替换成 GitHub 页面显示的仓库地址：

   ```bash
   cd /path/to/Global-AI-Daily
   git init -b main
   git add .
   git commit -m "Initial Global AI Daily site"
   git remote add origin https://github.com/你的用户名/Global-AI-Daily.git
   git push -u origin main
   ```

   如果项目已经是 Git 仓库，跳过 `git init`；如果已有 `origin`，用 `git remote -v` 检查，不要重复添加。
3. 在 GitHub 仓库打开 **Settings → Actions → General → Workflow permissions**，选择 **Read and write permissions** 并保存，让 Actions 可以把每日 JSON 归档提交回 `main`。
4. 在 GitHub 仓库打开 **Actions**，启用工作流。点开 **Update Global AI Daily → Run workflow**，手动运行一次以验证 RSS 和自动提交流程。定时任务有时会延迟几分钟。
5. 在 Hostinger hPanel 打开该域名的 **Manage site → Advanced → Git**，选择 **Connect with GitHub** 并授权访问这个仓库。选择 `Global-AI-Daily`、`hostinger-deploy` 分支，Root directory 设为 `public_html`，完成首次部署并开启 Auto-deployment。
6. 访问域名确认首页已显示 JSON 新闻。后续每天的 Actions 提交会触发 Hostinger 自动重新部署。`hostinger-upload.zip` 仍可用于首次手动上传或故障回退。

#### 可选：自动中文翻译与摘要

不配置模型 API 时，采集到的新闻会保留原文并注明摘要待生成。若要自动生成中文标题、摘要、亮点及影响分析，在 GitHub 仓库进入 **Settings → Secrets and variables → Actions**：

- 在 **Repository secrets** 新建 `AI_API_KEY`，值为模型服务密钥。
- 在 **Variables** 可选设置 `AI_API_BASE_URL`（完整 Chat Completions URL）和 `AI_MODEL`。

请勿把 API Key 写入仓库文件。每次定时运行会使用这些仓库设置调用兼容 OpenAI Chat Completions 的服务。

#### 手动触发与故障查看

在 GitHub **Actions → Update Global AI Daily → Run workflow** 可随时手动更新。失败时打开对应运行记录查看是哪一个 RSS 源或步骤报错；更新脚本会隔离单个来源故障。如果 24～72 小时内所有来源都没有新条目，脚本会保留当前线上日报不变。
