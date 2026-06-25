import os
import re
import sys
import xml.etree.ElementTree as ET

def get_js_content(repo_path):
    api_path = os.path.join(repo_path, 'api', 'mega.js')
    if not os.path.exists(api_path):
        raise FileNotFoundError(f"Could not find mega.js at {api_path}")
    with open(api_path, 'r') as f:
        return f.read()

def get_py_content(file_path):
    with open(file_path, 'r') as f:
        return f.read()

def update_addon_version(addon_xml_path):
    tree = ET.parse(addon_xml_path)
    root = tree.getroot()
    version = root.attrib.get('version', '1.0.0')
    
    # Increment patch version
    parts = version.split('.')
    if len(parts) == 3:
        parts[2] = str(int(parts[2]) + 1)
        new_version = '.'.join(parts)
        root.attrib['version'] = new_version
        tree.write(addon_xml_path, encoding='UTF-8', xml_declaration=True)
        print(f"Updated addon version: {version} -> {new_version}")
        return new_version
    return version

def extract_and_patch(js_content, py_content):
    changes_made = False
    
    # 1. keygenHashMultVal
    mult_match = re.search(r'var keygenHashMultVal = (\d+)n', js_content)
    if mult_match:
        mult_val = mult_match.group(1)
        new_py, count = re.subn(r'keygen_hash_mult_val = \d+', f'keygen_hash_mult_val = {mult_val}', py_content)
        if count > 0 and new_py != py_content:
            py_content = new_py
            changes_made = True
            print(f"Updated keygen_hash_mult_val to {mult_val}")

    # 2. keygenXORVal
    xor_match = re.search(r'var keygenXORVal = (\d+);', js_content)
    if xor_match:
        xor_val = xor_match.group(1)
        new_py, count = re.subn(r'chr\(ord\(c\) \^ \d+\)', f'chr(ord(c) ^ {xor_val})', py_content)
        if count > 0 and new_py != py_content:
            py_content = new_py
            changes_made = True
            print(f"Updated keygenXORVal to {xor_val}")

    # 3. keygenShiftVal
    shift_match = re.search(r'var keygenShiftVal = (\d+)', js_content)
    if shift_match:
        shift_val = shift_match.group(1)
        new_py, count = re.subn(r'pivot = \(l_hash % len\(temp_key\)\) \+ \d+', f'pivot = (l_hash % len(temp_key)) + {shift_val}', py_content)
        if count > 0 and new_py != py_content:
            py_content = new_py
            changes_made = True
            print(f"Updated keygenShiftVal to {shift_val}")
            
    # 4. PRNG constants
    lcg_mult_match = re.search(r'shuffleNum \* (\d+)n \+ (\d+)n', js_content)
    if lcg_mult_match:
        lcg_mult = lcg_mult_match.group(1)
        lcg_add = lcg_mult_match.group(2)
        new_py, count = re.subn(r'\(seed \* \d+ \+ \d+\)', f'(seed * {lcg_mult} + {lcg_add})', py_content)
        new_py, count2 = re.subn(r'\(shuffle_num \* \d+ \+ \d+\)', f'(shuffle_num * {lcg_mult} + {lcg_add})', new_py)
        if (count > 0 or count2 > 0) and new_py != py_content:
            py_content = new_py
            changes_made = True
            print(f"Updated PRNG constants to {lcg_mult} and {lcg_add}")

    return py_content, changes_made

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python transform.py <path_to_mega_embed_2_repo> <path_to_megacloud_addon>")
        sys.exit(1)
        
    repo_path = sys.argv[1]
    addon_path = sys.argv[2]
    
    js_content = get_js_content(repo_path)
    py_file = os.path.join(addon_path, 'resources', 'lib', 'megacloud.py')
    py_content = get_py_content(py_file)
    
    new_py_content, changed = extract_and_patch(js_content, py_content)
    
    if changed:
        with open(py_file, 'w') as f:
            f.write(new_py_content)
        print("Successfully updated megacloud.py with upstream values.")
        update_addon_version(os.path.join(addon_path, 'addon.xml'))
        sys.exit(0) # Changes made
    else:
        print("No changes needed. Python logic is up-to-date with upstream JavaScript.")
        sys.exit(2) # No changes
