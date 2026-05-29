import json

END_MARK = "<#END>"

def parse_llm_response(text: str, call_tool):
    lines = text.splitlines()

    i = 0
    n = len(lines)

    tool_results = []

    while i < n:
        line = lines[i].strip()

        # ---------------- TEXT ----------------
        if line.startswith("TEXT:"):
            i += 1
            buf = []

            while i < n and END_MARK not in lines[i]:
                buf.append(lines[i])
                i += 1

            content = "\n".join(buf).strip()

            if content:
                print(content)

            i += 1
            continue

        # ---------------- TOOL ----------------
        if line.startswith("TOOL:"):
            raw = line[len("TOOL:"):].strip()

            i += 1

            # fallback dla multiline JSON
            if not raw:
                buf = []

                while i < n and END_MARK not in lines[i]:
                    buf.append(lines[i])
                    i += 1

                raw = "\n".join(buf).strip()

            # skip END line
            if i < n and END_MARK in lines[i]:
                i += 1

            try:
                if not raw:
                    raise ValueError("Empty TOOL JSON")

                data = json.loads(raw)

                name = data["name"]
                args = data.get("args", [])

                try:
                    result = call_tool(name, args)

                    # 🔥 zapisujemy wynik toola
                    tool_results.append({
                        "name": name,
                        "args": args,
                        "result": result
                    })
                except Exception as e:
                    # 🔥 zapisujemy wynik toola
                    tool_results.append({
                        "name": name,
                        "args": args,
                        "result": f"TOOL CALL ERROR: {e}"
                    })
                    
                    print("TOOL CALL ERROR: ", e)

            except Exception as e:
                print("TOOL PARSE ERROR:", e)
                print("RAW WAS:", repr(raw))

            continue

        i += 1

    return tool_results