# 在 RTX 4060 笔记本上跑起 Ternary Bonsai 2 27B：1.75-bit 三值量化实战

PrismML（加州理工团队创立）开源了 Ternary Bonsai 2 27B：通过 1.76-bit 三值量化，把 Qwen3.8 27B 从 54GB 压到 5.9GB，官方称性能留存 98.2%。新闻里说"单卡断网驱动 Cline 狂飙至 143 tokens/s"——那是在 RTX 5090 上。手上这台 RTX 4060 Laptop（8GB 显存）能不能跑？实测结果：能跑，质量达标，速度是瓶颈。本文记录完整过程。

> 本文首发地址 <https://h89.cn/archives/821.html>

## 结论先行

| 项目         | 实测结果                                 |
| ---------- | ------------------------------------ |
| 能否运行       | 能，CUDA 后端正常加载                        |
| 生成速度 tg128 | 13.1 t/s（RTX 5090 为 130，M5 Max 为 47） |
| 提示处理 pp512 | 287 t/s                              |
| 输出质量       | 数学、代码、思考链均正常，无乱码                     |
| 可用性        | 聊天可用，跑 Cline 这类 agent 循环偏慢但可用        |

## 硬件与软件

- 笔记本：i7-14650HX / RTX 4060 Laptop 8GB / 32GB 内存
- 运行时：PrismML 定制版 llama.cpp（CUDA 12.4 构建，build b10772）
- 模型：`Ternary-Bonsai-2-27B-PTQ1_0.gguf`（5.53 GiB，26.9B 参数，1.75 bpw 三值量化）

## 一个关键前提：必须用 PrismML 定制运行时

这个模型不是普通 GGUF。它的权重是三值 {-1, 0, +1} + FP16 分组缩放，且在 Hadamard 旋转基下存储，运行时要对激活做对应变换。因此：

- **原版 llama.cpp、Ollama、LM Studio 都跑不了**——它们不认 `PTQ1_0`/`PQ2_0` 类型，甚至加载 F16 文件也会输出乱码
- 必须用 [PrismML-Eng/llama.cpp](https://github.com/PrismML-Eng/llama.cpp/releases) 的构建
- Windows 上注意选 **CUDA 12.4** 构建（13.3 版在部分机器上启动即崩，官方 KNOWN\_ISSUES 有记录）

## 下载地址

**模型（5.53GiB，放部署目录根下）：**

```
https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/resolve/main/Ternary-Bonsai-2-27B-PTQ1_0.gguf
```

镜像（直连慢时用）：

```
https://hf-mirror.com/prism-ml/Ternary-Bonsai-2-27B-gguf/resolve/main/Ternary-Bonsai-2-27B-PTQ1_0.gguf
```

文件校验大小：`5,946,648,928` 字节。

**运行时（Windows CUDA 12.4，约 300MB，解压后直接可用）：**

```
https://github.com/PrismML-Eng/llama.cpp/releases/download/prism-b10772-e8fd209/llama-prism-b10772-e8fd209-bin-win-cuda-12.4-x64.zip
```

**官方文档与运行示例（source of truth）：**

- 模型卡：<https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf>
- 运行脚本/集成示例：<https://github.com/PrismML-Eng/Bonsai-demo>
- 已知问题：模型卡里的 `KNOWN_ISSUES.md`（很有用，建议先读）

同仓库还有 `PQ2_0`（7.21GB，打包更松但解包更快）和 `mmproj` 视觉塔（Q8\_0，0.63GB，需要看图时再下）。

## 部署过程中的坑

1. **国内网络**：HF 直连单线程约 16MB/s 但频繁被重置，hf-mirror 只有 86KB/s。建议用支持多线程/断点续传的下载工具（IDM、迅雷等）走直连链接，别硬用 curl 单线程。
2. **输出上限要给够**：模型默认 xhigh 思考模式，先输出长思考链再给答案。`-n` 设小了（比如 256）会在思考中途截断，表现为"空回复"或"想个没完"。建议 `-n 8192` 以上。
3. **`reasoning_effort: "high"`** **会 500**：聊天模板只接受 `low`/`medium`/`xhigh`，没有 `high`。
4. **单用户服务要限制 slot**：默认多 slot 分割缓存，长对话会反复重算。加 `-np 1 --cache-ram 16384`。

## 实测数据

`llama-bench`，`-ngl 99 -fa 1`：

| 测试         | RTX 4060 Laptop（实测） | RTX 5090（官方）      | M5 Max（官方） |
| ---------- | ------------------- | ----------------- | ---------- |
| tg128 生成   | 13.1 ± 1.2 t/s      | 130 t/s           | 47 t/s     |
| pp512 提示处理 | 287 ± 16 t/s        | 1805 t/s（PTQ1\_0） | —          |

差距主要来自显存带宽：三值量化模型的生成速度几乎完全由权重搬运速度决定，桌面旗舰卡的带宽是笔记本卡的好几倍。

交互体验（llama-cli，含思考链）约 10-17 t/s，日常问答等待感可接受。

**质量抽检：**

- "2+2 等于几" → 思考后答 4
- "写斐波那契函数" → 输出带边界检查的迭代实现，代码质量正常
- 思考链清晰连贯，没有低比特量化常见的语义崩坏

官方基准（20 项测试，Qwen3.8 27B 全精度 85.4 分）：Bonsai 2 27B 得 83.9 分（留存 98.2%），数学、编码几乎无损，差距集中在知识推理和视觉。

## 跑 Cline（本地编码 Agent）

```powershell
runtime\llama-server.exe -m Ternary-Bonsai-2-27B-PTQ1_0.gguf -ngl 99 -fa on -c 16384 `
  -np 1 --cache-ram 16384 --host 127.0.0.1 --port 8080
```

Cline 的 API base 填 `http://127.0.0.1:8080`，完全断网可用。建议：

- 上下文设 8K\~16K（8GB 显存放不下 262K，官方默认 32K 上下文的脚本也会爆显存）
- 用 `reasoning_effort: "medium"` 或 thinking budget 压思考长度，加速编辑-调试循环
- 工具调用偶有畸形输出（官方已知问题），复杂任务建议搭配云端模型混合使用

## 目录结构

```
Ternary-Bonsai-2-27B-PTQ1_0.gguf   模型
runtime\                           PrismML llama.cpp（CUDA 12.4）
logs\                              部署过程日志
AGENTS.md                          技术摘要（给 agent 看）
README.md                          本文
```

## 一句话总结

5.9GB 的 27B 模型在 8GB 显存的笔记本上真实可跑，推理质量接近全精度；速度只有旗舰卡的十分之一，适合隐私敏感、断网、轻量 agent 场景，不适合追求"狂飙"的重度编码流水线。
