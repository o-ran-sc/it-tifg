# Copyright 2025 highstreet technologies USA Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import difflib
import os
import re
from pathlib import Path


def patch_root_models(file_content):
    """
    Replace classes using __root__ with RootModel

    For example:
    class Contacts(BaseModel):
        __root__: List[Contact] = Field(
            ...,
            description='Contact information for person / party involved in the testing or an aspect of the testing.',
        )

    becomes:
    class Contacts(RootModel[List[Contact]]):
        pass
    """
    # Process line by line, keeping track of indentation levels
    lines = file_content.split('\n')
    result_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Look for class definitions inheriting from BaseModel
        if re.match(r'^class\s+(\w+)\s*\(\s*BaseModel\s*\)\s*:', line):
            class_name = re.match(r'^class\s+(\w+)\s*\(\s*BaseModel\s*\)\s*:', line).group(1)
            class_start = i

            # Look ahead to check if this class contains a __root__ field
            has_root = False
            root_type = None
            j = i + 1

            # Store the class content to analyze
            class_content = []
            class_indent = None

            # Determine the indentation level of the class body
            if j < len(lines) and lines[j].strip():
                # Find the first non-empty line to get the indentation
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines):
                    class_indent = len(lines[j]) - len(lines[j].lstrip())

            # If we couldn't determine indentation, use a default
            if class_indent is None:
                class_indent = 4

            # Collect all class content at this indentation level
            j = i + 1
            while j < len(lines):
                # Skip empty lines
                if not lines[j].strip():
                    class_content.append(lines[j])
                    j += 1
                    continue

                # If we hit a line that's not indented at least as much as class_indent,
                # we've reached the end of the class
                current_indent = len(lines[j]) - len(lines[j].lstrip())
                if current_indent < class_indent and lines[j].strip():
                    break

                class_content.append(lines[j])
                j += 1

            # Look for __root__ in the class content
            for idx, content_line in enumerate(class_content):
                if re.search(r'^\s*__root__\s*:', content_line):
                    has_root = True
                    # Extract the type from the __root__ field
                    root_type_match = re.search(r'^\s*__root__\s*:\s*(.*?)\s*=\s*Field', content_line)
                    if root_type_match:
                        root_type = root_type_match.group(1).strip()
                    break

            if has_root and root_type:
                # Replace the class with RootModel version
                result_lines.append(f"class {class_name}(RootModel[{root_type}]):")
                result_lines.append(f"{' ' * class_indent}pass")

                # Skip to the end of the original class
                i = class_start + len(class_content) + 1
            else:
                # Keep the class declaration as is
                result_lines.append(line)
                i += 1
        else:
            # Keep the line as is
            result_lines.append(line)
            i += 1

    return '\n'.join(result_lines)


def patch_constr_blocks(content):
    """
    Replace all forms of constr(...) with Annotated[str, StringConstraints(...)]

    Also fixes missing closing brackets in Union[ constructs.

    Examples:
    constr(max_length=255) -> Annotated[str, StringConstraints(max_length=255)]
    constr(regex=r'^[a-z0-9-]+$', max_length=255) -> Annotated[str, StringConstraints(pattern=r'^[a-z0-9-]+$', max_length=255)]
    """
    import re

    # Now handle constr replacements
    constr_pattern = re.compile(r'constr\((.*?)\)', re.DOTALL)

    def constr_repl(match):
        args = match.group(1)
        # Replace 'regex=' with 'pattern=' for Pydantic v2 compatibility
        args = re.sub(r'regex=', 'pattern=', args)
        return f"Annotated[str, StringConstraints({args})]"

    # Replace all instances of constr(...)
    content = constr_pattern.sub(constr_repl, content)

    return content


def fix_regex_issues(content):
    """
    Replace 'regex=' with 'pattern=' in StringConstraints to accommodate Pydantic v2 API changes.

    Args:
        content (str): The content of the file to process

    Returns:
        str: The processed content
    """
    # Regular expression to match StringConstraints with regex parameter
    pattern = r'StringConstraints\(([^)]*\bregex\b[^)]*)\)'

    def replace_regex_with_pattern(match):
        constraints_content = match.group(1)
        # Replace 'regex=' with 'pattern=' while preserving the rest of the parameters
        updated_content = constraints_content.replace('regex=', 'pattern=')
        return f"StringConstraints({updated_content})"

    # Perform the replacement
    updated_content = re.sub(pattern, replace_regex_with_pattern, content)

    return updated_content


