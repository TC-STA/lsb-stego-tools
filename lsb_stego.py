#!/usr/bin/env python3
"""
LSB 隐写工具 —— 在图片中隐藏/提取秘密信息
原理：修改每个像素RGB值的最低有效位，人眼无法察觉差异

用法：
  python lsb_stego.py encode <输入图> <输出图> <秘密信息>
  python lsb_stego.py decode <隐写图>
  python lsb_stego.py demo                          # 一键演示
"""

import sys, os
import numpy as np
from PIL import Image

# ======================== 核心函数 ========================

def text_to_bits(text: str) -> str:
    """将文本转为二进制字符串，末尾加 32bit 结束标记"""
    data = text.encode('utf-8')
    # 结束标记：8个0x00字节（64个0bit），用作解码终止判断
    data += b'\x00' * 8
    return ''.join(format(b, '08b') for b in data)


def bits_to_text(bits: str) -> str:
    """从二进制字符串提取文本（遇到结束标记停止）"""
    bytes_list = bytearray()
    for i in range(0, len(bits), 8):
        byte = int(bits[i:i+8], 2)
        bytes_list.append(byte)
        # 检测结束标记
        if len(bytes_list) >= 8 and bytes_list[-8:] == b'\x00' * 8:
            bytes_list = bytes_list[:-8]
            break
    return bytes_list.decode('utf-8', errors='replace')


def encode_lsb(image_path: str, secret_message: str, output_path: str):
    """
    将秘密信息嵌入图片（LSB替换）
    - 支持中文等任意UTF-8文本
    - 输出必须为 PNG 格式（无损压缩保证数据完整）
    """
    # 1. 加载图片
    img = Image.open(image_path).convert('RGB')
    pixels = np.array(img, dtype=np.uint8)
    height, width, _ = pixels.shape
    total_pixels = height * width * 3

    # 2. 文本 → 二进制
    bits = text_to_bits(secret_message)
    if len(bits) > total_pixels:
        max_chars = (total_pixels - 64) // 8
        raise ValueError(
            f"图片太小！当前最多嵌入约 {max_chars} 个字符，"
            f"而你的消息需要 {len(secret_message)} 个字符"
        )

    # 3. 展平像素数组，逐位替换LSB
    flat = pixels.ravel()
    for i, bit in enumerate(bits):
        flat[i] = (flat[i] & 0xFE) | int(bit)

    # 4. 重组为图像，保存PNG
    result = flat.reshape(height, width, 3)
    out_img = Image.fromarray(result, 'RGB')
    out_img.save(output_path, 'PNG')

    # 统计信息
    orig_size = os.path.getsize(image_path) if os.path.exists(image_path) else 0
    out_size = os.path.getsize(output_path)
    hidden_bytes = (len(bits) - 64) // 8  # 减去结束标记

    print(f'✅ 嵌入成功！')
    print(f'   原始图片: {os.path.basename(image_path)} ({orig_size//1024}KB)')
    print(f'   隐写图片: {os.path.basename(output_path)} ({out_size//1024}KB)')
    print(f'   隐藏信息: "{secret_message}"')
    print(f'   隐藏大小: {hidden_bytes} 字节 / {len(bits)} bit')
    print(f'   像素利用率: {len(bits)/total_pixels*100:.4f}%')


def decode_lsb(image_path: str) -> str:
    """
    从LSB隐写图片中提取秘密信息
    返回提取到的文本
    """
    img = Image.open(image_path).convert('RGB')
    pixels = np.array(img, dtype=np.uint8)
    flat = pixels.ravel()

    # 提取所有LSB位
    bits = ''.join(str(pixel & 1) for pixel in flat)

    # 转换为文本（自动在结束标记处停止）
    message = bits_to_text(bits)
    if message:
        print(f'✅ 提取成功！')
        print(f'   提取到的信息: "{message}"')
        return message
    else:
        print('❌ 未检测到隐藏信息')
        return ''


