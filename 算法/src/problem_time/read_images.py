"""Read math drawn in a question's pictures.

The transcription is only for scoring. The output document keeps the
original picture bytes.
"""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from docx.oxml.ns import qn

_STOP = re.compile(r"^[【\[]?(答案|解析|详解|解题方法)")
_PROMPT = "只转写图片里的数学内容。按图片顺序每张一行，保留数字、分数、运算符和竖式。不要解释，不要解题。"
_ENDPOINT = "https://api.deepseek.com/chat/completions"
_MODEL = "deepseek-flash"


class ImageReadError(RuntimeError):
    """The vision call did not return a transcription."""


def stem_images(document, block: list) -> list[tuple[bytes, str]]:
    """Pictures that sit in the stem, before the answer."""
    images: list[tuple[bytes, str]] = []
    for element in block:
        if _STOP.match(_plain(element)):
            break
        for blip in element.findall(".//" + qn("a:blip")):
            relation = blip.get(qn("r:embed"))
            if not relation:
                continue
            part = document.part.related_parts[relation]
            mime = _mime(part.blob, part.content_type)
            if mime is None:
                raise ImageReadError("有一张图不是 PNG、JPEG、GIF 或 WebP，读图接口读不了")
            images.append((part.blob, mime))
    return images


def deepseek_reader(api_key: str) -> Callable[[list[tuple[bytes, str]], str], str]:
    """Return a reader that sends stem pictures to DeepSeek."""

    def read(images: list[tuple[bytes, str]], context: str) -> str:
        content: list[dict[str, object]] = [{"type": "text", "text": f"{_PROMPT}\n题干文字：{context or '（无）'}"}]
        for blob, mime in images:
            encoded = base64.b64encode(blob).decode("ascii")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{encoded}", "detail": "high"},
            })
        payload = json.dumps({
            "model": _MODEL,
            "messages": [{"role": "user", "content": content}],
        }).encode("utf-8")
        request = Request(
            _ENDPOINT,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=90) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:180]
            raise ImageReadError(f"读图没有成功：{detail}") from exc
        except URLError as exc:
            raise ImageReadError("读图接口连不上") from exc
        message = body.get("choices", [{}])[0].get("message", {}).get("content", "")
        if isinstance(message, list):
            message = "\n".join(str(part.get("text", "")) for part in message if isinstance(part, dict))
        text = str(message).strip()
        if not text:
            raise ImageReadError("读图没有返回内容")
        return text

    return read


def _plain(element) -> str:
    return "".join(node.text or "" for node in element.findall(".//" + qn("w:t"))).replace("\u200b", "").strip()


def _mime(blob: bytes, content_type: str) -> str | None:
    if content_type in {"image/png", "image/jpeg", "image/gif", "image/webp"}:
        return content_type
    if blob.startswith(b"\x89PNG"):
        return "image/png"
    if blob.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if blob.startswith(b"GIF8"):
        return "image/gif"
    if blob.startswith(b"RIFF") and blob[8:12] == b"WEBP":
        return "image/webp"
    return None
