from pathlib import Path

PROJECT_ROOT = Path.cwd().resolve()

def resolve_safe_path(user_path: str) -> Path:
    target_path = Path(user_path)
    
    full_path = (PROJECT_ROOT / target_path).resolve()

    if not full_path.is_relative_to(PROJECT_ROOT):
        raise PermissionError("Sandbox escape detected")
        
    if full_path == PROJECT_ROOT:
        raise PermissionError("Cannot overwrite project root")

    return full_path

def resolve_strict_path(user_path: str) -> Path:
    target_path = Path(user_path)
    
    full_path = (PROJECT_ROOT / target_path)

    parent_path = full_path.parent.resolve()

    if not parent_path.is_relative_to(PROJECT_ROOT):
        raise PermissionError("Sandbox escape detected via parent directory")

    final_path = full_path.resolve(strict=False) 
    
    if final_path.exists():
        raise FileExistsError(f"The path '{user_path}' already exists.")
        
    if final_path == PROJECT_ROOT:
        raise PermissionError("Cannot modify or overwrite project root")

    return final_path

def resolve_path_project_root_allowed(user_path: str) -> Path:
    target_path = Path(user_path)
    
    full_path = (PROJECT_ROOT / target_path).resolve()

    if not full_path.is_relative_to(PROJECT_ROOT):
        raise PermissionError("Sandbox escape detected")
        
    if full_path == PROJECT_ROOT:
        raise PermissionError("Cannot overwrite project root")

    return full_path