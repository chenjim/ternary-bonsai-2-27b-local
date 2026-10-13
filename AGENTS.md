# AGENTS.md

本目录是 Ternary Bonsai 2 27B（PrismML 三值量化模型）的本地部署。详细叙述见 README.md，本文件是给 agent 的技术摘要。

## 目录结构

```
Ternary-Bonsai-2-27B-PTQ1_0.gguf   模型，5.53GiB，26.9B 参数，1.75bpw 三值量化
runtime\                           PrismML 定制 llama.cpp，Windows CUDA 12.4，build b10772
logs\                              部署过程日志（bench.log 为测速结果）
README.md                          部署博文（过程、踩坑、实测）
```

## 运行方式

必须用 `runtime\` 下的定制构建。原版 llama.cpp / Ollama / LM Studio 无法运行此模型（不识别 PTQ1_0 类型，或加载后输出乱码）。

交互对话：

```powershell
runtime\llama-cli.exe -m Ternary-Bonsai-2-27B-PTQ1_0.gguf -ngl 99 -fa on -c 8192 `
  --temp 1.0 --top-p 0.95 --top-k 20 --min-p 0.05 -f prompt.txt -n 8192
```

OpenAI 兼容服务（供 Cline 等使用）：

```powershell
runtime\llama-server.exe -m Ternary-Bonsai-2-27B-PTQ1_0.gguf -ngl 99 -fa on -c 16384 `
  -np 1 --cache-ram 16384 --host 127.0.0.1 --port 8080
```

## 硬件基线（RTX 4060 Laptop 8GB / 32GB 内存）

- tg128 生成 13.1 t/s，pp512 提示处理 287 t/s
- 8GB 显存下上下文建议 8K~16K；262K 上下文需要大显存
- 参考：RTX 5090 为 130 t/s，M5 Max 为 47 t/s

## 已知约束（来自官方 KNOWN_ISSUES）

- 模型默认 xhigh 思考，`-n`/`max_tokens` 必须给够（8192+），否则截断或空回复
- `reasoning_effort` 只接受 `low`/`medium`/`xhigh`，传 `high` 会 HTTP 500
- `low` 并不明显缩短思考；要短用 `medium`
- 单用户服务加 `-np 1 --cache-ram`，否则长对话反复重算
- 工具调用偶有畸形输出，agent 场景需容错
- Windows 构建选 CUDA 12.4（13.3 版部分机器启动即崩）

## 下载来源

- 模型：https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/resolve/main/Ternary-Bonsai-2-27B-PTQ1_0.gguf （校验大小 5,946,648,928 字节）
- 运行时：https://github.com/PrismML-Eng/llama.cpp/releases （win-cuda-12.4-x64 包）
- 官方运行指南：https://github.com/PrismML-Eng/Bonsai-demo
