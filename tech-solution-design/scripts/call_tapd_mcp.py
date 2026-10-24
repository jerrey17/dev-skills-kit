#!/usr/bin/env python3
"""
通过 **stdio** 模式调用 TAPD MCP server（uvx mcp-server-tapd），
获取 TAPD 需求/缺陷等内容，适用于 tech-solution-design skill。

依赖：pip install -r requirements-mcp.txt

配置 JSON（tapd_mcp.config.json）：
  - command: 启动命令（默认 uvx）
  - args: 命令参数（默认 ["mcp-server-tapd"]）
  - env: 环境变量（TAPD_ACCESS_TOKEN / TAPD_API_BASE_URL / TAPD_BASE_URL）

环境变量：TAPD_MCP_CONFIG 指向配置文件；或使用 --config。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = SCRIPT_DIR / "tapd_mcp.config.json"


def _load_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        print(
            f"未找到 TAPD MCP 配置文件: {path}\n"
            f"请复制 tapd_mcp.config.json 并填入 TAPD_ACCESS_TOKEN。",
            file=sys.stderr,
        )
        sys.exit(2)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not data.get("command"):
        print("配置缺少必填字段: command", file=sys.stderr)
        sys.exit(2)
    env = data.get("env", {})
    if not env.get("TAPD_ACCESS_TOKEN"):
        print(
            "警告: TAPD_ACCESS_TOKEN 为空，请在配置文件中填入实际值。",
            file=sys.stderr,
        )
    return data


def _print_tool_result(result: Any) -> None:
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


def _import_stdio():
    try:
        from mcp.client.stdio import stdio_client

        return stdio_client
    except ImportError:
        _auto_install_deps()
        for mod_name in list(sys.modules):
            if mod_name == "mcp" or mod_name.startswith("mcp."):
                del sys.modules[mod_name]
        try:
            from mcp.client.stdio import stdio_client  # type: ignore

            return stdio_client
        except ImportError as e:
            try:
                import mcp  # type: ignore

                mcp_version = getattr(mcp, "__version__", "unknown")
            except Exception:
                mcp_version = "not-installed"
            print(
                "自动升级后仍不支持 stdio 客户端。"
                f"\nPython: {sys.executable}"
                f"\n检测到 mcp 版本: {mcp_version}"
                f"\n导入错误: {e}"
                "\n请手动升级:"
                f"\n{sys.executable} -m pip install -U -r {SCRIPT_DIR / 'requirements-mcp.txt'}",
                file=sys.stderr,
            )
            sys.exit(127)


def _import_server_params():
    try:
        from mcp import StdioServerParameters

        return StdioServerParameters
    except ImportError:
        from mcp.client.stdio import StdioServerParameters  # type: ignore

        return StdioServerParameters


def _unpack_rw(streams: Any) -> tuple[Any, Any]:
    if isinstance(streams, tuple) and len(streams) >= 2:
        return streams[0], streams[1]
    raise TypeError(f"unexpected MCP streams value: {type(streams)!r}")


async def _with_stdio_session(
    config: dict[str, Any],
    fn: Callable[[Any], Awaitable[None]],
) -> None:
    stdio_client = _import_stdio()
    ClientSession = _import_client_session()
    StdioServerParameters = _import_server_params()

    merged_env = {**os.environ, **{k: v for k, v in config.get("env", {}).items() if v}}

    server_params = StdioServerParameters(
        command=config["command"],
        args=config.get("args", []),
        env=merged_env,
    )

    async with stdio_client(server_params) as streams:
        read_stream, write_stream = _unpack_rw(streams)
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            await fn(session)


async def _run_tool(config: dict[str, Any], tool_name: str, arguments: dict[str, Any]) -> None:
    async def work(session: Any) -> None:
        result = await session.call_tool(tool_name, arguments=arguments)
        _print_tool_result(result)

    await _with_stdio_session(config, work)


async def _list_tools(config: dict[str, Any]) -> None:
    async def work(session: Any) -> None:
        listed = await session.list_tools()
        for t in listed.tools:
            name = getattr(t, "name", "?")
            desc = getattr(t, "description", "") or ""
            print(f"{name}\t{desc[:120]}")

    await _with_stdio_session(config, work)


def _parse_tapd_url(url: str) -> dict[str, str]:
    """解析 TAPD 链接，提取 workspace_id 和资源信息。

    支持的链接格式：
    - https://www.tapd.cn/{workspace_id}/prong/stories/view/{story_id}
    - https://www.tapd.cn/{workspace_id}/bugtrace/bugs/view?bug_id={bug_id}
    - https://www.tapd.cn/{workspace_id}/prong/tasks/view/{task_id}
    """
    patterns = [
        (
            r"tapd\.cn/(?:tapd_fe/)?(\d+)/(?:prong/stories/view|story/detail)/(\d+)",
            lambda m: {"workspace_id": m.group(1), "story_id": m.group(2), "type": "story"},
        ),
        (
            r"tapd\.cn/(?:tapd_fe/)?(\d+)/(?:bugtrace/bugs/view|bug/detail)/?\?.*bug_id=(\d+)",
            lambda m: {"workspace_id": m.group(1), "bug_id": m.group(2), "type": "bug"},
        ),
        (
            r"tapd\.cn/(?:tapd_fe/)?(\d+)/(?:bugtrace/bugs/view|bug/detail)/(\d+)",
            lambda m: {"workspace_id": m.group(1), "bug_id": m.group(2), "type": "bug"},
        ),
        (
            r"tapd\.cn/(?:tapd_fe/)?(\d+)/(?:prong/tasks/view|task/detail)/(\d+)",
            lambda m: {"workspace_id": m.group(1), "task_id": m.group(2), "type": "task"},
        ),
    ]
    for pattern, extractor in patterns:
        m = re.search(pattern, url)
        if m:
            return extractor(m)
    print(
        f"无法解析 TAPD 链接: {url}\n"
        "支持的格式：\n"
        "  - https://www.tapd.cn/{workspace}/prong/stories/view/{id}\n"
        "  - https://www.tapd.cn/tapd_fe/{workspace}/story/detail/{id}\n"
        "  - https://www.tapd.cn/{workspace}/bugtrace/bugs/view?bug_id={id}\n"
        "  - https://www.tapd.cn/tapd_fe/{workspace}/bug/detail/{id}\n"
        "  - https://www.tapd.cn/{workspace}/prong/tasks/view/{id}\n"
        "  - https://www.tapd.cn/tapd_fe/{workspace}/task/detail/{id}",
        file=sys.stderr,
    )
    sys.exit(1)


async def _fetch_by_url(config: dict[str, Any], url: str) -> None:
    parsed = _parse_tapd_url(url)

    async def work(session: Any) -> None:
        listed = await session.list_tools()
        tool_names = [getattr(t, "name", "") for t in listed.tools]

        resource_type = parsed["type"]
        target_id = parsed.get("story_id") or parsed.get("bug_id") or parsed.get("task_id")

        if resource_type == "story":
            candidates = ["get_stories_or_tasks", "get_story", "get_story_detail", "tapd_get_story"]
            tool_name = next((c for c in candidates if c in tool_names), None)
            if not tool_name:
                print(
                    f"未找到需求获取工具。可用工具: {', '.join(tool_names)}",
                    file=sys.stderr,
                )
                sys.exit(1)
            arguments = {
                "workspace_id": parsed["workspace_id"],
                "options": {"id": parsed["story_id"], "fields": "id,name,description,status,owner,priority,developer,created,modified,begin,due,iteration_id,workspace_id"},
            }
        elif resource_type == "bug":
            candidates = ["get_bug", "get_bug_detail", "tapd_get_bug"]
            tool_name = next((c for c in candidates if c in tool_names), None)
            if not tool_name:
                print(
                    f"未找到缺陷获取工具。可用工具: {', '.join(tool_names)}",
                    file=sys.stderr,
                )
                sys.exit(1)
            arguments = {
                "workspace_id": parsed["workspace_id"],
                "options": {"id": parsed["bug_id"], "fields": "id,title,description,status,severity,priority,current_owner,reporter,created,modified,workspace_id"},
            }
        elif resource_type == "task":
            candidates = ["get_stories_or_tasks", "get_task", "get_task_detail", "tapd_get_task"]
            tool_name = next((c for c in candidates if c in tool_names), None)
            if not tool_name:
                print(
                    f"未找到任务获取工具。可用工具: {', '.join(tool_names)}",
                    file=sys.stderr,
                )
                sys.exit(1)
            arguments = {
                "workspace_id": parsed["workspace_id"],
                "options": {"id": parsed["task_id"], "entity_type": "task", "fields": "id,name,description,status,owner,priority,developer,created,modified,workspace_id"},
            }
        else:
            print(f"不支持的资源类型: {resource_type}", file=sys.stderr)
            sys.exit(1)

        print(f"调用工具: {tool_name}，参数: {json.dumps(arguments, ensure_ascii=False)}", file=sys.stderr)
        result = await session.call_tool(tool_name, arguments=arguments)

        is_err = getattr(result, "isError", None)
        if is_err is None:
            is_err = getattr(result, "is_error", False)
        if is_err:
            _print_tool_result(result)
            return

        content = getattr(result, "content", None) or []
        raw_text = ""
        for block in content:
            text = getattr(block, "text", None)
            if text is not None:
                raw_text += text

        if raw_text and target_id:
            try:
                data = json.loads(raw_text)
                items = data.get("data", [])
                if isinstance(items, list) and len(items) > 1:
                    entity_key = {"story": "Story", "bug": "Bug", "task": "Task"}.get(resource_type, "Story")
                    matched = [
                        item for item in items
                        if item.get(entity_key, {}).get("id") == target_id
                    ]
                    if matched:
                        data["data"] = matched
                        print(json.dumps(data, ensure_ascii=False, indent=2))
                        return
            except (json.JSONDecodeError, AttributeError):
                pass

        _print_tool_result(result)

    await _with_stdio_session(config, work)


def _extract_image_urls(text: str) -> list[str]:
    """从 TAPD 需求描述 HTML 中提取图片 URL/路径。"""
    urls: list[str] = []
    # 完整 URL
    for pat in [
        r'https?://(?:www\.)?tapd\.cn/tfl/pictures/[^\s"\'<>)]+',
        r'https?://(?:www\.)?tapd\.cn/tfl/captures/[^\s"\'<>)]+',
    ]:
        urls.extend(re.findall(pat, text))
    # 相对路径（<img src="/tfl/captures/..."> 或 <img src="/tfl/pictures/...">）
    for pat in [
        r'(?:src|href)=["\'](/tfl/(?:pictures|captures)/[^"\'<>]+)["\']',
    ]:
        urls.extend(re.findall(pat, text))
    return list(dict.fromkeys(urls))


async def _download_file(url: str, output_path: Path, timeout: float = 30.0) -> bool:
    """用 httpx 下载文件，返回是否成功。"""
    try:
        import httpx
    except ImportError:
        _auto_install_deps()
        import httpx  # type: ignore
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(resp.content)
            return True
    except Exception as e:
        print(f"下载失败 {url}: {e}", file=sys.stderr)
        return False


def _safe_filename(name: str, index: int) -> str:
    """生成安全的文件名，冲突时追加序号。"""
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    if not name:
        name = f"file_{index}"
    return name


async def _fetch_attachments(
    config: dict[str, Any], workspace_id: str, entry_id: str, output_dir: str
) -> None:
    """下载 TAPD 实体关联的附件。"""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    async def work(session: Any) -> None:
        listed = await session.list_tools()
        tool_names = [getattr(t, "name", "") for t in listed.tools]

        list_candidates = [
            "get_entity_attachments", "get_attachments",
            "tapd_get_attachments", "get_attachment_list",
        ]
        list_tool = next((c for c in list_candidates if c in tool_names), None)
        if not list_tool:
            print(
                f"未找到附件列表工具。可用工具: {', '.join(tool_names)}",
                file=sys.stderr,
            )
            print("[]")
            return

        print(f"调用工具: {list_tool}", file=sys.stderr)
        result = await session.call_tool(list_tool, arguments={
            "workspace_id": int(workspace_id),
            "options": {"entry_id": entry_id},
        })

        raw_text = ""
        for block in getattr(result, "content", []) or []:
            text = getattr(block, "text", None)
            if text is not None:
                raw_text += text

        if not raw_text:
            print("附件列表为空。", file=sys.stderr)
            print("[]")
            return

        try:
            data = json.loads(raw_text)
            attachments = data.get("data", data) if isinstance(data, dict) else data
            if not isinstance(attachments, list):
                attachments = [attachments]
        except json.JSONDecodeError:
            print(f"附件列表解析失败: {raw_text[:200]}", file=sys.stderr)
            print("[]")
            return

        results_list: list[dict[str, str]] = []
        for i, att in enumerate(attachments):
            att_data = att.get("Attachment", att) if isinstance(att, dict) else att
            att_id = str(att_data.get("id", ""))
            filename = att_data.get("filename", f"attachment_{i}")
            filename = _safe_filename(filename, i)

            dl_url = att_data.get("download_url", "")

            if dl_url:
                local_path = out / filename
                ok = await _download_file(dl_url, local_path)
                if ok:
                    ext = Path(filename).suffix.lower()
                    ftype = "image" if ext in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".bmp", ".webp") else (
                        "doc" if ext in (".md", ".txt", ".csv", ".docx", ".xlsx", ".pdf", ".doc", ".xls") else "other"
                    )
                    results_list.append({
                        "id": att_id, "filename": filename,
                        "local_path": str(local_path), "type": ftype,
                    })
                    print(f"已下载: {filename}", file=sys.stderr)
                else:
                    results_list.append({
                        "id": att_id, "filename": filename,
                        "local_path": "", "type": "error",
                    })
            else:
                print(f"跳过附件 {filename}（无下载链接）", file=sys.stderr)
                results_list.append({
                    "id": att_id, "filename": filename,
                    "local_path": "", "type": "skipped",
                })

        print(json.dumps(results_list, ensure_ascii=False, indent=2))

    await _with_stdio_session(config, work)


async def _fetch_images(
    config: dict[str, Any], workspace_id: str, image_urls: list[str], output_dir: str
) -> None:
    """下载 TAPD 需求描述中的内联图片。"""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if not image_urls:
        print("[]")
        return

    async def work(session: Any) -> None:
        listed = await session.list_tools()
        tool_names = [getattr(t, "name", "") for t in listed.tools]

        img_candidates = [
            "get_image", "get_image_download_url", "download_image",
            "tapd_get_image", "get_image_url",
        ]
        img_tool = next((c for c in img_candidates if c in tool_names), None)

        results_list: list[dict[str, str]] = []
        for i, url in enumerate(image_urls):
            filename = f"image_{i+1}" + (Path(url.split("?")[0]).suffix or ".png")
            filename = _safe_filename(filename, i)
            local_path = out / filename

            dl_url = ""
            if img_tool:
                image_path = url
                m = re.search(r"(/tfl/(?:pictures|captures)/[^\s\"'<>)]+)", url)
                if m:
                    image_path = m.group(1)
                try:
                    result = await session.call_tool(img_tool, arguments={
                        "workspace_id": int(workspace_id),
                        "options": {"image_path": image_path},
                    })
                    raw = ""
                    for block in getattr(result, "content", []) or []:
                        t = getattr(block, "text", None)
                        if t:
                            raw += t
                    dl_data = json.loads(raw)
                    att_info = dl_data.get("data", {})
                    if isinstance(att_info, dict) and "Attachment" in att_info:
                        att_info = att_info["Attachment"]
                    dl_url = att_info.get("download_url", "")
                except Exception as e:
                    print(f"获取图片下载链接失败 {url}: {e}", file=sys.stderr)

            if not dl_url:
                if url.startswith("/"):
                    dl_url = f"https://www.tapd.cn{url}"
                elif url.startswith("http"):
                    dl_url = url

            ok = await _download_file(dl_url, local_path)
            if ok:
                results_list.append({
                    "original_url": url, "local_path": str(local_path), "filename": filename,
                })
                print(f"已下载: {filename}", file=sys.stderr)
            else:
                results_list.append({
                    "original_url": url, "local_path": "", "filename": filename,
                })

        print(json.dumps(results_list, ensure_ascii=False, indent=2))

    await _with_stdio_session(config, work)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="通过 stdio 模式调用 TAPD MCP server（需求/缺陷/任务拉取）",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="JSON 配置文件路径（默认: TAPD_MCP_CONFIG 或 tapd_mcp.config.json）",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_fetch = sub.add_parser("fetch", help="通过 TAPD 链接获取需求/缺陷/任务内容")
    p_fetch.add_argument("--url", "-u", required=True, help="TAPD 链接")

    sub.add_parser("tools", help="列出 MCP 提供的工具名（调试用）")

    p_call = sub.add_parser("call", help="通用调用任意 TAPD MCP 工具")
    p_call.add_argument("tool_name", help="工具名称")
    p_call.add_argument("--args", "-a", default="{}", help="JSON 格式的参数")

    p_attachments = sub.add_parser("attachments", help="下载 TAPD 实体关联的附件")
    p_attachments.add_argument("--workspace", "-w", required=True, help="TAPD workspace_id")
    p_attachments.add_argument("--entry-id", "-e", required=True, help="需求/缺陷/任务 ID")
    p_attachments.add_argument("--output-dir", "-o", required=True, help="附件保存目录")

    p_images = sub.add_parser("images", help="下载 TAPD 需求描述中的内联图片")
    p_images.add_argument("--workspace", "-w", required=True, help="TAPD workspace_id")
    p_images.add_argument("--image-urls", "-i", required=True, help="逗号分隔的图片 URL 列表")
    p_images.add_argument("--output-dir", "-o", required=True, help="图片保存目录")

    args = parser.parse_args()

    cfg_path = args.config
    if cfg_path is None:
        cfg_path = Path(os.environ.get("TAPD_MCP_CONFIG", "") or DEFAULT_CONFIG)
    config = _load_config(cfg_path)

    if args.cmd == "tools":
        asyncio.run(_list_tools(config))
        return

    if args.cmd == "fetch":
        asyncio.run(_fetch_by_url(config, args.url))
        return

    if args.cmd == "call":
        try:
            arguments = json.loads(args.args)
        except json.JSONDecodeError as e:
            print(f"参数 JSON 解析失败: {e}", file=sys.stderr)
            sys.exit(1)
        asyncio.run(_run_tool(config, args.tool_name, arguments))
        return

    if args.cmd == "attachments":
        asyncio.run(_fetch_attachments(config, args.workspace, args.entry_id, args.output_dir))
        return

    if args.cmd == "images":
        urls = [u.strip() for u in args.image_urls.split(",") if u.strip()]
        asyncio.run(_fetch_images(config, args.workspace, urls, args.output_dir))
        return


if __name__ == "__main__":
    main()
