#!/usr/bin/env python3
"""
生成编码报告：功能点状态表 + 4-bullet 小结。

用法:
  python3 generate_report.py \
    --output coding-report.md \
    --features '[{"id":"F-01","name":"apply+checkAsync","status":"✅","note":"骨架即完整"},
                 {"id":"F-02","name":"handleSubTask","status":"🔶","note":"展开逻辑待实现"}]' \
    --commits '[{"service":"demo-service","hash":"abc1234"}]' \
    --compile '{"status":"passed","rounds":1}' \
    --test '{"total":19,"passed":19,"failed":0}' \
    --blockers "无" \
    --gaps "F-02 handleSubTask code8 展开逻辑待实现, F-03 preview 上游查询待实现" \
    --handoff "后端全部完成，待前端开发"
"""

import argparse
import json
import sys
from datetime import datetime


def _write_header(f, title: str):
    f.write(f"# {title}\n\n")
    f.write(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")


def _write_feature_table(f, features: list[dict]):
    if not features:
        f.write("（无功能点记录）\n\n")
        return

    f.write("## 功能点状态表\n\n")
    f.write("| # | 功能点 | 状态 | 说明 |\n")
    f.write("|---|--------|------|------|\n")
    for feat in features:
        fid = feat.get("id", "")
        name = feat.get("name", "")
        status = feat.get("status", "❌")
        note = feat.get("note", "")
        f.write(f"| {fid} | {name} | {status} | {note} |\n")

    # 状态统计
    stats = {"✅": 0, "⏳": 0, "🔶": 0, "❌": 0, "↩": 0}
    for feat in features:
        s = feat.get("status", "❌")
        if s in stats:
            stats[s] += 1

    f.write(f"\n**统计**：✅ {stats['✅']} | ⏳ {stats['⏳']} | 🔶 {stats['🔶']} | ❌ {stats['❌']} | ↩ {stats['↩']}\n\n")

    # 已知缺口
    gaps = [f for f in features if f.get("status") in ("🔶", "⏳")]
    if gaps:
        f.write("### 已知缺口\n\n")
        for g in gaps:
            f.write(f"- **{g['id']} {g['name']}**（{g['status']}）：{g.get('note', '无说明')}\n")
        f.write("\n")

    # 延后项
    deferred = [f for f in features if f.get("status") == "↩"]
    if deferred:
        f.write("### 延后项\n\n")
        for d in deferred:
            f.write(f"- **{d['id']} {d['name']}**：{d.get('note', '无说明')}\n")
        f.write("\n")


def _write_commits(f, commits: list[dict]):
    if not commits:
        return
    f.write("## 各服务 Commit\n\n")
    f.write("| 服务 | Commit |\n")
    f.write("|------|--------|\n")
    for c in commits:
        f.write(f"| {c.get('service', '')} | {c.get('hash', '')} |\n")
    f.write("\n")


def _write_build_result(f, compile_result: dict, test_result: dict):
    f.write("## 编译与测试\n\n")
    f.write(f"- 编译：**{compile_result.get('status', 'unknown')}**（{compile_result.get('rounds', 0)} 轮）\n")
    total = test_result.get("total", 0)
    passed = test_result.get("passed", 0)
    failed = test_result.get("failed", 0)
    f.write(f"- 测试：{total} runs, {passed} passed, {failed} failed\n\n")


def _write_summary(f, output: str, blockers: str, gaps: str, handoff: str):
    f.write("## 小结\n\n")
    f.write(f"- 产出: {output}\n")
    f.write(f"- 阻塞: {blockers}\n")
    f.write(f"- 已知缺口: {gaps}\n")
    f.write(f"- 交接: {handoff}\n")


def main():
    parser = argparse.ArgumentParser(description="生成编码报告（4-bullet 小结 + 功能点状态表）")
    parser.add_argument("--output", required=True, help="输出文件路径")
    parser.add_argument("--title", default="编码实现报告", help="报告标题")
    parser.add_argument("--features", default="[]", help="功能点列表 JSON")
    parser.add_argument("--commits", default="[]", help="Commit 列表 JSON")
    parser.add_argument("--compile", default="{}", help="编译结果 JSON")
    parser.add_argument("--test", default="{}", help="测试结果 JSON")
    parser.add_argument("--output-files", default="", help="产出文件清单，逗号分隔")
    parser.add_argument("--blockers", default="无", help="阻塞项描述")
    parser.add_argument("--gaps", default="无", help="已知缺口描述")
    parser.add_argument("--handoff", default="", help="交接说明")

    args = parser.parse_args()

    features = json.loads(args.features)
    commits = json.loads(args.commits)
    compile_result = json.loads(args.compile)
    test_result = json.loads(args.test)

    with open(args.output, "w", encoding="utf-8") as f:
        _write_header(f, args.title)
        _write_feature_table(f, features)
        _write_commits(f, commits)
        _write_build_result(f, compile_result, test_result)
        _write_summary(f, args.output_files, args.blockers, args.gaps, args.handoff)

    print(f"✅ 报告已生成：{args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
