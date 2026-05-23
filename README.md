# 角色与场景资产库

维护 AI 出图素材的工具，分**角色资产库**与**场景资产库**两个模块（顶部切换）：
增删改查、多维筛选、AI 写提示词、调用图片接口生成图片、批量重新生成。

## 形态

- 前端网页：React + Vite + TypeScript + Ant Design
- 后端：FastAPI，数据存 Neon Postgres，图片存火山引擎 TOS
- 业务字段存到 Postgres JSONB，方便后续字段小改动；图片只在 TOS 保存，数据库记录 object key

## 启动

```bash
./start.sh
```

首次运行会自动建后端虚拟环境、装前后端依赖。启动后打开 **http://localhost:5180**。

后端启动前需要复制 `backend/.env.example` 为 `backend/.env`，并填好：

```
DATABASE_URL=postgresql://...
TOS_BUCKET=
TOS_REGION=
TOS_ENDPOINT=
TOS_ACCESS_KEY_ID=
TOS_SECRET_ACCESS_KEY=
```

手动分开启动：

```bash
# 后端
cd backend && .venv/bin/python main.py        # http://localhost:8000

# 前端
cd frontend && npm run dev                    # http://localhost:5180
```

## 数据导入

- 角色：`角色资料库数据.csv`（76 个角色）可导入到 Neon。重导：`python import_csv.py --force`
- 场景：55 个高频场景可导入到 Neon。重灌：`python seed_scenes.py --force`

```bash
cd backend
.venv/bin/python import_csv.py --force      # 重导角色
.venv/bin/python seed_scenes.py --force     # 重灌场景
```

## Schema migration

Postgres schema 由 `backend/migrations/*.sql` 管理，执行记录写入 `schema_migrations`。
首次建表也是 migration：

```bash
cd backend
.venv/bin/python migrate_schema.py
```

以后如果需要改表结构，新增一个递增编号 SQL 文件，例如：

```
backend/migrations/0002_add_asset_owner.sql
```

部署脚本会在重启服务前自动执行未应用的 schema migration；应用启动时也会调用同一套 migration，避免漏跑。

从旧 SQLite + 本地图片迁移到 Neon + TOS：

```bash
cd backend
.venv/bin/python migrate_sqlite_to_neon_tos.py \
  --sqlite data/app.db \
  --images data/images \
  --force
```

## AI 功能配置

写提示词、生成图片走 OpenRouter 兼容端点，配置在 `backend/.env`（已隔离，不读取其他项目）。
固定项已预填，通常只需填 API Key：

```
OPENROUTER_API_KEY=
TEXT_MODEL=anthropic/claude-opus-4.7
```

其余一般无需改动：

```
OPENROUTER_BASE_URL=https://proxy.offerin.cn/openrouter/api/v1
IMAGE_MODEL=openai/gpt-5.4-image-2
```

- 文字（写提示词）：OpenAI SDK 调 OpenRouter 兼容端点
- 图片（生成图片）：OpenAI SDK 调 OpenRouter 兼容端点，后端把返回图片上传到 TOS

未配置时 AI 功能不可用，其余功能（增删改查 / 筛选 / 搜索 / 图集 / 上传）正常。
改完 `.env` 需重启后端生效。

## 部署到 benchmark.jy-video.cn

当前应用前端使用同源相对路径访问 `/api` 与 `/images`，部署时不用在前端写死 IP。生产域名为 `https://benchmark.jy-video.cn`。推荐形态是：

- Nginx 监听 `80/443`，`80` 用于证书续期与跳转 HTTPS，`443` 静态托管 `frontend/dist`
- Nginx 将 `/api/` 与 `/images/` 反代到本机后端 `127.0.0.1:8000`
- FastAPI 后端用 systemd 常驻运行，数据写 Neon，图片写 TOS

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
- 域名：`benchmark.jy-video.cn`

部署脚本要求本机环境里已设置 `DATABASE_URL` 和 TOS 变量，并会写入远端 `backend/.env`。如果不想依赖 SSH config，也可以临时指定：`SSH_KEY=~/.ssh/<your_deploy_key> ./deploy/deploy-remote.sh`。

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
