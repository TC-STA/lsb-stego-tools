# LSB Steganography Tools

一套**LSB（最低有效位）图片隐写工具**，支持在PNG图片中隐藏/提取秘密信息，人眼无法察觉。

## 工具列表

| 脚本 | 版本 | 功能 |
|:---|:---:|:---|
| `lsb_stego.py` | V1 基础版 | 文本隐写，中英文+Emoji全支持 |
| `lsb_stego_v2.py` | V2 进阶版 | AES-256-GCM加密 + 任意文件嵌入 + 纠错编码 |

---

## 原理

每个像素的RGB三通道各占8bit，修改最低1位（LSB），人眼无法分辨颜色变化。

```
原像素: R=255 (11111111) -> 改最低位 -> R=254 (11111110)
        G=128 (10000000) -> 改最低位 -> G=129 (10000001)
        B=64  (01000000) -> 改最低位 -> B=65  (01000001)
```

一张400x300的PNG图可隐藏约45KB的数据。**必须保存为PNG（无损压缩）**，JPEG有损压缩会破坏LSB数据。

---

## V1 基础版

### 依赖

```bash
pip install Pillow numpy
```

### 使用

```bash
# 隐藏文本
python lsb_stego.py encode input.png output.png "你的秘密消息"

# 提取文本
python lsb_stego.py decode output.png

# 一键演示
python lsb_stego.py demo
```

### 功能特性

- 纯文本隐藏，支持中文、英文、Emoji混合
- 自动检测水印结束标记
- 最小像素改动量

---

## V2 进阶版

### 额外依赖

```bash
pip install cryptography
```

### 使用

```bash
# 文本隐藏 + AES-256-GCM加密
python lsb_stego_v2.py encode input.png output.png "秘密消息" --password "你的密码"

# 隐藏任意文件（PDF/ZIP/图片等任何格式）
python lsb_stego_v2.py encode input.png output.png secret.zip --file

# 隐藏文件 + 加密 + 纠错编码
python lsb_stego_v2.py encode input.png output.png doc.pdf --file --password "pwd" --ecc

# 解码提取
python lsb_stego_v2.py decode output.png --password "你的密码"

# 解码后文件输出到指定目录
python lsb_stego_v2.py decode output.png --password "pwd" --output-dir ./extracted

# 一键演示
python lsb_stego_v2.py demo
```

### 功能特性

| 功能 | 说明 |
|:---|:---|
| AES-256-GCM加密 | PBKDF2密钥派生，认证加密防篡改 |
| 文件嵌入 | 任意格式文件，保留原文件名 |
| 纠错编码 | (3,1)重复码，抗轻度图像损坏 |
| 自动识别 | 魔数+头部元数据，一键解码 |
| 密码保护 | 错误密码无法解密，无信息泄露 |

### 数据包格式

```
[MAGIC(4B LSB2)][VER(1B)][FLAGS(1B)][ORIG_LEN(4B)][NAME_LEN(1B)][FILENAME][NONCE(12B)][TAG(16B)][DATA][EOF(8B)]
```

| 字段 | 说明 |
|:---|:---|
| MAGIC | 魔数 LSB2，用于自动识别 |
| VER | 版本号 |
| FLAGS | 标志位：bit0=加密, bit1=文件模式, bit2=纠错 |
| ORIG_LEN | 原始数据长度 |
| NAME_LEN | 原始文件名长度（文件模式） |
| FILENAME | 原始文件名 |
| NONCE | AES-GCM随机数（12字节） |
| TAG | AES-GCM认证标签（16字节） |
| DATA | 载荷数据（加密或明文） |
| EOF | 结束标记（8个0x00） |

---

## 演示效果

### V1 演示

```
嵌入成功！
隐藏信息: "这是隐藏信息！Hello LSB Steganography! 测试中文+英文混合"
隐藏大小: 80 字节 / 704 bit
像素利用率: 0.1956%

图片对比分析:
最大像素差值: 1
平均像素差值: 0.0009 <- 人眼完全无法察觉
```

### V2 演示

```
[2/5] 文本嵌入（带AES-256-GCM加密）... OK
[3/5] 文件嵌入（隐藏一个文本文件）... OK
[4/5] 错误密码解码... FAIL not found <- 无信息泄露
[5/5] 正确密码解码... TEXT: 密码666隐藏的消息! OK
[6/5] 文件解码... FILE -> secret.txt OK
```

---

## 注意事项

1. **必须使用PNG格式**保存隐写后的图片，JPEG有损压缩会破坏LSB数据
2. V2加密模式下，**忘记密码则无法恢复数据**
3. 图片尺寸决定最大容量：最大字节数 = (宽 x 高 x 3) / 8（V2带纠错时再除以3）
4. 本工具仅用于学习/研究用途，请勿用于非法目的

---

## 项目结构

```
lsb-stego-tools/
  README.md
  lsb_stego.py         V1 基础版
  lsb_stego_v2.py      V2 进阶版
  test_original.png    V1 测试原图
  test_stego.png       V1 测试隐写图
  v2_orig.png          V2 测试原图
  v2_enc.png           V2 加密文本隐写图
  v2_file.png          V2 文件隐写图
  secret.txt           从v2_file.png解码出的测试文件
```

---

## License

MIT
