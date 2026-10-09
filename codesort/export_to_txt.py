from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = (PROJECT_ROOT / "codesort" / "code").resolve()

BACKEND_SOURCE_ROOT = (PROJECT_ROOT / "backend" / "app").resolve()
FRONTEND_SOURCE_ROOT = (PROJECT_ROOT / "frontend").resolve()

BACKEND_OUTPUT_FILE = OUTPUT_ROOT / "mango-talk.backend.txt"
FRONTEND_OUTPUT_FILE = OUTPUT_ROOT / "mango-talk.frontend.txt"

FRONTEND_EXCLUDED_DIRS = {"node_modules", ".vscode", "dist"}


def build_project_relative_path(file_path: Path) -> str:
    """
    生成项目相对路径，例如：
    mango-talk/backend/app/models/user.py
    """
    relative_to_project = file_path.relative_to(PROJECT_ROOT)
    return f"{PROJECT_ROOT.name}/{relative_to_project.as_posix()}"


def is_excluded(file_path: Path, source_root: Path, excluded_dir_names: set[str]) -> bool:
    """
    判断文件是否位于需要排除的目录中
    """
    relative_parts = file_path.relative_to(source_root).parts
    return any(part in excluded_dir_names for part in relative_parts)


def collect_files(
    source_root: Path,
    allowed_suffixes: set[str],
    excluded_dir_names: set[str] | None = None,
) -> list[Path]:
    """
    收集 source_root 下所有指定后缀文件
    可按目录名排除部分路径
    """
    if not source_root.exists():
        raise FileNotFoundError(f"源目录不存在: {source_root}")

    excluded_dir_names = excluded_dir_names or set()

    files = []
    for path in source_root.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in allowed_suffixes:
            continue

        if excluded_dir_names and is_excluded(path, source_root, excluded_dir_names):
            continue

        files.append(path.resolve())

    return sorted(files)


def write_merged_txt(source_files: list[Path], output_file: Path, title: str) -> None:
    """
    将多个源码文件合并写入一个 txt
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if not source_files:
        output_file.write_text(
            f"{title}\n\n未找到符合条件的文件。\n",
            encoding="utf-8",
        )
        print(f"[WARN] {title}: 未找到符合条件的文件")
        print(f"[OUT ] {output_file}")
        return

    parts = []
    parts.append(f"{title}\n")
    parts.append(f"TOTAL_FILES: {len(source_files)}\n\n")

    for file_path in source_files:
        project_path = build_project_relative_path(file_path)
        absolute_path = str(file_path.resolve())
        code_text = file_path.read_text(encoding="utf-8", errors="replace")

        block = (
            "=" * 100 + "\n"
            f"PATH: {project_path}\n"
            f"ABSOLUTE_PATH: {absolute_path}\n"
            + "=" * 100 + "\n\n"
            + code_text
            + "\n\n"
        )
        parts.append(block)

    output_file.write_text("".join(parts), encoding="utf-8")
    print(f"[OK  ] {title}: {len(source_files)} 个文件")
    print(f"[OUT ] {output_file}")


def export_backend() -> None:
    """
    导出后端 backend/app 下所有 .py 文件
    """
    backend_files = collect_files(
        source_root=BACKEND_SOURCE_ROOT,
        allowed_suffixes={".py"},
    )

    write_merged_txt(
        source_files=backend_files,
        output_file=BACKEND_OUTPUT_FILE,
        title="MANGO TALK BACKEND CODE MERGED",
    )


def export_frontend() -> None:
    """
    导出 frontend 下所有 .js / .vue / .html 文件
    排除 node_modules 和 .vscode
    """
    frontend_files = collect_files(
        source_root=FRONTEND_SOURCE_ROOT,
        allowed_suffixes={".js", ".vue", ".html"},
        excluded_dir_names=FRONTEND_EXCLUDED_DIRS,
    )

    write_merged_txt(
        source_files=frontend_files,
        output_file=FRONTEND_OUTPUT_FILE,
        title="MANGO TALK FRONTEND CODE MERGED",
    )


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    export_backend()
    export_frontend()

    print("\n全部完成。")


if __name__ == "__main__":
    main()