def ensure_imports(file_content):
    """Add required imports if they don't exist"""
    # Check for necessary imports
    needs_annotated = 'Annotated' not in file_content
    needs_rootmodel = 'RootModel' not in file_content
    needs_stringconstraints = 'StringConstraints' not in file_content
    needs_literal = 'Literal' not in file_content

    # Add imports if needed
    if needs_annotated or needs_literal:
        # Look for existing typing imports
        typing_import = re.search(r'from typing import (.*)', file_content)
        if typing_import:
            # Add Annotated to existing imports
            imports = typing_import.group(1).split(', ')
            if needs_annotated:
                imports.append('Annotated')
            if needs_literal:
                imports.append('Literal')
            imports = sorted(set(imports))  # Remove duplicates and sort

            new_import = f"from typing import {', '.join(imports)}"
            file_content = file_content.replace(typing_import.group(0), new_import)
        else:
            # Add new typing import after other imports
            pos = file_content.find('\n\n', file_content.find('import'))
            if pos > 0:
                if needs_annotated and needs_literal:
                    file_content = file_content[:pos] + '\nfrom typing import Annotated, Literal' + file_content[pos:]
                elif needs_annotated:
                    file_content = file_content[:pos] + '\nfrom typing import Annotated' + file_content[pos:]
                elif needs_literal:
                    file_content = file_content[:pos] + '\nfrom typing import Literal' + file_content[pos:]
            else:
                # Add at the top if no other imports found
                if needs_annotated and needs_literal:
                    file_content = 'from typing import Annotated, Literal\n\n' + file_content
                elif needs_annotated:
                    file_content = 'from typing import Annotated\n\n' + file_content
                elif needs_literal:
                    file_content = 'from typing import Literal\n\n' + file_content



    # Add pydantic imports
    if needs_rootmodel or needs_stringconstraints:
        pydantic_imports_to_add = []
        if needs_rootmodel:
            pydantic_imports_to_add.append('RootModel')
        if needs_stringconstraints:
            pydantic_imports_to_add.append('StringConstraints')

        # Look for existing pydantic imports
        pydantic_import = re.search(r'from pydantic import (.*)', file_content)
        if pydantic_import:
            # Add to existing imports
            imports = pydantic_import.group(1).split(', ')
            imports.extend(pydantic_imports_to_add)
            imports = sorted(set(imports))  # Remove duplicates and sort

            new_import = f"from pydantic import {', '.join(imports)}"
            file_content = file_content.replace(pydantic_import.group(0), new_import)
        else:
            # Add new pydantic import
            new_import = f"from pydantic import {', '.join(pydantic_imports_to_add)}"
            pos = file_content.find('\n\n', file_content.find('import'))
            if pos > 0:
                file_content = file_content[:pos] + '\n' + new_import + file_content[pos:]
            else:
                # Add at the top if no other imports found
                file_content = new_import + '\n\n' + file_content

    return file_content

def fix_missing_brackets(file_content):
    """Fix missing closing brackets in Annotated[str, StringConstraints(...)] patterns"""
    # Fix specific pattern where closing bracket is missing before = Field
    pattern = r'(Annotated\[str, StringConstraints\([^]]*?\))\s*=\s*Field'
    replacement = r'\1] = Field'

    # Apply the fix
    file_content = re.sub(pattern, replacement, file_content)

    return file_content


def fix_const_parameter(text):
    """
    Replace const=True in Field() with Literal type hints to be compatible with Pydantic v2.

    Args:
        text (str): The source code text to patch

    Returns:
        str: The patched source code
    """
    import re

    # Find all Field declarations with const=True - handle multi-line cases
    field_pattern = re.compile(
        r'(\w+)\s*:\s*(\w+)\s*=\s*Field\(\s*([\s\S]*?)\s*const=True\s*([\s\S]*?)\)',
        re.DOTALL
    )
    matches = list(field_pattern.finditer(text))

    # Start from the end to avoid messing up character positions with earlier replacements
    for match in reversed(matches):
        field_name = match.group(1)  # The variable name
        field_type = match.group(2)  # The original type
        prefix = match.group(3)  # Everything before const=True
        suffix = match.group(4)  # Everything after const=True

        # Extract the default value from the prefix
        # This needs to handle multi-line definitions
        value = None
        # Clean up the prefix (remove comments, extra whitespace)
        clean_prefix = re.sub(r'#.*?\n', '', prefix)
        clean_prefix = re.sub(r'\s+', ' ', clean_prefix).strip()

        # Look for the first parameter without a name (likely the default value)
        if clean_prefix and '=' not in clean_prefix.split(',')[0]:
            first_param = clean_prefix.split(',')[0].strip()
            if first_param:
                value = first_param

        # If no value found but there's content, try to extract numeric or string literals
        if not value and clean_prefix:
            value_match = re.search(r'([-+]?\d+(?:\.\d+)?|"[^"]*"|\'[^\']*\'|True|False|None)', clean_prefix)
            if value_match:
                value = value_match.group(1)

        # Default to 1 if no value found (common for schemaVersion)
        if not value:
            value = "1"

        # Create the replacement with Literal type
        # Keep the original formatting
        replacement = f"{field_name}: Literal[{value}] = Field({prefix}"

        # Remove const=True from the parameters
        cleaned_suffix = re.sub(r'^\s*,?\s*', '', suffix, 1)

        # Put it all together
        replacement += cleaned_suffix + ")"

        # Replace the original text
        text = text[:match.start()] + replacement + text[match.end():]

    return text


model_path = Path("src/hybrid_mplane_test_runner/models/testresult_models.py")
if not model_path.exists():
    print("❌ Model file not found.")
    exit(1)

# Add debug mode to save intermediate results
DEBUG = True
debug_dir = Path("debug")

# Load the model file
with open(model_path, 'r') as f:
    original = f.read()

# Apply transformations
text = original

text = ensure_imports(text)
text = patch_root_models(text)
text = patch_constr_blocks(text)
text = fix_regex_issues(text)
text = fix_missing_brackets(text)
text = fix_const_parameter(text)


# Write out the patched file
with open(model_path, 'w') as f:
    f.write(text)

if DEBUG:
    try:
        # Save debug information
        os.makedirs(debug_dir, exist_ok=True)
        print(f"Debug directory created at: {debug_dir.absolute()}")

        # Generate diff for debugging
        diff_file = debug_dir / 'diff.txt'
        with open(diff_file, 'w') as f:
            diff = difflib.unified_diff(
                original.splitlines(keepends=True),
                text.splitlines(keepends=True),
                fromfile='original',
                tofile='patched'
            )
            f.writelines(diff)
        print(f"Diff saved to: {diff_file.absolute()}")

        # Also save the final patched file
        patched_file = debug_dir / 'patched.py'
        with open(patched_file, 'w') as f:
            f.write(text)
        print(f"Patched file saved to: {patched_file.absolute()}")
    except Exception as e:
        print(f"Error creating debug files: {e}")
