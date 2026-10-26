import ast
import json
import re


def _remove_json_comments(text: str) -> str:
    """移除字符串外的 // 注释。"""
    output: list[str] = []
    in_string = False
    escaped = False
    index = 0
    while index < len(text):
        char = text[index]
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            output.append(char)
            index += 1
            continue
        if char == "/" and index + 1 < len(text) and text[index + 1] == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue
        output.append(char)
        index += 1
    return "".join(output)


def _balanced_object(text: str) -> str:
    start = text.find("{")
    if start < 0:
        raise json.JSONDecodeError("No JSON object found", text, 0)
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise json.JSONDecodeError("Incomplete JSON object", text, len(text))


def extract_json_object(response: str) -> dict:
    """从模型回复提取 JSON，并修正常见的注释、尾逗号与代码围栏。"""
    text = (response or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    candidate = _balanced_object(text)
    attempts = [
        candidate,
        re.sub(r",\s*([}\]])", r"\1", _remove_json_comments(candidate)),
    ]
    last_error: Exception | None = None
    for attempt in attempts:
        try:
            result = json.loads(attempt)
            if not isinstance(result, dict):
                raise ValueError("JSON root must be an object")
            return result
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
    try:
        result = ast.literal_eval(attempts[-1])
        if isinstance(result, dict):
            return result
    except (SyntaxError, ValueError):
        pass
    raise last_error or ValueError("Invalid JSON response")
