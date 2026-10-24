#!/usr/bin/env python3
"""
TAPD Wiki 推送脚本（tapd-wiki-publish skill 配套）

用途：把本地 Markdown 文件推送到 TAPD Wiki，支持首次创建与后续更新。
适用场景：大内容（≥30KB）推送，绕过 mcp__tapd__update_wiki 的输出 token 上限。

Token 来源（按优先级）：
  1. --token 命令行参数
  2. ~/.claude/.tapd-wiki-config.json 的 tapd_access_token 字段
  3. 环境变量 TAPD_ACCESS_TOKEN

用法：
  # 更新已有 wiki
  python3 push_wiki.py \
      --source /path/to/03-技术方案.md \
      --workspace-id 100001 \
      --wiki-id 11100001001029900 \
      --creator 示例作者 \
      --version v2.4.3 \
      --name "需求名 - 技术方案" \
      --state-file /path/to/.claude/workflow/需求名/tapd-wiki.json \
      --current-md /path/to/.claude/workflow/需求名/current.md

  # 首次创建 wiki
  python3 push_wiki.py \
      --source /path/to/03-技术方案.md \
      --workspace-id 100001 \
      --parent-wiki-id 11100001001026027 \
      --creator 示例作者 \
      --version v1 \
      --name "需求名 - 技术方案" \
      --state-file /path/to/.claude/workflow/需求名/tapd-wiki.json \
      --current-md /path/to/.claude/workflow/需求名/current.md

退出码：0 成功；1 推送失败；2 参数/配置错误。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude" / ".tapd-wiki-config.json"


def load_config() -> dict:
    if not CONFIG_PATH.is_file():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[warn] 配置文件 {CONFIG_PATH} 解析失败: {e}", file=sys.stderr)
        return {}


def resolve_token(explicit: str | None) -> str:
    """Token 优先级：显式参数 > 配置文件 > 环境变量。"""
    if explicit:
        return explicit
    cfg = load_config()
    cfg_token = cfg.get("tapd_access_token", "")
    if cfg_token and cfg_token != "xx":
        return cfg_token
    env_token = os.environ.get("TAPD_ACCESS_TOKEN", "")
    if env_token and env_token != "xx":
        return env_token
    return ""


def resolve_base_url() -> str:
    cfg = load_config()
    return cfg.get("tapd_api_base_url", "https://api.tapd.cn")


def build_payload(
    *,
    workspace_id: str,
    wiki_id: str | None,
    parent_wiki_id: str | None,
    name: str,
    creator: str,
    markdown: str,
) -> dict:
    payload = {
        "workspace_id": workspace_id,
        "name": name,
        "markdown_description": markdown,
    }
    if wiki_id:
        payload["id"] = wiki_id
        payload["modifier"] = creator
    else:
        if not parent_wiki_id:
            raise ValueError("首次创建 wiki 必须提供 --parent-wiki-id")
        payload["parent_wiki_id"] = parent_wiki_id
        payload["creator"] = creator
    return payload


def post_wiki(base_url: str, token: str, payload: dict) -> dict:
    url = f"{base_url}/tapd_wikis?s=mcp"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Via": "mcp",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[error] HTTP {e.code}: {body[:2000]}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[error] 请求失败: {e}", file=sys.stderr)
        sys.exit(1)


def update_state_file(
    state_file: Path,
    *,
    workspace_id: str,
    parent_wiki_id: str | None,
    wiki_id: str,
    wiki_url: str,
    version: str,
    source_md_path: str,
    source_md_mtime: int,
    pushed_scope: str,
) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if state_file.is_file():
        try:
            existing = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    existing.update(
        {
            "workspace_id": workspace_id,
            "parent_wiki_id": parent_wiki_id or existing.get("parent_wiki_id"),
            "wiki_id": wiki_id,
            "wiki_url": wiki_url,
            "version_label": version,
            "last_pushed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source_md_path": source_md_path,
            "source_md_mtime": source_md_mtime,
            "pushed_content_scope": pushed_scope,
        }
    )
    # 清理 v2.3 时代的旧阻塞字段
    for k in (
        "full_push_blocked_reason",
        "full_push_attempted",
        "full_content_local_authoritative",
    ):
        existing.pop(k, None)
    state_file.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def update_current_md(current_md: Path, wiki_url: str, version: str, pushed_at: str) -> None:
    if not current_md.is_file():
        return
    lines = current_md.read_text(encoding="utf-8").splitlines()
    new_line = f"- TAPD Wiki: {wiki_url} （{version} 已推送，{pushed_at}）"
    out = []
    replaced = False
    for ln in lines:
        if ln.startswith("- TAPD Wiki:"):
            out.append(new_line)
            replaced = True
        else:
            out.append(ln)
    if not replaced:
        # 找 PR 链接行后插入
        for i, ln in enumerate(out):
            if ln.startswith("- PR 链接"):
                out.insert(i + 1, new_line)
                replaced = True
                break
    if not replaced:
        out.append(new_line)
    current_md.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="TAPD Wiki 推送脚本")
    ap.add_argument("--source", required=True, help="本地 Markdown 文件路径")
    ap.add_argument("--workspace-id", required=True)
    ap.add_argument("--wiki-id", help="已有 wiki id（缺省则视为首次创建）")
    ap.add_argument("--parent-wiki-id", help="父 wiki id（首次创建必填）")
    ap.add_argument("--creator", required=True)
    ap.add_argument("--version", required=True, help="版本标签，如 v2.4.3")
    ap.add_argument("--name", required=True, help="Wiki 名称")
    ap.add_argument("--state-file", help="tapd-wiki.json 状态文件路径")
    ap.add_argument("--current-md", help="current.md 路径，用于更新 TAPD Wiki 行")
    ap.add_argument("--token", help="TAPD access token（缺省则按 fallback 链查找）")
    ap.add_argument(
        "--no-version-header",
        action="store_true",
        help="不在 Markdown 顶部插版本行（默认会插）",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="只做参数/token/文件检查与 payload 组装，不发起 HTTP，不写状态文件",
    )
    args = ap.parse_args()

    source = Path(args.source).expanduser().resolve()
    if not source.is_file():
        print(f"[error] 源文件不存在: {source}", file=sys.stderr)
        return 2

    token = resolve_token(args.token)
    if not token:
        print(
            "[error] 未找到 TAPD_ACCESS_TOKEN。请在 ~/.claude/.tapd-wiki-config.json 填 tapd_access_token 字段，或 export TAPD_ACCESS_TOKEN，或确保 Claude Code MCP 已启动（ps 抓进程 fallback）。",
            file=sys.stderr,
        )
        return 2

    content = source.read_text(encoding="utf-8")
    if not args.no_version_header:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        header = f"> 版本: {args.version} | 推送时间: {now} | 作者: {args.creator}\n\n"
        markdown = header + content
    else:
        markdown = content

    payload = build_payload(
        workspace_id=args.workspace_id,
        wiki_id=args.wiki_id or None,
        parent_wiki_id=args.parent_wiki_id,
        name=args.name,
        creator=args.creator,
        markdown=markdown,
    )

    base_url = resolve_base_url()
    print(f"[info] 推送 {source.name} (内容 {len(markdown)} 字符) → TAPD Wiki", file=sys.stderr)
    if args.wiki_id:
        print(f"[info] 模式: 更新 wiki_id={args.wiki_id}", file=sys.stderr)
    else:
        print(f"[info] 模式: 首次创建, parent_wiki_id={args.parent_wiki_id}", file=sys.stderr)

    if args.dry_run:
        print("[dry-run] 跳过 HTTP POST，仅校验参数/token/文件/payload。", file=sys.stderr)
        print(f"[dry-run] payload keys: {list(payload.keys())}", file=sys.stderr)
        print(f"[dry-run] markdown 长度: {len(markdown)} 字符", file=sys.stderr)
        return 0

    result = post_wiki(base_url, token, payload)
    if result.get("status") != 1:
        print(f"[error] TAPD 返回失败: {result}", file=sys.stderr)
        return 1

    wiki = result["data"]["Wiki"]
    wiki_id = wiki["id"]
    workspace_id = args.workspace_id
    wiki_url = f"https://www.tapd.cn/{workspace_id}/markdown_wikis/show/#{wiki_id}"
    pushed_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"[ok] 推送成功")
    print(f"  wiki_id: {wiki_id}")
    print(f"  url: {wiki_url}")
    print(f"  name: {wiki.get('name')}")
    print(f"  modified: {wiki.get('modified', '')}")

    if args.state_file:
        update_state_file(
            Path(args.state_file),
            workspace_id=workspace_id,
            parent_wiki_id=args.parent_wiki_id or None,
            wiki_id=wiki_id,
            wiki_url=wiki_url,
            version=args.version,
            source_md_path=str(source),
            source_md_mtime=int(source.stat().st_mtime),
            pushed_scope=f"全文 {args.version}",
        )
        print(f"[ok] 状态文件已更新: {args.state_file}")

    if args.current_md:
        update_current_md(Path(args.current_md), wiki_url, args.version, pushed_at)
        print(f"[ok] current.md TAPD Wiki 行已更新: {args.current_md}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
