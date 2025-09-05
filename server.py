import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("local-folder-server")

# Workspace path (folder to store files/logs)
WORKSPACE = os.path.abspath("workspace")
LOG_FILE = os.path.join(WORKSPACE, "network_scans.json")

# Ensure workspace directory exists
os.makedirs(WORKSPACE, exist_ok=True)

# File Operations
@mcp.tool()
def list_files(directory: str = "") -> dict:
    """List all files and directories in the specified directory (relative to workspace)."""
    target_dir = os.path.join(WORKSPACE, directory)
    
    if not os.path.exists(target_dir):
        raise ValueError(f"Directory '{directory}' does not exist in workspace")
    
    if not os.path.isdir(target_dir):
        raise ValueError(f"'{directory}' is not a directory")
    
    items = os.listdir(target_dir)
    files = []
    dirs = []
    
    for item in items:
        item_path = os.path.join(target_dir, item)
        if os.path.isdir(item_path):
            dirs.append(item + "/")
        else:
            files.append(item)
    
    # Sort directories first, then files
    sorted_items = sorted(dirs) + sorted(files)
    
    return {
        "result": sorted_items, 
        "text": f"Contents of '{directory}':\n" + "\n".join(sorted_items) if sorted_items else "Directory is empty"
    }


@mcp.tool()
def read_file(filename: str) -> dict:
    """Read the contents of a file from the workspace."""
    filepath = os.path.join(WORKSPACE, filename)
    
    if not os.path.isfile(filepath):
        raise ValueError("File not found")
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    return {
        "result": content, 
        "text": f"--- {filename} ---\n{content}"
    }


@mcp.tool()
def write_file(filename: str, content: str) -> dict:
    """Write content to a file in the workspace. Creates file if it doesn't exist."""
    filepath = os.path.join(WORKSPACE, filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    return {
        "result": f"✅ Wrote to {filename}", 
        "text": f"Updated {filename}"
    }


@mcp.tool()
def append_file(filename: str, content: str) -> dict:
    """Append content to a file in the workspace."""
    filepath = os.path.join(WORKSPACE, filename)
    
    if not os.path.isfile(filepath):
        raise ValueError("File not found")
    
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(content)
    
    return {
        "result": f"✅ Appended to {filename}", 
        "text": f"Appended content to {filename}"
    }


@mcp.tool()
def delete_file(filename: str) -> dict:
    """Delete a file from the workspace."""
    filepath = os.path.join(WORKSPACE, filename)
    
    if not os.path.exists(filepath):
        raise ValueError("File not found")
    
    if os.path.isdir(filepath):
        raise ValueError("Use delete_directory for directories")
    
    os.remove(filepath)
    
    return {
        "result": f"✅ Deleted {filename}", 
        "text": f"Deleted {filename}"
    }


@mcp.tool()
def create_directory(directory: str) -> dict:
    """Create a new directory in the workspace."""
    dirpath = os.path.join(WORKSPACE, directory)
    
    if os.path.exists(dirpath):
        raise ValueError("Directory already exists")
    
    os.makedirs(dirpath)
    
    return {
        "result": f"✅ Created directory {directory}", 
        "text": f"Created directory {directory}"
    }


@mcp.tool()
def delete_directory(directory: str) -> dict:
    """Delete a directory and all its contents from the workspace."""
    dirpath = os.path.join(WORKSPACE, directory)
    
    if not os.path.exists(dirpath):
        raise ValueError("Directory not found")
    
    if not os.path.isdir(dirpath):
        raise ValueError("Path is not a directory")
    
    # Prevent accidental deletion of workspace root
    if os.path.abspath(dirpath) == os.path.abspath(WORKSPACE):
        raise ValueError("Cannot delete workspace root")
    
    shutil.rmtree(dirpath)
    
    return {
        "result": f"✅ Deleted directory {directory}", 
        "text": f"Deleted directory {directory} and all its contents"
    }


@mcp.tool()
def file_info(filename: str) -> dict:
    """Get information about a file or directory."""
    filepath = os.path.join(WORKSPACE, filename)
    
    if not os.path.exists(filepath):
        raise ValueError("File or directory not found")
    
    stat = os.stat(filepath)
    is_dir = os.path.isdir(filepath)
    
    info = {
        "name": filename,
        "is_directory": is_dir,
        "size": stat.st_size if not is_dir else 0,
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "absolute_path": os.path.abspath(filepath)
    }
    
    if is_dir:
        # Count files and subdirectories
        items = os.listdir(filepath)
        dir_count = sum(os.path.isdir(os.path.join(filepath, item)) for item in items)
        file_count = len(items) - dir_count
        info["contents"] = f"{file_count} files, {dir_count} directories"
    
    text = f"Info for {filename}:\n"
    for key, value in info.items():
        if key != "absolute_path":  # Skip absolute path in text output for brevity
            text += f"{key.replace('_', ' ').title()}: {value}\n"
    
    return {
        "result": info, 
        "text": text
    }


@mcp.tool()
def search_files(query: str, extension: str = "") -> dict:
    """Search for files in the workspace containing the query text."""
    matches = []
    
    for root, dirs, files in os.walk(WORKSPACE):
        for file in files:
            if extension and not file.endswith(extension):
                continue
                
            filepath = os.path.join(root, file)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    if query.lower() in content.lower():
                        # Make path relative to workspace
                        rel_path = os.path.relpath(filepath, WORKSPACE)
                        matches.append({
                            "file": rel_path,
                            "matches": content.lower().count(query.lower())
                        })
            except (UnicodeDecodeError, IOError):
                # Skip binary files or files that can't be read
                continue
    
    text = f"Found {len(matches)} files containing '{query}'"
    if extension:
        text += f" with extension '{extension}'"
    text += ":\n"
    
    for match in matches:
        text += f"- {match['file']} ({match['matches']} matches)\n"
    
    return {
        "result": matches, 
        "text": text
    }


@mcp.tool()
def find_files(pattern: str = "*") -> dict:
    """Find files in the workspace matching a pattern (e.g., *.py, *.txt)."""
    matches = []
    
    for root, dirs, files in os.walk(WORKSPACE):
        for file in files:
            if pattern == "*" or file.endswith(pattern.lstrip('*')):
                rel_path = os.path.relpath(os.path.join(root, file), WORKSPACE)
                matches.append(rel_path)
    
    text = f"Found {len(matches)} files matching pattern '{pattern}':\n"
    text += "\n".join(matches) if matches else "No files found"
    
    return {
        "result": matches, 
        "text": text
    }

@mcp.tool()
def get_workspace_info() -> dict:
    """Get information about the workspace."""
    total_size = 0
    file_count = 0
    dir_count = 0
    
    for root, dirs, files in os.walk(WORKSPACE):
        dir_count += len(dirs)
        file_count += len(files)
        for file in files:
            filepath = os.path.join(root, file)
            try:
                total_size += os.path.getsize(filepath)
            except OSError:
                pass
    
    # Convert size to human readable format
    size_units = ["B", "KB", "MB", "GB"]
    size_index = 0
    while total_size >= 1024 and size_index < len(size_units) - 1:
        total_size /= 1024.0
        size_index += 1
    
    info = {
        "path": WORKSPACE,
        "total_files": file_count,
        "total_directories": dir_count,
        "total_size": f"{total_size:.2f} {size_units[size_index]}"
    }
    
    text = "Workspace Information:\n"
    for key, value in info.items():
        text += f"{key.replace('_', ' ').title()}: {value}\n"
    
    return {
        "result": info, 
        "text": text
    }


if __name__ == "__main__":
    mcp.run()