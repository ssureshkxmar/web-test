import os
import glob

TEMPLATES_DIR = '/home/sureshkumar-s/Documents/ECG-Digitiser/templates'
files = glob.glob(os.path.join(TEMPLATES_DIR, '*.html'))

for fpath in files:
    with open(fpath, 'r') as f:
        content = f.read()
    
    # Check for window.onclick being closed
    if 'window.onclick = function (event) {' in content:
        if '};' not in content.split('window.onclick = function (event) {')[1].split('</script>')[0]:
            print(f"ISSUE in {fpath}: window.onclick not closed correctly")
        else:
            print(f"OK: {fpath} JS looks closed")
    
    # Check for saveProfileChanges or other try-catch being closed
    if '} catch (e) { console.error(e); }' in content:
        # Check if there is a } after it before window.onclick
        idx = content.find('} catch (e) { console.error(e); }')
        after = content[idx+33:idx+100]
        if '}' not in after and 'window.onclick' in after:
             print(f"ISSUE in {fpath}: Missing closing brace after catch")

