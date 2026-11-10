"""Validate the grade 1-9 textbook-model library without extra packages."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

def _project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "知识库").is_dir() and (parent / "算法").is_dir():
            return parent
    raise RuntimeError("找不到题目时间复杂度项目根目录")


ROOT = _project_root()
KNOWLEDGE = ROOT / "知识库" / "知识点"
LIBRARY = ROOT / "知识库" / "课内模型"
FAMILIARITY = {
    "introduced",
    "core",
    "reinforced",
    "uncommon_transform",
    "out_of_scope",
}
MODEL_ID = re.compile(r"^pep-g[1-9]-[a-z0-9-]+$")
FORBIDDEN_KEYS = {
    "question",
    "question_text",
    "stem",
    "answer",
    "solution",
    "choices",
    "image",
    "image_url",
}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    topics = json.loads((KNOWLEDGE / "topics.json").read_text(encoding="utf-8"))
    topic_ids = {str(row["id"]) for row in topics}
    sources_payload = json.loads((LIBRARY / "sources.json").read_text(encoding="utf-8"))
    sources = sources_payload.get("books", [])
    source_ids = {str(row.get("id")) for row in sources}
    require(len(sources) == 18, "sources.json 必须正好有九个年级的上下册", errors)
    require(len(source_ids) == len(sources), "sources.json 有重复 id", errors)
    for source in sources:
        grade = source.get("grade")
        require(isinstance(grade, int) and 1 <= grade <= 9, f"来源年级非法：{source}", errors)
        require(source.get("semester") in {"上", "下"}, f"来源册次非法：{source.get('id')}", errors)
        require(source.get("publisher") == "人民教育出版社", f"来源出版社非法：{source.get('id')}", errors)
        require(bool(source.get("official_overview_url")), f"来源缺官方页面：{source.get('id')}", errors)
        require(
            source.get("rights_status") == "summary_only_no_textbook_expression",
            f"来源版权策略非法：{source.get('id')}",
            errors,
        )
        if source.get("isbn") is None:
            require(
                source.get("verification_status") == "series_verified_bibliography_pending",
                f"未核ISBN必须明确处于待核状态：{source.get('id')}",
                errors,
            )

    all_ids: set[str] = set()
    total = 0
    grades_seen: set[int] = set()
    for grade in range(1, 10):
        path = LIBRARY / f"grade-{grade}" / "models.json"
        require(path.is_file(), f"缺少 {path.relative_to(ROOT)}", errors)
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        require(payload.get("grade") == grade, f"{path}: 顶层年级不一致", errors)
        models = payload.get("models", [])
        require(isinstance(models, list) and models, f"{path}: models 不能为空", errors)
        grades_seen.add(grade)
        total += len(models)
        for index, model in enumerate(models):
            where = f"grade-{grade}[{index}]"
            keys = set(model)
            require(not keys.intersection(FORBIDDEN_KEYS), f"{where}: 出现禁止的教材表达字段", errors)
            model_id = str(model.get("id") or "")
            require(bool(MODEL_ID.fullmatch(model_id)), f"{where}: id 非法 {model_id}", errors)
            require(model_id not in all_ids, f"{where}: id 重复 {model_id}", errors)
            all_ids.add(model_id)
            require(model.get("grade") == grade, f"{where}: 模型年级不一致", errors)
            familiarity = model.get("familiarity_by_grade", {})
            require(
                set(familiarity) == {str(g) for g in range(1, 10)},
                f"{where}: familiarity_by_grade 必须覆盖1-9",
                errors,
            )
            require(
                set(familiarity.values()).issubset(FAMILIARITY),
                f"{where}: 有非法熟悉度",
                errors,
            )
            foreign = set(model.get("topic_ids", [])) - topic_ids
            require(not foreign, f"{where}: topic_ids 不存在 {sorted(foreign)}", errors)
            require(model.get("source_id") in source_ids, f"{where}: source_id 不存在", errors)
            require(
                model.get("rights_status") == "independent_non_reconstructive_summary",
                f"{where}: 版权状态非法",
                errors,
            )
            require(
                8 <= len(str(model.get("model_summary") or "")) <= 180,
                f"{where}: 模型摘要长度非法",
                errors,
            )
            refs = model.get("item_refs", [])
            require(bool(refs), f"{where}: 缺来源定位", errors)
            for ref in refs:
                require(bool(ref.get("chapter")), f"{where}: 定位缺 chapter", errors)
                require(
                    ref.get("verification_status")
                    in {"chapter_only_page_pending", "page_verified"},
                    f"{where}: 定位核验状态非法",
                    errors,
                )
                if ref.get("page") is None:
                    require(
                        ref.get("verification_status") == "chapter_only_page_pending",
                        f"{where}: 页码为空时必须标待核",
                        errors,
                    )
            serialized = json.dumps(model, ensure_ascii=False)
            require(len(serialized) < 6000, f"{where}: 单条过长，可能混入教材表达", errors)

    manifest = json.loads((LIBRARY / "manifest.json").read_text(encoding="utf-8"))
    require(grades_seen == set(range(1, 10)), "manifest 年级没有全部落盘", errors)
    require(manifest.get("grades") == list(range(1, 10)), "manifest.grades 不一致", errors)
    require(manifest.get("model_count") == total, "manifest.model_count 不一致", errors)
    require(manifest.get("formal_scoring") is False, "影子库不得标成正式计分", errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"ok: 18 books, {len(grades_seen)} grades, {total} model summaries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
