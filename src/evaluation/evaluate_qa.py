"""
评估问答系统效果。
用法：python src/evaluation/evaluate_qa.py
"""
import json
import os
import requests
import time
from datetime import datetime

API_URL = "http://localhost:8000/chat"

# 测试集：覆盖所有意图类型
TEST_CASES = [
    # 事实问答 (FACTUAL)
    {"id": 1, "type": "FACTUAL", "question": "马国翰是谁？", "keywords": ["清代", "辑佚", "书痴", "玉函山房辑佚书"]},
    {"id": 2, "type": "FACTUAL", "question": "王应麟是谁？", "keywords": ["宋代", "辑佚", "鼻祖", "首庸"]},
    {"id": 3, "type": "FACTUAL", "question": "《玉函山房辑佚书》有多少卷？", "keywords": ["594"]},
    {"id": 4, "type": "FACTUAL", "question": "严可均的代表作是什么？", "keywords": ["全上古三代秦汉三国六朝文"]},
    {"id": 5, "type": "FACTUAL", "question": "《永乐大典》是什么类型的文献？", "keywords": ["类书", "明代"]},

    # 关系问答 (RELATION)
    {"id": 6, "type": "RELATION", "question": "马国翰和王仁俊有什么关系？", "keywords": ["续编", "补编", "传承"]},
    {"id": 7, "type": "RELATION", "question": "王应麟对清代辑佚学有什么影响？", "keywords": ["鼻祖", "首庸", "影响"]},
    {"id": 8, "type": "RELATION", "question": "《全宋文》与《永乐大典》有什么关系？", "keywords": ["底本", "来源", "辑出"]},

    # 脉络问答 (CHAIN)
    {"id": 9, "type": "CHAIN", "question": "清代辑佚学经历了哪几个阶段？", "keywords": ["阶段", "发展"]},
    {"id": 10, "type": "CHAIN", "question": "辑佚学的发展历程是怎样的？", "keywords": ["宋代", "清代", "发展"]},

    # 方法问答 (METHOD)
    {"id": 11, "type": "METHOD", "question": "辑佚的基本方法有哪些？", "keywords": ["校勘", "辨伪"]},
    {"id": 12, "type": "METHOD", "question": "校勘在辑佚中起什么作用？", "keywords": ["校理", "纠正"]},

    # 比较问答 (COMPARE)
    {"id": 13, "type": "COMPARE", "question": "马国翰和严可均在辑佚方面有什么不同？", "keywords": ["不同", "区别"]},
    {"id": 14, "type": "COMPARE", "question": "明代辑佚和清代辑佚有什么差异？", "keywords": ["差异", "区别"]},
]


def call_api(question):
    """调用问答API"""
    try:
        start = time.time()
        resp = requests.post(API_URL, json={"question": question}, timeout=60)
        elapsed = time.time() - start
        if resp.status_code == 200:
            return resp.json().get("answer", ""), elapsed
        else:
            return f"ERROR: {resp.status_code}", elapsed
    except Exception as e:
        return f"ERROR: {str(e)}", 0


def evaluate_answer(answer, keywords):
    """评估答案质量"""
    score = {
        "has_keyword": 0,
        "keyword_count": 0,
        "has_source": 0,
        "no_hallucination": 1,  # 默认无幻觉
        "length_ok": 0,
    }

    # 1. 关键词命中率
    hit = 0
    for kw in keywords:
        if kw in answer:
            hit += 1
    score["keyword_count"] = hit
    score["has_keyword"] = hit / len(keywords) if keywords else 0

    # 2. 来源标注
    if "来源" in answer or "据记载" in answer or "据考证" in answer:
        score["has_source"] = 1

    # 3. 幻觉检测（简单规则）
    hallucination_words = ["魏源", "马国瀚", "马国瑾", "王应鳞"]
    for hw in hallucination_words:
        if hw in answer:
            score["no_hallucination"] = 0
            break

    # 4. 长度检查
    if 20 < len(answer) < 1000:
        score["length_ok"] = 1

    return score


def main():
    print("=" * 60)
    print("问答系统评估")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = []
    total_time = 0

    for case in TEST_CASES:
        print(f"\n[{case['id']}/{len(TEST_CASES)}] {case['type']}: {case['question']}")
        answer, elapsed = call_api(case["question"])
        total_time += elapsed

        score = evaluate_answer(answer, case["keywords"])
        score["time"] = elapsed

        results.append({
            "id": case["id"],
            "type": case["type"],
            "question": case["question"],
            "answer": answer[:200] + "..." if len(answer) > 200 else answer,
            "score": score,
            "time": elapsed,
        })

        print(f"  回答: {answer[:100]}...")
        print(f"  关键词命中: {score['keyword_count']}/{len(case['keywords'])} ({score['has_keyword']:.0%})")
        print(f"  来源标注: {'✓' if score['has_source'] else '✗'}")
        print(f"  无幻觉: {'✓' if score['no_hallucination'] else '✗'}")
        print(f"  耗时: {elapsed:.1f}s")

    # 汇总统计
    print("\n" + "=" * 60)
    print("汇总统计")
    print("=" * 60)

    # 按类型统计
    type_stats = {}
    for r in results:
        t = r["type"]
        if t not in type_stats:
            type_stats[t] = {"count": 0, "keyword_scores": [], "source_count": 0, "no_hallucination_count": 0}
        type_stats[t]["count"] += 1
        type_stats[t]["keyword_scores"].append(r["score"]["has_keyword"])
        type_stats[t]["source_count"] += r["score"]["has_source"]
        type_stats[t]["no_hallucination_count"] += r["score"]["no_hallucination"]

    print(f"\n{'类型':<12} {'数量':<6} {'关键词命中率':<12} {'来源标注率':<12} {'无幻觉率':<12}")
    print("-" * 60)
    for t, s in type_stats.items():
        avg_keyword = sum(s["keyword_scores"]) / len(s["keyword_scores"]) if s["keyword_scores"] else 0
        source_rate = s["source_count"] / s["count"]
        hallucination_rate = s["no_hallucination_count"] / s["count"]
        print(f"{t:<12} {s['count']:<6} {avg_keyword:.0%}{'':<8} {source_rate:.0%}{'':<8} {hallucination_rate:.0%}")

    # 总体统计
    total = len(results)
    avg_keyword = sum(r["score"]["has_keyword"] for r in results) / total
    total_source = sum(r["score"]["has_source"] for r in results)
    total_hallucination = sum(r["score"]["no_hallucination"] for r in results)
    avg_time = total_time / total

    print("-" * 60)
    print(f"{'总体':<12} {total:<6} {avg_keyword:.0%}{'':<8} {total_source/total:.0%}{'':<8} {total_hallucination/total:.0%}")
    print(f"\n平均响应时间: {avg_time:.1f}s")

    # 保存详细结果
    output_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "eval_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存到: {output_path}")


if __name__ == "__main__":
    main()