def compare_images(orig_path: str, stego_path: str):
    """对比原始图片和隐写图片的差异"""
    orig = np.array(Image.open(orig_path).convert('RGB'), dtype=np.int16)
    stego = np.array(Image.open(stego_path).convert('RGB'), dtype=np.int16)
    diff = np.abs(orig - stego)
    max_diff = diff.max()
    mean_diff = diff.mean()
    identical = np.all(orig == stego)

    print(f'\n📊 图片对比分析:')
    print(f'   两张图完全相同? {"✅ 是" if identical else "❌ 否"}')
    print(f'   最大像素差值: {max_diff}')
    print(f'   平均像素差值: {mean_diff:.4f}')
    print(f'   (差值 <= 1 属于正常LSB修改范围)')

    # 如果有明显差异，找出差异区域
    if max_diff > 1:
        diff_mask = np.max(diff, axis=2) > 1
        diff_count = diff_mask.sum()
        total = diff_mask.size
        print(f'   差异像素比例: {diff_count/total*100:.4f}%')


# ======================== Demo 演示 ========================

def run_demo():
    """一键生成演示：创建测试图 → 隐藏信息 → 提取验证"""
    print('=' * 55)
    print('  LSB 隐写演示')
    print('=' * 55)

    demo_dir = os.path.dirname(os.path.abspath(__file__))
    if not demo_dir:
        demo_dir = '/storage/emulated/0/星宝阁'

    # 1. 创建一张测试图片（彩色渐变图）
    test_img_path = os.path.join(demo_dir, 'test_original.png')
    stego_img_path = os.path.join(demo_dir, 'test_stego.png')

    print(f'\n[1/4] 生成测试图片...')
    w, h = 400, 300
    test_img = Image.new('RGB', (w, h))
    for x in range(w):
        for y in range(h):
            r = int(255 * x / w)
            g = int(255 * y / h)
            b = int(255 * (x + y) / (w + h))
            test_img.putpixel((x, y), (r, g, b))
    test_img.save(test_img_path, 'PNG')
    print(f'   已创建: {test_img_path} ({w}x{h})')

    # 2. 嵌入秘密信息
    secret = '这是隐藏信息！Hello LSB Steganography! 测试中文+英文混合 🇨🇳'
    print(f'\n[2/4] 嵌入秘密信息...')
    print(f'   秘密内容: "{secret}"')
    encode_lsb(test_img_path, secret, stego_img_path)

    # 3. 解码验证
    print(f'\n[3/4] 解码验证...')
    decoded = decode_lsb(stego_img_path)
    assert decoded == secret, '❌ 解码结果与原文不一致！'
    print(f'   ✅ 解码与原信息完全匹配！')

    # 4. 对比两张图
    print(f'\n[4/4] 对比分析...')
    compare_images(test_img_path, stego_img_path)

    print(f'\n{"=" * 55}')
    print(f'  演示完成！生成的文件:')
    print(f'  📄 原始图: {test_img_path}')
    print(f'  📄 隐写图: {stego_img_path}')
    print(f'  📄 脚本: {os.path.join(demo_dir, "lsb_stego.py")}')
    print(f'{"=" * 55}')


# ======================== 命令行入口 ========================

def print_usage():
    print('''LSB 隐写工具

用法:
  编码（隐藏信息）:
    python lsb_stego.py encode <输入图片> <输出图片> "<秘密信息>"

  解码（提取信息）:
    python lsb_stego.py decode <隐写图片>

  一键演示:
    python lsb_stego.py demo

示例:
  python lsb_stego.py encode photo.png stego.png "这是秘密"
  python lsb_stego.py decode stego.png
    ''')


def main():
    if len(sys.argv) < 2:
        print_usage()
        return

    mode = sys.argv[1]

    if mode == 'encode':
        if len(sys.argv) < 5:
            print('用法: encode <输入图> <输出图> "<秘密信息>"')
            return
        encode_lsb(sys.argv[2], sys.argv[4], sys.argv[3])

    elif mode == 'decode':
        if len(sys.argv) < 3:
            print('用法: decode <隐写图>')
            return
        decode_lsb(sys.argv[2])

    elif mode == 'demo':
        run_demo()

    else:
        print(f'未知模式: {mode}')
        print_usage()


if __name__ == '__main__':
    main()
