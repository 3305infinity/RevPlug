import os

root_dirs = [
    r"c:\Users\Nishtha\OneDrive\Desktop\revenue_recovery\revenue_recovery",
    r"c:\Users\Nishtha\OneDrive\Desktop\revenue_recovery\docs",
]

extensions = {".py", ".ts", ".tsx", ".md", ".json", ".html", ".css", ".env", ".example", ".txt"}

replacements = [
    ("RevPlug", "RevPlug"),
    ("revplug", "revplug"),
    ("REVPLUG", "REVPLUG"),
    ("RevPlug", "RevPlug"),
]

changed_files = []

for base_dir in root_dirs:
    for root, dirs, files in os.walk(base_dir):
        if "node_modules" in root or ".next" in root or ".git" in root or "__pycache__" in root:
            continue
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in extensions or file in ("pyproject.toml", ".env.example"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    new_content = content
                    for old, new in replacements:
                        new_content = new_content.replace(old, new)
                    
                    if new_content != content:
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        changed_files.append(filepath)
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")

print(f"Successfully updated brand name to RevPlug in {len(changed_files)} files!")
