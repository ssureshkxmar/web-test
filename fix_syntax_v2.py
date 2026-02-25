import os
import glob
import re

TEMPLATES_DIR = '/home/sureshkumar-s/Documents/ECG-Digitiser/templates'
files = glob.glob(os.path.join(TEMPLATES_DIR, '*.html'))

for fpath in files:
    with open(fpath, 'r') as f:
        content = f.read()
    
    # Fix saveProfileChanges missing closing brace
    # Search for the pattern try { ... } catch (e) { ... } followed by window.onclick
    # If there is no } between } catch (e) { console.error(e); } and window.onclick, add it.
    
    content = re.sub(
        r'}\s*catch\s*\(e\)\s*\{\s*console\.error\(e\);\s*\}\s*(?!\s*})\s*window\.onclick',
        '} catch (e) { console.error(e); }\n        }\n\n        window.onclick',
        content
    )
    
    # Fix window.onclick missing closing brace
    # This matches window.onclick = function (event) { ... if (...) { ... } } without a closing }; before </script>
    
    regex_onclick = r'window\.onclick\s*=\s*function\s*\(event\)\s*\{(?:[^{}]|{(?:[^{}]|{[^{}]*})*})*\}\s*(?!\s*;?\s*})\s*</script>'
    # That regex is complex. Let's try simpler: find window.onclick, then find the last } before </script> and ensure it is closed.
    
    # Actually, let's just replace the whole window.onclick block with a correct one.
    
    onclick_replacement = '''window.onclick = function (event) {
            if (event.target.classList.contains('modal')) {
                closeProfileSettings();
            }
        };'''
    
    # Specific fix for history and analyze which have profileDropdown
    onclick_replacement_complex = '''window.onclick = function (event) {
            if (!event.target.closest('.profile-container')) {
                if (document.getElementById('profileDropdown')) {
                    document.getElementById('profileDropdown').classList.remove('show');
                }
            }
            if (event.target.classList.contains('modal')) {
                closeProfileSettings();
            }
        };'''

    if 'profileDropdown' in content:
        content = re.sub(r'window\.onclick\s*=\s*function\s*\(event\)\s*\{.*?\}\s*(?=</script>)', onclick_replacement_complex + '\n    ', content, flags=re.DOTALL)
    else:
        content = re.sub(r'window\.onclick\s*=\s*function\s*\(event\)\s*\{.*?\}\s*(?=</script>)', onclick_replacement + '\n    ', content, flags=re.DOTALL)

    # Double check if we still have the issue where window.onclick starts but never ends before </script>
    if 'window.onclick' in content and '};' not in content.split('window.onclick')[1].split('</script>')[0]:
        # Force close if needed - very blunt
        # But let's try to be precise.
        pass

    with open(fpath, 'w') as f:
        f.write(content)
print("Finished fixing syntax")
