"""Audit BetterGI community script naming conventions.

The checker is intentionally conservative: it reports rules that can be verified from
filenames, directory names, and JSON metadata without understanding route behavior.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PATHING_CATEGORIES = {"锄地专区", "地方特产", "敌人与魔物", "矿物", "其他"}
REGIONS = {"蒙德", "璃月", "稻妻", "须弥", "枫丹", "纳塔", "至冬"}
PATHING_ID_RE = re.compile(r"^(?:\d{2,3}|[A-Z]\d{2,3})$")
COUNT_RE = re.compile(r"^\d+个$")
JS_FOLDER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
BATTLE_AUTHOR_RE = re.compile(r"^//作者：\S+")


@dataclass(frozen=True)
class Violation:
    """One script convention violation."""

    path: Path
    rule: str
    detail: str


def relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def iter_readme_case_violations(root: Path) -> Iterable[Violation]:
    for path in root.rglob("*"):
        if path.is_file() and path.name.lower() == "readme.md" and path.name != "README.md":
            yield Violation(path, "README 文件名", "说明文件必须命名为 README.md。")


def material_from_pathing_path(pathing_root: Path, json_path: Path) -> str | None:
    parts = json_path.relative_to(pathing_root).parts
    if len(parts) < 3:
        return None
    category, material = parts[0], parts[1]
    if category not in PATHING_CATEGORIES:
        return None
    return material


def audit_pathing_json(pathing_root: Path, json_path: Path) -> Iterable[Violation]:
    name = json_path.stem
    parts = name.split("-")
    material = material_from_pathing_path(pathing_root, json_path)

    if len(parts) < 4:
        yield Violation(
            json_path,
            "地图追踪命名",
            "文件名至少应包含 编号-材料名称-地点-数量。",
        )
        return

    identifier, filename_material, *locations, count = parts
    if not PATHING_ID_RE.fullmatch(identifier):
        yield Violation(
            json_path,
            "地图追踪编号",
            "编号应为两位/三位数字，或类似 A01 的字母加数字编号。",
        )
    if not COUNT_RE.fullmatch(count):
        yield Violation(json_path, "地图追踪数量", "最后一段应为预期采集数量，例如 6个。")
    if any(not segment for segment in locations):
        yield Violation(json_path, "地图追踪地点", "地点段不能为空。")
    if len(locations) >= 2 and locations[0] in REGIONS and not locations[1]:
        yield Violation(json_path, "地图追踪区域", "跨区域材料标注区域后仍需提供地点。")
    if material and filename_material != material:
        yield Violation(
            json_path,
            "地图追踪材料目录",
            f"文件名材料“{filename_material}”应与材料目录“{material}”一致。",
        )

    payload = read_json(json_path)
    if payload is None:
        yield Violation(json_path, "JSON 格式", "文件不是有效的 JSON 对象。")
        return
    json_name = payload.get("name")
    if json_name != name:
        yield Violation(
            json_path,
            "JSON name 字段",
            f"json 文件中的 name 字段应等于文件名“{name}”。",
        )


def audit_pathing(root: Path) -> Iterable[Violation]:
    pathing_root = root / "pathing"
    if not pathing_root.exists():
        return
    for child in pathing_root.iterdir():
        if child.is_dir() and child.name not in PATHING_CATEGORIES:
            yield Violation(child, "地图追踪一级分类", "一级分类应为锄地专区、地方特产、敌人与魔物、矿物、其他。")
    for json_path in pathing_root.rglob("*.json"):
        yield from audit_pathing_json(pathing_root, json_path)


def audit_js(root: Path) -> Iterable[Violation]:
    js_root = root / "js"
    if not js_root.exists():
        return
    for script_dir in sorted(path for path in js_root.iterdir() if path.is_dir()):
        if not JS_FOLDER_RE.fullmatch(script_dir.name):
            yield Violation(
                script_dir,
                "JS 文件夹命名",
                "脚本主体文件夹名称不应包含空格，建议使用大驼峰式等清晰命名。",
            )
        if not (script_dir / "manifest.json").is_file():
            yield Violation(script_dir, "JS manifest", "JS 脚本目录应包含 manifest.json。")


def audit_battle(root: Path) -> Iterable[Violation]:
    candidates = [root / "combat", root / "battle", root / "fight", root / "AutoFight"]
    for battle_root in candidates:
        if not battle_root.exists():
            continue
        for script_path in battle_root.rglob("*.txt"):
            text = script_path.read_text(encoding="utf-8-sig", errors="replace")
            if "//作者：" not in text:
                yield Violation(script_path, "战斗策略署名", "战斗策略脚本应使用 //作者：你的名字 署名。")
            elif not any(BATTLE_AUTHOR_RE.match(line) for line in text.splitlines()):
                yield Violation(script_path, "战斗策略署名", "署名格式必须为 //作者：你的名字。")
            if "副本" in script_path.name and not script_path.stem.endswith("-副本"):
                yield Violation(script_path, "战斗策略副本后缀", "仅用于副本的策略名称应增加 -副本 后缀。")


def audit(root: Path) -> list[Violation]:
    return [
        *iter_readme_case_violations(root),
        *audit_pathing(root),
        *audit_js(root),
        *audit_battle(root),
    ]


def format_markdown(violations: list[Violation], root: Path) -> str:
    if not violations:
        return "未发现可自动判定的脚本规范问题。"
    lines = ["| 路径 | 规则 | 问题 |", "| --- | --- | --- |"]
    for violation in violations:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{relative(violation.path, root)}`",
                    violation.rule,
                    violation.detail,
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="要扫描的脚本仓库根目录。")
    parser.add_argument(
        "--fail-on-violations",
        action="store_true",
        help="发现不规范脚本时以退出码 1 结束，便于 CI 使用。",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    violations = audit(root)
    print(format_markdown(violations, root))
    return 1 if args.fail_on_violations and violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
