import json
import sys


class StreamingLLMParser:
    def __init__(self, call_tool):
        self.call_tool = call_tool

        self.buffer = ""
        self.mode = None  # None | "TEXT" | "TOOL"

        self.text = []
        self.tool = ""

        self.tool_results = []

        self.end_marker = "<#END>"

    # -----------------------------
    # helper: safe END detection
    # -----------------------------
    def _has_end(self):
        return self.end_marker in self.buffer

    def _end_prefix_len(self, text):
        max_len = min(len(text), len(self.end_marker) - 1)

        for size in range(max_len, 0, -1):
            if self.end_marker.startswith(text[-size:]):
                return size

        return 0

    def _write_text(self, text):
        if not text:
            return

        self.text.append(text)
        sys.stdout.write(text)
        sys.stdout.flush()

    def _consume_header(self, header):
        idx = self.buffer.find(header)
        if idx == -1:
            return False

        self.buffer = self.buffer[idx + len(header):]

        if self.buffer.startswith(" "):
            self.buffer = self.buffer[1:]
        elif self.buffer.startswith("\n"):
            self.buffer = self.buffer[1:]

        return True

    def feed(self, chunk: str):
        out = []

        # normalize chunk (VERY IMPORTANT for Ollama stream)
        chunk = chunk.replace("\r", "")
        self.buffer += chunk

        while True:
            # -----------------------------
            # MODE DETECTION (robust)
            # -----------------------------
            if self.mode is None:

                # tolerate split "TEXT:" / "TEXT: " across chunks
                if self._consume_header("TEXT:"):
                    self.mode = "TEXT"

                elif self._consume_header("TOOL:"):
                    self.mode = "TOOL"

                else:
                    return out

            # -----------------------------
            # TEXT MODE
            # -----------------------------
            if self.mode == "TEXT":

                if not self._has_end():
                    hold_len = self._end_prefix_len(self.buffer)
                    safe_part = self.buffer[:-hold_len] if hold_len else self.buffer
                    self.buffer = self.buffer[-hold_len:] if hold_len else ""

                    self._write_text(safe_part)
                    return out

                part, self.buffer = self.buffer.split(self.end_marker, 1)
                self._write_text(part)

                content = "".join(self.text)
                if content:
                    out.append(content)

                self.text = []
                self.mode = None
                continue

            # -----------------------------
            # TOOL MODE
            # -----------------------------
            if self.mode == "TOOL":

                if not self._has_end():
                    hold_len = self._end_prefix_len(self.buffer)
                    safe_part = self.buffer[:-hold_len] if hold_len else self.buffer
                    self.buffer = self.buffer[-hold_len:] if hold_len else ""

                    self.tool += safe_part
                    return out

                raw, self.buffer = self.buffer.split(self.end_marker, 1)
                self.tool += raw

                raw = self.tool.strip()

                try:
                    data = json.loads(raw)

                    name = data["name"]
                    args = data.get("args", [])

                    result = self.call_tool(name, args)

                    entry = {
                        "name": name,
                        "args": args,
                        "result": result
                    }

                    self.tool_results.append(entry)
                    out.append(entry)

                except Exception as e:
                    err = {
                        "error": str(e),
                        "raw": raw
                    }

                    self.tool_results.append(err)
                    out.append(err)

                    sys.stdout.write(f"\n[TOOL ERROR] {e}\n")
                    sys.stdout.flush()

                self.tool = ""
                self.mode = None
                continue
