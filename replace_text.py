import os

TEMPLATES_DIR = '/home/sureshkumar-s/Documents/ECG-Digitiser/templates'

for filename in os.listdir(TEMPLATES_DIR):
    if filename.endswith('.html'):
        filepath = os.path.join(TEMPLATES_DIR, filename)
        with open(filepath, 'r') as f:
            content = f.read()

        # Replace 'SMARTECG AI' with 'Clinical AI'
        content = content.replace('SMARTECG AI', 'Clinical AI')
        # Also handle SmartECG AI
        content = content.replace('SmartECG AI', 'Clinical AI')

        with open(filepath, 'w') as f:
            f.write(content)
print("Done")
