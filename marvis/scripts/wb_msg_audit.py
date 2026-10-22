# -*- coding: utf-8 -*-
"""wb_msg_audit.py — 投递前的话术真实性审计。

投递是对外可见、不可撤回的，话术里一旦出现「没做过却写成做过」的技术，
HR 技术面一问就穿，还会被当成群发模板。发之前逐份扫一遍：

  1. 打印每份话术的主推版全文（人工读）
  2. 扫描违禁技术词（本人没做过的：Vue/React/模型训练微调/RAG/向量检索/
     微服务云原生/Rust/Unity/C#/Spark/Flink/LangChain/大模型多模态/CUDA）

禁词表必须与**简历实测**对齐：把做过的技术列进去，等于自动生成
「我没做过 X」这种句子，和简历直接打架——HR 一对照就是破绽。

用法: python wb_msg_audit.py <final.json>
"""
import io
import json
import os
import re
import sys

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
RECRUIT = r"YOUR_HOME\招聘"

# 没做过 / 不能声称的技术
#
# ⚠ 这张表必须与**简历实测**对齐，不能凭印象写：
#   我**确实做过**的（曾被误列为禁词，实测简历 p1/p2 有据）：
#     · OpenCV + SSD Caffe 人脸检测、视觉引导抓取（某机械臂型号 机器人）
#     · Hadoop HDFS + Hive 分区表轨迹数据分析（数千条轨迹点 / 8 项指标）
#     · scikit-learn 分类 / 回归建模
#     · PyQt6、PyInstaller、Pillow、MoviePy、Flask、Jinja2
#   禁词表里写了这些，一旦照着它生成「我没做过 OpenCV」之类的话，
#   就会跟简历直接打架——HR 一对照就是破绽，比漏投还糟。
#   真正没做过的只有下面这些。
FORBID = {
    "Vue": [r"\bvue\b", r"\bvue3\b", r"vue\.js"],
    "React": [r"\breact\b", r"react\.js"],
    "模型训练/微调": [r"微调", r"模型训练", r"训练模型", r"lora", r"rlhf", r"预训练"],
    "RAG/向量检索": [r"\brag\b", r"向量检索", r"向量数据库", r"faiss", r"milvus",
                 r"embedding", r"向量库"],
    "微服务/云原生": [r"微服务", r"spring\s*cloud", r"k8s", r"kubernetes", r"服务治理"],
    "Rust": [r"\brust\b"],
    "Unity/C#": [r"unity", r"\bc#\b"],
    "Spark/Flink/实时数仓": [r"\bspark\b", r"\bflink\b", r"clickhouse", r"\bolap\b",
                     r"\bdoris\b", r"实时数仓"],
    "LangChain/工作流平台": [r"langchain", r"langgraph", r"coze", r"dify", r"n8n"],
    # 大模型多模态（视觉那块做的是 OpenCV/SSD，与此不同，别混为一谈）
    "大模型多模态": [r"多模态"],
    "CUDA/推理加速": [r"\bcuda\b", r"cudnn", r"tensorrt"],
}

# 话术文件里除主推版正文以外的部分（元信息/已核验）不算投递内容
META_MARK = "【按 JD 命中的证据点】"

# 否定语境：句子里出现这些，说明是在如实声明「我没做过」，不是违规声称。
# 判定口径是「**默认违规，有明确否定才放行**」——审计是最后一道闸，
# 宁可多报一条让人看一眼，也不能漏掉一句编造的「我做过」。
# （原来靠「我做过 / 我实际写过」这类固定短语表判肯定，实测漏掉
#   「我自己做过 RAG」「我都实际写过 React」「我用 LoRA 做过模型的微调」）
NEG_CTX = [
    "没做过", "没碰过", "没在项目里", "没真正", "没深入", "没有相关实践",
    "不敢含糊", "不把没做过的说成做过", "可以现学", "得讲在前面",
    "实打实用过", "未使用过", "尚未使用", "不糊弄", "如实说", "不敢含糊其辞",
    "只说我真正做过", "我真做过的", "没实打手", "不会把没做过",
]
# 句子里出现这些单字也算否定（如「不做多模态」「非模型训练方向」）
NEG_CHARS = ("没", "不", "未", "无", "非")


def _sentences(text):
    """按中英文句末标点切句。"""
    parts = re.split(r"(?<=[。！？!?；;])|\n+", text)
    return [p for p in parts if p.strip()]


def _is_negation(sent):
    """这句是否在如实声明「我没做过」。"""
    if any(n in sent for n in NEG_CTX):
        return True
    return any(ch in sent for ch in NEG_CHARS)


def _check_sentence(sent):
    """判断一句话里有没有「违禁技术 + 声称做过」。

    口径：禁词出现即报，除非该句明确在否认做过。
    """
    if _is_negation(sent):
        return []
    hits = []
    for name, pats in FORBID.items():
        for pat in pats:
            for m in re.finditer(pat, sent, re.I):
                s = max(0, m.start() - 26)
                hits.append(f"  ⚠ [{name}] 「{m.group(0)}」 … {sent[s:m.end()+26]}")
    return hits


def main():
    final_file = sys.argv[1] if len(sys.argv) > 1 else "favai2_final.json"
    final = json.load(io.open(os.path.join(WORK, final_file), encoding="utf-8"))
    bad = 0
    for t in final:
        folder = t["folder"]
        p = os.path.join(RECRUIT, folder, "新建 文本文档.txt")
        print("=" * 96)
        print(folder, "|", t.get("company"), "|", t.get("position"), "|", t.get("salary"))
        if not os.path.isfile(p):
            print("  !! 话术文件缺失")
            bad += 1
            continue
        txt = io.open(p, encoding="utf-8").read()
        i = txt.find("】")
        body = txt[i + 1:].lstrip("\r\n") if i >= 0 else txt
        # 只审真正发出去的正文（截止到「按 JD 命中的证据点」元信息区之前）
        j = body.find(META_MARK)
        sent = body[:j] if j > 0 else body
        print(sent[:1800])
        hits = []
        for s in _sentences(sent):
            hits.extend(_check_sentence(s))
        if hits:
            bad += 1
            for h in hits:
                print(h)
        else:
            print("  ✓ 正文无违禁技术词")
        print()
    print(f"共 {len(final)} 份，{len(final) - bad} 份通过，{bad} 份需人工处理")


if __name__ == "__main__":
    main()
