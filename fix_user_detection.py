#!/usr/bin/env python3
"""Script to fix user_id detection logic in db_manager.py"""

import re

def fix_user_detection():
    with open('db_manager.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern 1: Find try/except blocks with web_user_id_val = int(user_id) and dual SQL
    # Replace with is_web_user() helper

    # This pattern matches:
    # try:
    #     web_user_id_val = int(user_id)
    #     ... SQL for web_user_id ...
    # except ValueError:
    #     ... SQL for user_id ...

    pattern = r'''(\s+)try:\s+
            web_user_id_val = int\(user_id\)\s+
            (.*?)
        except ValueError:\s+
            (.*?)
        (\n\s+)(rows?|cur|budget)'''

    # For safety, let's do a simpler approach - just replace the detection logic
    # Replace: web_user_id_val = int(user_id)
    # With helper that includes the range check

    simple_pattern = r'(\s+)try:\s+web_user_id_val = int\(user_id\)\s+'

    # Count occurrences first
    matches = re.findall(simple_pattern, content, re.MULTILINE)
    print(f"Found {len(matches)} patterns to potentially fix")

    # Manual replacement - let's find each occurrence and its context
    lines = content.split('\n')

    in_try_block = False
    try_start = -1
    fixed_content = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this line has the problematic pattern
        if '    try:' in line or '        try:' in line:
            # Check next line
            if i + 1 < len(lines) and 'web_user_id_val = int(user_id)' in lines[i + 1]:
                # This is a block we need to fix
                indent = line[:len(line) - len(line.lstrip())]

                # Replace with is_web_user call
                fixed_content.append(f'{indent}is_web, processed_id = is_web_user(user_id)')
                fixed_content.append(f'{indent}')
                fixed_content.append(f'{indent}if is_web:')

                # Skip the try line and int(user_id) line
                i += 2

                # Copy SQL until except
                while i < len(lines) and 'except ValueError:' not in lines[i]:
                    # Replace web_user_id_val with processed_id
                    modified_line = lines[i].replace('web_user_id_val', 'processed_id')
                    fixed_content.append(modified_line)
                    i += 1

                # Replace except ValueError: with else:
                if i < len(lines) and 'except ValueError:' in lines[i]:
                    except_indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
                    fixed_content.append(f'{except_indent}else:')
                    i += 1

                continue

        fixed_content.append(line)
        i += 1

    # Write the fixed content
    with open('db_manager.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(fixed_content))

    print("Fixed db_manager.py")

if __name__ == '__main__':
    fix_user_detection()
