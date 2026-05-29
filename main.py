from ollama import chat
from ollama import ChatResponse
from os import listdir
import subprocess
from systemprompt import register_tool, build_systemprompt, call_tool
from response_parser import StreamingLLMParser
from utils import resolve_safe_path, resolve_path_project_root_allowed, resolve_strict_path
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings

kb = KeyBindings()

session = PromptSession(multiline=True, key_bindings=kb)

@kb.add("s-tab")
def _(event):
    event.current_buffer.insert_text("\n")

@kb.add("enter")
def _(event):
    event.app.exit(result=event.app.current_buffer.text)

def read_file(path, startline = 0, endline = 128):
    safe_path = resolve_safe_path(path)
    startline = int(startline)
    endline = int(endline)

    lines = safe_path.read_text(encoding="utf-8").splitlines(keepends=True)
    return "".join(lines[startline:endline])

def create_file(path):
    safe_path = resolve_safe_path(path)
    safe_path.touch(exist_ok=False)
    return "Success!"

def read_dir(path, start_index = 0):
    safe_path = resolve_path_project_root_allowed(path)
    files = listdir(safe_path)
    files = files[start_index:(start_index + 64)]
    
    files_str = "\n".join(files);
    
    return f"Files in {safe_path}:\n{files_str}"

def write_file(path, new_content):
    safe_path = resolve_safe_path(path)
    safe_path.write_text(new_content, encoding="utf-8")
    return "Success"

def mkdir(path):
    safe_path = resolve_strict_path(path)
    safe_path.mkdir()

def exec_cmd(*cmd):
    while True:
        res = input(
            f"The agent wants to run this command:\n`{cmd}`\n"
            f"confirm execution of the command? [y/n]: "
        ).lower()

        if res == "y":
            proc = subprocess.run(
                list(cmd),
                capture_output=True,
                text=True
            )

            return f"Exit code: {proc.returncode}; Stdout: `{proc.stdout}`; Stderr: `{proc.stderr}`"

        elif res == "n":
            print("Command execution was skipped")
            return "ERROR: User refused to run this command"

        else:
            print("Invalid option")
            continue

register_tool("readfile", "Reads file using relative path", ["\"path\": string - relative (from project root) path to file", "\"startline\" (optional, default: 0): integer - the line from which the reading should begin", "\"endline\" (optional, default: 128): integer - line to which the file is to be read"], read_file)
register_tool("writefile", "Overwrites file with the new content using relative path **without creating**", ["\"path\": string - relative (from project root) path to file", "\"new_content\": string - new content for file" ], write_file)
register_tool("readdir", "Lists up to 64 files and subdirectories in given directory", ["\"path\": string - relative (from project root) path to file", "\"start_index\" (optional, default: 5): integer - skips first N files" ], read_dir)
register_tool("createfile", "Creates new empty file using relative path", ["\"path\": string - relative (from project root) path to file" ], create_file)
register_tool("mkdir", "Creates new empty directory using relative path", ["\"path\": string - relative (from project root) path to file" ], mkdir)
register_tool("runcmd", "Executes a shell command. Command and args must be given as single argument. Neither you nor the user have access to stdin, so whenever possible, run commands that do not require user intervention.", ["\"cmd\": string[] - name of cmd (index 0) with arguments (index 1-n)" ], exec_cmd)

tools_result = None

parser = StreamingLLMParser(call_tool)

def format_tool_results(tool_results):
    lines = [
        "TOOL RESULTS from your previous tool call.",
        "Use these results to continue. If they are sufficient, answer with TEXT only.",
        "Do not repeat the same TOOL call unless the result is incomplete or an error occurred.",
        ""
    ]

    for res in tool_results:
        if "error" in res:
            lines.append(f"- Tool parse/call error: {res['error']}")
            lines.append(f"  Raw: {res.get('raw', '')}")
            continue

        lines.append(f"- Tool name: {res['name']}")
        lines.append(f"  Args: {res['args']}")
        lines.append("  Result:")
        lines.append(str(res["result"]))
        lines.append("")

    return "\n".join(lines)

messages = [
    {
        "role": "system",
        "content": build_systemprompt()
    }
]

while True:

    max_tool_rounds = 16
    tool_round = 0

    prompt = session.prompt(">>> ")
    
    messages.append({
        "role": "user",
        "content": prompt
    })

    while True:
        current_tool_results = []
        assistant_content = ""

        response = chat(
            model="gemma3:4b",
            messages=messages,
            stream=True
        )

        for chunk in response:
            content = chunk.message.content

            if not content:
                continue

            assistant_content += content
            results = parser.feed(content)

            for result in results:
                if isinstance(result, dict):
                    current_tool_results.append(result)

        messages.append({
            "role": "assistant",
            "content": assistant_content
        })

        if not current_tool_results:
            break

        tool_round += 1
        if tool_round >= max_tool_rounds:
            print("\n[STOP] Max tool rounds reached.")
            break

        tools_result = current_tool_results
        messages.append({
            "role": "user",
            "content": format_tool_results(tools_result)
        })
