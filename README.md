# AI 虚拟员工代理平台

本项目旨在创建一个平台, 用户可以通过前端界面启动和管理容器化的 AI 虚拟员工代理。

## 项目目标

*   通过 Web 界面展示不同类型的虚拟 AI 员工 (例如: 文案策划、数据分析员)。
*   用户点击某个员工卡片后, 后端能够 (未来将实现) 动态启动一个对应的 AI 代理容器实例。
*   用户可以 (未来将实现) 与启动的 AI 代理进行交互。
*   AI 代理容器的生命周期将被管理, 包括在长时间不活动后自动释放资源 (未来将实现)。
*   AI 代理的状态能够被保存和恢复, 以便下次对话时继续 (未来将实现)。

## 主要功能

除了基础的虚拟员工卡片展示和模拟代理启动外, 本项目现已集成一个更高级的 **深度研究助理**:

*   **深度研究助理**:
    *   基于 `openai-agents` SDK 实现, 包含多个协同工作的AI智能体 (策划、研究、编辑)。
    *   用户可以提交一个研究主题, AI助理将尝试进行网络搜索、信息收集, 并生成一份结构化的研究报告。
    *   通过API端点 `/api/agent/research_assistant/invoke` 进行调用, 需要提供研究任务描述。

## 技术栈

*   **后端:** Python, FastAPI
*   **前端:** HTML (Jinja2 模板), CSS, JavaScript
*   **AI代理:** openai-agents SDK
*   **实时通信:** Server-Sent Events (SSE)
*   **容器化:** Docker
*   **ASGI 服务器:** Uvicorn

## 当前状态

项目目前处于开发阶段, 已实现以下基础框架:
*   使用 FastAPI 搭建的基础后端服务。
*   一个简单的前端页面, 通过 Jinja2 模板渲染, 展示虚拟员工卡片。
*   初步集成了AI驱动的深度研究助理功能 (需要配置OPENAI_API_KEY, 详见“配置要求”部分)。
*   点击卡片可以调用后端的占位符 API 来“启动”标准代理, 并返回一个会话 ID。
*   一个 SSE 端点, 用于从后端向前端流式传输标准代理的 (模拟的) 状态更新。
*   一个 `Dockerfile` 用于将应用容器化。
*   基础的CI/CD流程 (代码检查和单元测试) 使用 GitHub Actions 配置。

## 配置要求

为了使用本项目的核心AI功能 (特别是深度研究助理), 您需要一个OpenAI API密钥.

请设置以下环境变量:
- `OPENAI_API_KEY`: 您的OpenAI API密钥.

**本地开发:**
建议在项目根目录下创建一个名为 `.env` 的文件, 并添加以下内容:
```
OPENAI_API_KEY="your_actual_openai_api_key_here"
```
确保已将 `.env` 文件添加到您的 `.gitignore` 文件中, 以避免意外提交密钥. 应用启动时会自动加载此文件中的环境变量.

**Docker部署:**
在运行Docker容器时, 通过 `-e` 标志或您部署平台的相应机制来提供此环境变量:
```bash
docker run -e OPENAI_API_KEY="your_actual_openai_api_key_here" -p 8000:8000 ai-agent-platform
```

## 安装与运行

### 1. 环境准备

*   Python 3.9+
*   pip (Python 包安装器)
*   Docker (如果需要构建和运行 Docker 镜像)

### 2. 安装依赖

克隆仓库后, 在项目根目录运行:

```bash
pip install -r requirements.txt
```

### 3. 运行开发服务器

在项目根目录运行 (确保 OPENAI_API_KEY 已在您的环境或 .env 文件中设置):

```bash
uvicorn app.main:app --reload
```
或者直接运行 `python app/main.py`.

应用将在 `http://127.0.0.1:8000` 上可用。

### 4. 构建和运行 Docker 镜像

确保 Docker 正在运行。在项目根目录:

**构建镜像:**
```bash
docker build -t ai-agent-platform .
```

**运行容器 (确保替换 "your_actual_openai_api_key_here"):**
```bash
docker run -e OPENAI_API_KEY="your_actual_openai_api_key_here" -p 8000:8000 ai-agent-platform
```
应用将在 `http://localhost:8000` (或 Docker 主机 IP) 上可用。

## 后续计划

*   完善深度研究助理的错误处理和状态反馈。
*   对深度研究助理的输出 (研究报告) 进行更友好的前端展示。
*   根据 `openai-agents` SDK 的能力, 进一步优化工具上下文传递机制。
*   完成集成测试, 确保AI研究助理功能的稳定性。
*   实现原计划中的其他功能, 如用户认证、更复杂的代理生命周期管理等。
