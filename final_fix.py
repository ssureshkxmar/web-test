import os
import glob
import re

TEMPLATES_DIR = '/home/sureshkumar-s/Documents/ECG-Digitiser/templates'
files = glob.glob(os.path.join(TEMPLATES_DIR, '*.html'))

for fpath in files:
    with open(fpath, 'r') as f:
        content = f.read()

    # 1. Fix CSS fragments (like the dangling 100% { ... })
    # This usually happens if the previous regex only partially matched.
    # We'll search for "100% {" at the start of a line (after indentation) that isn't inside a @keyframes
    lines = content.split('\n')
    new_lines = []
    skip = False
    for i, line in enumerate(lines):
        # Extremely specific fix for the observed fragment
        if '100% {' in line and i > 0 and lines[i-1].strip() == '':
            # check if next lines are transform/opacity and then }
            if i+3 < len(lines) and 'transform' in lines[i+1] and 'opacity' in lines[i+2] and '}' in lines[i+3]:
                skip = True
                continue
        if skip:
            if '}' in line:
                skip = False
            continue
        new_lines.append(line)
    content = '\n'.join(new_lines)

    # 2. Add missing closing braces in JS
    # Fix saveProfileChanges
    content = re.sub(
        r'\}\s*catch\s*\(e\)\s*\{\s*console\.error\(e\);\s*\}\s*(?!\s*\})\s*//\s*Close dropdown',
        '} catch (e) { console.error(e); }\n        }\n\n        // Close dropdown',
        content
    )
    
    # Also handle cases where there is no comment
    content = re.sub(
        r'\}\s*catch\s*\(e\)\s*\{\s*console\.error\(e\);\s*\}\s*(?!\s*\})\s*window\.onclick',
        '} catch (e) { console.error(e); }\n        }\n\n        window.onclick',
        content
    )

    # 3. Ensure window.onclick is closed
    # Match the whole window.onclick block and replace it correctly
    if 'profileDropdown' in content:
        onclick_pattern = r'window\.onclick\s*=\s*function\s*\(event\)\s*\{.*?\}\s*(?=</script>|window\.onload)'
        onclick_fixed = '''window.onclick = function (event) {
            if (!event.target.closest('.profile-container')) {
                if (document.getElementById('profileDropdown')) {
                    document.getElementById('profileDropdown').classList.remove('show');
                }
            }
            if (event.target.classList.contains('modal')) {
                closeProfileSettings();
            }
        };'''
        content = re.sub(onclick_pattern, onclick_fixed + '\n        ', content, flags=re.DOTALL)
    else:
        onclick_pattern = r'window\.onclick\s*=\s*function\s*\(event\)\s*\{.*?\}\s*(?=</script>|window\.onload|//)'
        onclick_fixed = '''window.onclick = function (event) {
            if (event.target.classList.contains('modal')) {
                closeProfileSettings();
            }
        };'''
        content = re.sub(onclick_pattern, onclick_fixed + '\n        ', content, flags=re.DOTALL)

    # 4. Final check for closing braces before </script>
    # If we have an odd number of braces in the script section... 
    # That's too risky. Let's just trust the regexes for now.

    with open(fpath, 'w') as f:
        f.write(content)

print("Final fix completed")
