# 文档一致性分析（需求 ↔ 设计）

面向"需求规格说明 ↔ 设计说明"的文档一致性分析工具。当前处于 **骨架阶段**：目录、数据模型、函数签名已就位，函数体统一为 `...`，业务逻辑尚未实现。

## 技术栈

- 后端：FastAPI + SQLModel + PostgreSQL/pgvector + Alembic
- 模型：外部 OpenAI 兼容服务；chat 默认 DeepSeek，embedding 走独立 `/embeddings`
- 解析：python-docx；分词 jieba；BM25 用 rank_bm25
- 前端：React 19 + TanStack Router/Query + shadcn/ui + Tailwind

## 目录

```
backend/app/
├── main.py                  应用入口
├── models.py                10 张数据表
├── domain.py                枚举与数据结构
├── crud.py                  数据库读写封装
├── api/
│   ├── deps.py              SessionDep
│   ├── main.py              api_router
│   └── routes/              analyses / findings / mappings / utils
├── core/
│   ├── config.py            Settings
│   ├── db.py                engine / get_session
│   └── dependencies.py      外部依赖检查
└── services/
    ├── docx_reader.py       docx 结构块读取
    ├── parsing.py           标题、文档画像、候选切块
    ├── llm.py               对话模型 + 向量模型客户端
    ├── retrieval.py         BM25F + pgvector + RRF
    ├── requirements.py      需求判定、原子化、语义合并
    ├── design.py            设计要素判定、抽取、去重
    ├── mapping.py           裁决、校验、反向判定、聚合
    ├── checks.py            确定性规则
    ├── prompts.py           提示词构建
    ├── pipeline.py          流水线编排
    ├── scoring.py           覆盖率与结论
    ├── exporters.py         Markdown / CSV 导出
    └── samples.py           内置样例

frontend/src/
├── routes/_layout/index.tsx                 工作台
├── routes/_layout/analysis.$analysisId.tsx  结果页
├── components/Analysis/*                    上传、确认、进度、概览、问题、映射、审计、导出
└── hooks/useAnalysis.ts
```

## 外部依赖

- 外部 PostgreSQL，需已启用 `pgvector` 扩展
- embedding 服务（OpenAI 兼容 `/embeddings`）
- chat 服务（默认 DeepSeek）

配置写在 `.env`；真实密钥请放 `.env.local`（已加入 `.gitignore`）。项目不包含 Docker / 部署配置，直接在本机运行即可。

## 运行

后端：

```bash
cd backend
uv sync
uv run fastapi dev
```

前端：

```bash
npm install
npm run dev
```

> 需要 Node 20+ / npm 11+。

## 生成前端 API 客户端

后端路由变化后，按下述方式重新生成 `frontend/src/client`：

```bash
cd backend
uv run python -c "import json, app.main; open('../frontend/openapi.json','w',encoding='utf-8').write(json.dumps(app.main.app.openapi(), ensure_ascii=False))"
cd ../frontend
npx openapi-ts
```

## 测试

测试使用独立数据库（`TEST_DATABASE_URL`），首次运行会自动安装 pgvector、执行迁移，每个用例结束后清空业务表。

```bash
cd backend
uv run pytest -q
```

`conftest.py` 会拒绝 `TEST_DATABASE_URL` 与 `DATABASE_URL` 相同的配置，避免测试清空业务库。

## 当前状态

- 骨架可导入（`import app.main`）、可构建（`npm run build`）、`ruff` 通过
- 尚未实现：初始迁移、文档解析、提示词、检索、判定、API 逻辑、前端界面
- `pytest` 已就位但暂无测试用例，按实现顺序表逐步补齐

## 下一步

实现顺序与当前进度见 [docs/implementation-order.md](docs/implementation-order.md)。

当前进行到 **B7（上下文与上限）**，之后是 B8（阶段自测）。
