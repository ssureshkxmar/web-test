import os
import glob
import re

TEMPLATES_DIR = '/home/sureshkumar-s/Documents/ECG-Digitiser/templates'
files = glob.glob(os.path.join(TEMPLATES_DIR, '*.html'))

font_awesome = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">\n    <script src="https://accounts.google.com/gsi/client"'

for fpath in files:
    with open(fpath, 'r') as f:
        content = f.read()
    
    # 1. Add font_awesome before gsi/client
    if 'font-awesome' not in content:
        content = content.replace('<script src="https://accounts.google.com/gsi/client"', font_awesome)
    
    # 2. Add font-awesome just in case it's another file without gsi/client
    if 'font-awesome' not in content and '</title>' in content:
        content = content.replace('</title>', '</title>\n    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">')

    # 3. Change "SMARTECG AI" to "Clinical AI"
    content = content.replace('SMARTECG AI', 'Clinical AI')
    content = content.replace('SmartECG AI', 'Clinical AI')

    # 4. Make background more Github-like
    content = re.sub(r'--bg-dark: #[0-9a-fA-F]+;', '--bg-dark: #0d1117;', content)
    content = re.sub(r'--card-dark: #[0-9a-fA-F]+;', '--card-dark: #161b22;', content)
    content = re.sub(r'--border-color: rgba\([^)]+\);', '--border-color: rgba(255, 255, 255, 0.1);', content)

    # 5. Fix ambient-bg for GitHub glow
    glow_css = '''
            background: 
                radial-gradient(circle at 50% 120%, rgba(121, 40, 202, 0.4) 0%, transparent 60%);
            animation: pulse-glow 8s ease-in-out infinite alternate;
        }

        @keyframes pulse-glow {
            0% { transform: scale(1); opacity: 0.8; }
            100% { transform: scale(1.1); opacity: 1; }
        }'''
    
    if 'radial-gradient(circle at 20% 20%' in content:
        # replace the background section of .ambient-bg
        content = re.sub(r'background:\s*radial-gradient\(circle at 20% 20%.*?transparent 50%\);', glow_css, content, flags=re.DOTALL)

    with open(fpath, 'w') as f:
        f.write(content)
print("Updated all templates")
