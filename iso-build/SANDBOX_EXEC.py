
import subprocess
import os
import tempfile
from dotenv import load_dotenv
from openai import OpenAI

class SANDBOX_EXECPrimitive(CapabilityPrimitive):
    def __init__(self):
        super().__init__(
            id="SANDBOX_EXEC",
            type_signature=TypeSignature(type_in=["text", "path"], type_out=["text"]),
            semantic_descriptor="Execute any file - AI analyzes format, converts if needed, and runs it.",
        )

    def _ask_ai(self, path, content):
        load_dotenv()
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            return None
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": f"""你是一个代码执行专家。分析这个文件并决定如何运行它。

文件路径: {path}
文件内容:
{content[:1000]}

可用的解释器: /usr/bin/python3, /bin/sh

返回JSON格式（只返回JSON，不要其他内容）：

如果可以直接运行：
{{"mode": "direct", "interpreter": "/usr/bin/python3", "can_run": true, "reason": "说明"}}

如果需要转换代码才能运行（如自定义格式/DSL），提供转换后的Python代码：
{{"mode": "convert", "converted_code": "print('Hello')", "can_run": true, "reason": "说明"}}

如果完全无法运行：
{{"can_run": false, "reason": "原因"}}"""}],
            temperature=0,
        )
        import json
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        return json.loads(text)

    def invoke(self, input_data, session_id=None):
        path = input_data.get("path") or input_data.get("text", "")
        if not path or not os.path.exists(path):
            return {"result": f"Error: file not found - {path}", "status": "error"}
        try:
            with open(path, "r", errors="replace") as f:
                content = f.read()
        except Exception as e:
            return {"result": str(e), "status": "error"}

        ext = os.path.splitext(path)[1].lower()
        quick_map = {".py": ["/usr/bin/python3", path], ".sh": ["/bin/sh", path]}

        if ext in quick_map:
            cmd = quick_map[ext]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                return {"result": (result.stdout+result.stderr).strip(),
                        "exit_code": result.returncode,
                        "status": "ok" if result.returncode == 0 else "error"}
            except Exception as e:
                return {"result": str(e), "status": "error"}

        # AI 分析
        print(f"[SANDBOX] Analyzing {path} with AI...")
        try:
            analysis = self._ask_ai(path, content)
            if not analysis or not analysis.get("can_run"):
                reason = analysis.get("reason", "Unknown") if analysis else "AI unavailable"
                return {"result": f"Cannot execute: {reason}", "status": "error"}

            print(f"[SANDBOX] AI: {analysis.get('reason')} (mode={analysis.get('mode')})")

            if analysis.get("mode") == "convert":
                # 写入临时文件运行
                converted = analysis.get("converted_code", "")
                with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                                 delete=False) as tmp:
                    tmp.write(converted)
                    tmp_path = tmp.name
                print(f"[SANDBOX] Running converted code...")
                try:
                    result = subprocess.run(["/usr/bin/python3", tmp_path],
                                           capture_output=True, text=True, timeout=30)
                    return {"result": (result.stdout+result.stderr).strip(),
                            "exit_code": result.returncode,
                            "status": "ok" if result.returncode == 0 else "error"}
                finally:
                    os.unlink(tmp_path)
            else:
                cmd = [analysis["interpreter"], path]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                return {"result": (result.stdout+result.stderr).strip(),
                        "exit_code": result.returncode,
                        "status": "ok" if result.returncode == 0 else "error"}
        except Exception as e:
            return {"result": f"Failed: {e}", "status": "error"}
