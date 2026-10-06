import re
import os

base_dir = r"d:\Software Engineering\Development\InternRoleFinder"

# 1. Update python file
with open(os.path.join(base_dir, "backend", "startups_500_python.py"), "r") as f:
    new_python_list = f.read()

with open(os.path.join(base_dir, "backend", "app", "indian_jobs_data.py"), "r", encoding='utf-8') as f:
    content = f.read()

# Replace INDIAN_COMPANIES_LIST = [...]
content = re.sub(r'INDIAN_COMPANIES_LIST\s*=\s*\[.*?\]', new_python_list, content, flags=re.DOTALL)

with open(os.path.join(base_dir, "backend", "app", "indian_jobs_data.py"), "w", encoding='utf-8') as f:
    f.write(content)

# 2. Update README.md
with open(os.path.join(base_dir, "backend", "startups_500_readme.md"), "r", encoding='utf-8') as f:
    new_readme_list = f.read()

with open(os.path.join(base_dir, "README.md"), "r", encoding='utf-8') as f:
    readme = f.read()

pattern = r'(### Indian Startups & Tech Companies\s*).*?(?=\s*> \[!TIP\])'
readme = re.sub(pattern, r'\1\n' + new_readme_list + r'\n', readme, flags=re.DOTALL)

with open(os.path.join(base_dir, "README.md"), "w", encoding='utf-8') as f:
    f.write(readme)

print("Files updated successfully!")
