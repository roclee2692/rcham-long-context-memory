#!/usr/bin/env python3
"""Render the architecture overview to SVG; optionally export PNG with Pillow.

Usage: python3 scripts/render_architecture.py [--font /path/to/CJK-font.ttc]
The diagram is a target design, not a record of implemented model modules.
"""
import argparse
import html
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
W, H = 1560, 1160
BG, INK, MUTED = '#f5f7fb', '#18243a', '#56647a'
BLUE, GREEN, ORANGE = '#3567bc', '#238579', '#a56a21'
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<title>局部注意力与可回溯层级记忆 v0.1</title>',
       '<desc>目标架构：局部输入向上形成层级表示，当前需求沿同一层级回读必要细节，长期档案和状态重放提供底层信息。</desc>',
       f'<rect width="{W}" height="{H}" fill="{BG}"/>']
canvas = None
draw = None
font_path = None


def text(x, y, value, size=22, fill=INK, bold=False):
    weight = 700 if bold else 400
    svg.append(f'<text x="{x}" y="{y+size}" font-size="{size}" font-weight="{weight}" fill="{fill}" font-family="PingFang SC,Heiti SC,Noto Sans CJK SC,sans-serif">{html.escape(value)}</text>')
    if draw is not None:
        font = ImageFont.truetype(font_path, size)
        draw.text((x, y), value, font=font, fill=fill)


def box(x, y, w, h, title, lines=(), accent=BLUE):
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="15" fill="white" stroke="{accent}" stroke-width="2"/>')
    if draw is not None:
        draw.rounded_rectangle((x,y,x+w,y+h),radius=15,fill='white',outline=accent,width=2)
    text(x+22,y+17,title,24,accent,True)
    for i,line in enumerate(lines):
        text(x+22,y+57+i*30,line,20,MUTED)


def arrow(points, color=BLUE, dashed=False):
    pts=' '.join(f'{x},{y}' for x,y in points)
    dash=' stroke-dasharray="7 6"' if dashed else ''
    svg.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="3"{dash}/>')
    if draw is not None:
        draw.line(points,fill=color,width=3)
    x,y=points[-1]; px,py=points[-2]; a=math.atan2(y-py,x-px)
    tri=[(x,y),(x-13*math.cos(a-.45),y-13*math.sin(a-.45)),(x-13*math.cos(a+.45),y-13*math.sin(a+.45))]
    svg.append(f'<polygon points="{" ".join(f"{u},{v}" for u,v in tri)}" fill="{color}"/>')
    if draw is not None:
        draw.polygon(tri,fill=color)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font',type=Path)
    args=parser.parse_args()
    if args.font:
        from PIL import Image, ImageDraw, ImageFont
        font_path=str(args.font)
        canvas=Image.new('RGB',(W,H),BG); draw=ImageDraw.Draw(canvas)

    text(60,36,'局部注意力与可回溯层级记忆',38,INK,True)
    text(60,93,'v0.1  /  2026-09-14  /  目标架构 · 尚未完成神经模型实现',22,MUTED)

    text(60,158,'① 写入：局部理解，逐层扩大语义范围',25,BLUE,True)
    box(60,208,290,112,'当前输入',['仅使用已出现的 token'])
    box(435,208,290,112,'局部窗口 Attention',['保留当前精确细节'])
    box(810,208,290,112,'多尺度层级聚合',['低层细节 → 高层概况'])
    box(1185,208,315,112,'高层表示 / 全局状态',['作为当前理解的概况'])
    for left,right in [(350,435),(725,810),(1100,1185)]: arrow([(left,264),(right,264)])

    text(60,374,'② 保存：同一层级连接整体与细节',25,BLUE,True)
    box(60,420,665,165,'每个层级节点',['内容表示：理解这一片在说什么','导航表示：这里还能找到什么','子节点入口 / 原始位置 / 来源与版本'])
    box(810,420,315,165,'长期原始档案',['原始内容 / 可选 KV','按需读取，计入总空间','热冷调度与保留精度'],ORANGE)
    box(1185,420,315,165,'状态快照 + 增量',['保留变化顺序与生效时间','恢复指定历史状态','不从有损摘要凭空还原'],ORANGE)
    arrow([(955,320),(955,365),(750,365),(750,402),(393,402),(393,420)])
    arrow([(725,502),(810,502)],ORANGE)
    text(810,598,'少量实体 / 时间 / 逻辑连接',20,MUTED)

    text(60,644,'③ 回忆：根据当前需要，沿同一层级展开',25,GREEN,True)
    box(60,690,290,112,'当前问题 / 隐藏状态',['形成当前导航需求'],GREEN)
    box(435,690,290,112,'高层线索与记忆锚点',['定位可能相关的分支'],GREEN)
    box(810,690,290,112,'有预算地逐层展开',['限制每层总候选与读取量'],GREEN)
    box(1185,690,315,112,'读回必要细节',['子节点 / 原文 / 历史状态'],GREEN)
    for left,right in [(350,435),(725,810),(1100,1185)]: arrow([(left,746),(right,746)],GREEN)
    arrow([(580,585),(580,690)],GREEN)
    arrow([(1125,550),(1150,550),(1150,666),(1340,666),(1340,690)],ORANGE)
    arrow([(1415,585),(1415,690)],ORANGE)

    box(435,890,665,122,'工作记忆：融合局部、概况与回读',['细节可以修正当前理解；持久更新保留来源与版本'],GREEN)
    box(1185,890,315,122,'继续理解与生成',['根据需求再次读取历史'],GREEN)
    arrow([(1342,802),(1342,847),(768,847),(768,890)],GREEN)
    arrow([(1100,951),(1185,951)],GREEN)
    arrow([(580,320),(580,343),(31,343),(31,951),(435,951)],BLUE)
    arrow([(1342,320),(1530,320),(1530,1060),(768,1060),(768,1012)],BLUE)
    text(60,1090,'证据状态：已运行的是“合成向量均值摘要 + 层级导航”探针；语义压缩、训练与整模收益待验证。',21,MUTED)
    svg.append('</svg>')
    out=ROOT/'outputs'; out.mkdir(exist_ok=True)
    (out/'architecture-v0.1.svg').write_text('\n'.join(svg)+'\n')
    if canvas is not None:
        canvas.save(out/'architecture-v0.1.png')
    print('Rendered architecture-v0.1.svg' + (' and architecture-v0.1.png' if canvas is not None else ''))
