#!/usr/bin/env python3
"""
通用知识库访问脚本（tech-solution-design skill 使用）。

支持两种 access_mode：

1. **local**（默认，主路径）：直接读取本地 kb_root 目录下的 Markdown 文件
   - search：基于 ripgrep / grep 的关键词检索（返回文件路径 + 命中片段）
   - read：打印指定文件内容（主路径由 skill 直接用 Read 工具，本子命令仅 CLI 调试用）
   - list：列出 kb_root 下符合 include_globs 的文件
   - index：打印 kb_index_file 内容

2. **remote_mcp**（可选降级）：通过 MCP Streamable HTTP 调用远程知识库
   - 保留原 call_pay_rag_mcp.py 的 MCP 客户端实现
   - search/read/list 映射到 rag_doc_search / rag_doc_read / rag_doc_list

配置文件（默认 scripts/kb.config.json，可用 --config 或环境变量 KB_CONFIG 覆盖）：
  {
    "access_mode": "local",
    "kb_root": "/path/to/kb",
    "kb_index_file": "_INDEX.md",
    "include_globs": ["**/*.md"],
    "exclude_globs": [],
    "mcp_remote": { ... }   # 仅 access_mode=remote_mcp 时使用
  }

依赖：
  - local 模式：Python 3.8+ 标准库（无第三方依赖）；若安装了 ripgrep 则优先使用
  - remote_mcp 模式：pip install -r requirements-mcp.txt
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = SCRIPT_DIR / "kb.config.json"
EXAMPLE_CONFIG = SCRIPT_DIR / "kb.config.example.json"


def _load_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        print(
            f"未找到 KB 配置文件: {path}\n"
            f"请复制 {EXAMPLE_CONFIG} 为 kb.config.json（或设置 KB_CONFIG），"
            f"并填入 kb_root / kb_index_file / access_mode。",
            file=sys.stderr,
        )
        sys.exit(2)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    mode = data.get("access_mode", "local")
    if mode == "local" and not data.get("kb_root"):
        print("配置缺少必填字段: kb_root（本地知识库根目录）", file=sys.stderr)
        sys.exit(2)
    if mode == "remote_mcp":
        mcp = data.get("mcp_remote") or {}
        if not mcp.get("url"):
            print("access_mode=remote_mcp 但 mcp_remote.url 未配置", file=sys.stderr)
            sys.exit(2)
    return data


# ============================================================
# local 模式实现
# ============================================================


def _iter_kb_files(kb_root: Path, include_globs: list[str], exclude_globs: list[str]) -> Iterable[Path]:
    for p in sorted(kb_root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(kb_root).as_posix()
        if include_globs and not any(fnmatch.fnmatch(rel, pat) for pat in include_globs):
            continue
        if exclude_globs and any(fnmatch.fnmatch(rel, pat) for pat in exclude_globs):
            continue
        yield p


def _has_ripgrep() -> bool:
    try:
        r = subprocess.run(["rg", "--version"], capture_output=True, text=True)
        return r.returncode == 0
    except FileNotFoundError:
        return False


def _local_search(kb_root: Path, keyword: str, include_globs: list[str], exclude_globs: list[str]) -> None:
    """关键词检索：返回文件路径 + 命中行。优先 ripgrep，回退到 Python 正则。"""
    files = list(_iter_kb_files(kb_root, include_globs, exclude_globs))
    if not files:
        print(f"kb_root 下无符合 include_globs 的文件: {kb_root}", file=sys.stderr)
        sys.exit(1)

    if _has_ripgrep():
        try:
            cmd = ["rg", "-n", "--no-heading", "-i", keyword] + [str(p) for p in files]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode not in (0, 1):
                print(f"ripgrep 执行失败: {r.stderr}", file=sys.stderr)
                sys.exit(1)
            print(r.stdout)
            return
        except FileNotFoundError:
            pass

    # 回退：Python 正则
    pat = re.compile(re.escape(keyword), re.IGNORECASE)
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if pat.search(line):
                rel = p.relative_to(kb_root).as_posix()
                print(f"{rel}:{i}:{line.rstrip()}")


def _local_list(kb_root: Path, path: str, recursive: bool, include_globs: list[str], exclude_globs: list[str]) -> None:
    base = kb_root / path if path else kb_root
    if not base.exists():
        print(f"路径不存在: {base}", file=sys.stderr)
        sys.exit(1)
    if recursive:
        for p in _iter_kb_files(kb_root, include_globs, exclude_globs):
            rel = p.relative_to(kb_root).as_posix()
            if not path or rel == path or rel.startswith(path.rstrip("/") + "/"):
                print(rel)
    else:
        for p in sorted(base.iterdir()):
            if p.name.startswith("."):
                continue
            rel = p.relative_to(kb_root).as_posix()
            print(rel)


def _local_read(kb_root: Path, file_path: str) -> None:
    """打印文件内容。skill 主要通过 Read 工具直接读取，此子命令仅 CLI 调试用。"""
    target = kb_root / file_path
    if not target.is_file():
        # 尝试直接绝对路径
        alt = Path(file_path)
        if alt.is_file():
            target = alt
        else:
            print(f"文件不存在: {file_path}（相对路径基于 kb_root={kb_root}）", file=sys.stderr)
            sys.exit(1)
    print(target.read_text(encoding="utf-8", errors="replace"))


def _local_index(kb_root: Path, kb_index_file: str) -> None:
    index_path = kb_root / kb_index_file
    if not index_path.is_file():
        print(f"索引文件不存在: {index_path}", file=sys.stderr)
        sys.exit(1)
    print(index_path.read_text(encoding="utf-8", errors="replace"))


# ============================================================
# remote_mcp 模式实现（原 call_pay_rag_mcp.py 逻辑）
# ============================================================


def _auto_install_deps() -> None:
    import subprocess

    req_file = SCRIPT_DIR / "requirements-mcp.txt"
    print(f"正在自动安装/升级依赖: {req_file}", file=sys.stderr)
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-U", "-r", str(req_file)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"依赖安装失败:\n{result.stderr}", file=sys.stderr)
        sys.exit(127)
    print("依赖安装/升级完成。", file=sys.stderr)


def _import_client_session():
    try:
        from mcp import ClientSession

        return ClientSession
    except ImportError:
        _auto_install_deps()
        try:
            from mcp import ClientSession  # type: ignore

            return ClientSession
        except ImportError:
            print(
                "自动安装后仍无法导入 mcp.ClientSession。"
                f"\n请手动执行: {sys.executable} -m pip install -U -r "
                f"{SCRIPT_DIR / 'requirements-mcp.txt'}",
                file=sys.stderr,
            )
            sys.exit(127)


def _import_streamable():
    try:
        from mcp.client.streamable_http import streamable_http_client

        return streamable_http_client
    except ImportError:
        _auto_install_deps()
        for mod_name in list(sys.modules):
            if mod_name == "mcp" or mod_name.startswith("mcp."):
                del sys.modules[mod_name]
        try:
            from mcp.client.streamable_http import streamable_http_client  # type: ignore

            return streamable_http_client
        except ImportError as e:
            try:
                import mcp  # type: ignore

                mcp_version = getattr(mcp, "__version__", "unknown")
            except Exception:
                mcp_version = "not-installed"
            print(
                "自动升级后仍不支持 Streamable HTTP 客户端。"
                f"\nPython: {sys.executable}"
                f"\n检测到 mcp 版本: {mcp_version}"
                f"\n导入错误: {e}"
                "\n请手动升级:"
                f"\n{sys.executable} -m pip install -U -r {SCRIPT_DIR / 'requirements-mcp.txt'}",
                file=sys.stderr,
            )
            sys.exit(127)


def _unpack_rw(streams: Any) -> tuple[Any, Any]:
    if isinstance(streams, tuple) and len(streams) >= 2:
        return streams[0], streams[1]
    raise TypeError(f"unexpected MCP streams value: {type(streams)!r}")


async def _with_streamable_session(config: dict[str, Any], fn) -> None:
    streamable_http_client = _import_streamable()
    ClientSession = _import_client_session()
    import httpx

    url = str(config["url"])
    headers = dict(config.get("headers") or {})
    timeout_sec = float(config.get("timeout", 120))
    timeout = httpx.Timeout(timeout_sec, read=timeout_sec * 10)

    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as http_client:
        async with streamable_http_client(url, http_client=http_client) as streams:
            read_stream, write_stream = _unpack_rw(streams)
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                await fn(session)


def _print_mcp_result(result: Any) -> None:
    is_err = getattr(result, "isError", None)
    if is_err is None:
        is_err = getattr(result, "is_error", False)
    if is_err:
        print("工具返回错误。", file=sys.stderr)
    content = getattr(result, "content", None) or []
    for block in content:
        text = getattr(block, "text", None)
        if text is not None:
            print(text)
            continue
        if getattr(block, "type", None) == "text" and hasattr(block, "text"):
            print(block.text)
            continue
        print(block, file=sys.stderr)
    if is_err:
        sys.exit(1)


async def _mcp_run_tool(config: dict[str, Any], tool_name: str, arguments: dict[str, Any]) -> None:
    async def work(session: Any) -> None:
        result = await session.call_tool(tool_name, arguments=arguments)
        _print_mcp_result(result)

    await _with_streamable_session(config, work)


async def _mcp_list_tools(config: dict[str, Any]) -> None:
    async def work(session: Any) -> None:
        listed = await session.list_tools()
        for t in listed.tools:
            name = getattr(t, "name", "?")
            desc = getattr(t, "description", "") or ""
            print(f"{name}\t{desc[:120]}")

    await _with_streamable_session(config, work)


def _run_remote(args, config: dict[str, Any]) -> None:
    import asyncio

    mcp_cfg = config["mcp_remote"]

    if args.cmd == "tools":
        asyncio.run(_mcp_list_tools(mcp_cfg))
        return

    if args.cmd == "search":
        arguments: dict[str, Any] = {"keyword": args.keyword}
        if args.path_must_contain:
            arguments["pathMustContain"] = args.path_must_contain
        asyncio.run(_mcp_run_tool(mcp_cfg, "rag_doc_search", arguments))
        return

    if args.cmd == "read":
        asyncio.run(_mcp_run_tool(mcp_cfg, "rag_doc_read", {"filePath": args.file_path}))
        return

    if args.cmd == "list":
        arguments = {}
        if args.path:
            arguments["path"] = args.path
        if args.recursive:
            arguments["recursive"] = True
        asyncio.run(_mcp_run_tool(mcp_cfg, "rag_doc_list", arguments))
        return

    if args.cmd == "index":
        # remote_mcp 模式下没有统一索引文件，提示用户改用 list
        print("access_mode=remote_mcp 时 index 子命令不可用，请改用 list --path /", file=sys.stderr)
        sys.exit(1)


# ============================================================
# 入口
# ============================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="通用知识库访问脚本（tech-solution-design skill），支持 local / remote_mcp 双模式",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="JSON 配置文件路径（默认: KB_CONFIG 或 scripts/kb.config.json）",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search", help="关键词检索（local: ripgrep/grep；remote_mcp: rag_doc_search）")
    p_search.add_argument("--keyword", "-k", required=True, help="检索关键词或自然语言")
    p_search.add_argument("--path-must-contain", default="", help="[remote_mcp] 路径须包含的子串")

    p_read = sub.add_parser("read", help="读取指定文件内容")
    p_read.add_argument(
        "--file-path",
        "-f",
        required=True,
        help="文件路径（local: 相对 kb_root 或绝对路径；remote_mcp: 知识库内路径）",
    )

    p_list = sub.add_parser("list", help="列出文件")
    p_list.add_argument("--path", default="", help="子路径，默认 kb_root")
    p_list.add_argument("--recursive", action="store_true", help="递归子目录")

    p_index = sub.add_parser("index", help="[local] 打印 kb_index_file 内容")

    sub.add_parser("tools", help="[remote_mcp] 列出 MCP 提供的工具名（调试用）")

    args = parser.parse_args()

    cfg_path = args.config
    if cfg_path is None:
        cfg_path = Path(os.environ.get("KB_CONFIG", "") or DEFAULT_CONFIG)
    config = _load_config(cfg_path)

    mode = config.get("access_mode", "local")

    if mode == "remote_mcp":
        _run_remote(args, config)
        return

    # local 模式
    kb_root = Path(config["kb_root"]).expanduser().resolve()
    if not kb_root.is_dir():
        print(f"kb_root 不是目录: {kb_root}", file=sys.stderr)
        sys.exit(2)
    include_globs = config.get("include_globs") or ["**/*.md"]
    exclude_globs = config.get("exclude_globs") or []
    kb_index_file = config.get("kb_index_file", "_INDEX.md")

    if args.cmd == "search":
        _local_search(kb_root, args.keyword, include_globs, exclude_globs)
        return

    if args.cmd == "read":
        _local_read(kb_root, args.file_path)
        return

    if args.cmd == "list":
        _local_list(kb_root, args.path, args.recursive, include_globs, exclude_globs)
        return

    if args.cmd == "index":
        _local_index(kb_root, kb_index_file)
        return

    if args.cmd == "tools":
        print("access_mode=local 时 tools 子命令不可用", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
