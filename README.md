# 角色与场景资产库

维护 AI 出图素材的工具，分**角色资产库**与**场景资产库**两个模块（顶部切换）：
增删改查、多维筛选、AI 写提示词、调用图片接口生成图片、批量重新生成。

## 形态

- 前端网页：React + Vite + TypeScript + Ant Design
- 后端：本地 Python 脚本（FastAPI），数据存 SQLite，图片存本地磁盘
- 数据库与图片都在 `backend/data/` 下，整个文件夹可直接拷贝备份

## 启动

```bash
./start.sh
```

首次运行会自动建后端虚拟环境、装前后端依赖。启动后打开 **http://localhost:5180**。

手动分开启动：

```bash
# 后端
cd backend && .venv/bin/python main.py        # http://localhost:8000

# 前端
cd frontend && npm run dev                    # http://localhost:5180
```

## 数据导入

- 角色：`角色资料库数据.csv`（76 个角色）已导入。重导：`python import_csv.py --force`
- 场景：55 个高频场景由脚本灌入。重灌：`python seed_scenes.py --force`

```bash
cd backend
.venv/bin/python import_csv.py --force      # 重导角色
.venv/bin/python seed_scenes.py --force     # 重灌场景
```

## AI 功能配置

写提示词、生成图片走 ZenMux，配置在 `backend/.env`（已隔离，不读取其他项目）。
固定项已预填，只需填两处：

```
ZENMUX_API_KEY=    ZenMux 的 API Key（必填，图片与文字共用）
TEXT_MODEL=        写提示词的文字模型，如 openai/gpt-4o
```

其余为 ZenMux 固定项，一般无需改动：

```
TEXT_BASE_URL=https://zenmux.ai/api/v1          文字走 OpenAI 兼容端点
IMAGE_BASE_URL=https://zenmux.ai/api/vertex-ai  图片走 Vertex-AI 端点
IMAGE_MODEL=openai/gpt-image-2
```

- 文字（写提示词）：OpenAI SDK 调 ZenMux 的 OpenAI 兼容端点
- 图片（生成图片）：google-genai SDK 调 ZenMux 的 Vertex-AI 端点

未配置时 AI 功能不可用，其余功能（增删改查 / 筛选 / 搜索 / 图集 / 上传）正常。
改完 `.env` 需重启后端生效。

## 部署到 benchmark.jy-video.cn

当前应用前端使用同源相对路径访问 `/api` 与 `/images`，部署时不用在前端写死 IP。生产域名为 `https://benchmark.jy-video.cn`。推荐形态是：

- Nginx 监听 `80/443`，`80` 用于证书续期与跳转 HTTPS，`443` 静态托管 `frontend/dist`
- Nginx 将 `/api/` 与 `/images/` 反代到本机后端 `127.0.0.1:8000`
- FastAPI 后端用 systemd 常驻运行，数据与图片通过 `BENCHMARK_ASSET_DATA_DIR` 写到 `/data/benchmarkAsset`

### 首次配置 SSH

如果本机还没有部署用的 SSH key，先生成一把，文件名可以按团队习惯自定：

```bash
ssh-keygen -t ed25519 -f ~/.ssh/<your_deploy_key> -C "benchmark-asset-deploy"
```

把公钥写入服务器。第一次通常需要输入服务器 root 密码：

```bash
ssh-copy-id -i ~/.ssh/<your_deploy_key>.pub root@115.190.185.17
```

验证免密登录：

```bash
ssh root@115.190.185.17 'hostname && whoami'
```

如果 `ssh-copy-id` 提示 key 已存在，可以直接执行验证命令。验证通过后再跑部署脚本。

一键部署：

```bash
./deploy/deploy-remote.sh
```

部署脚本默认使用：

- 服务器：`root@115.190.185.17`
- SSH：默认使用本机 `~/.ssh/config`、ssh-agent 或 OpenSSH 默认 key
- 应用目录：`/opt/benchmarkAsset`
- 数据目录：`/data/benchmarkAsset`
- 域名：`benchmark.jy-video.cn`

可通过环境变量覆盖，例如 `SYNC_DATA=0 ./deploy/deploy-remote.sh` 可以只发代码不覆盖服务器数据。如果不想依赖 SSH config，也可以临时指定：`SSH_KEY=~/.ssh/<your_deploy_key> ./deploy/deploy-remote.sh`。

页面和 API 使用 Nginx Basic Auth 做简单访问验证，默认账号密码是 `benchmark` / `benchmark`。首次部署或需要覆盖线上密码时：

```bash
BASIC_AUTH_USER=你的账号 BASIC_AUTH_PASSWORD=你的密码 BASIC_AUTH_OVERWRITE=1 ./deploy/deploy-remote.sh
```

上线后检查：

```bash
curl -u benchmark:benchmark https://benchmark.jy-video.cn/api/health
```

安全端口策略：

- 公网开放：`22/tcp`、`80/tcp`、`443/tcp`
- 不开放：`8000/tcp`，后端只监听 `127.0.0.1:8000` 给 Nginx 反代
- 服务器本机启用 UFW，仅允许 OpenSSH、80、443

## 功能

- 列表页：左侧多维筛选（时代 / 类型 / 性别 / 年龄段 / 题材）+ 顶部搜索
- 每条角色一张横向卡片：信息 | 提示词 | 图片
- 点「编辑」/「新建角色」打开抽屉：编辑字段、AI 写提示词、生成 / 上传图片、设封面
- 提示词一键复制，图片点击放大看原图
