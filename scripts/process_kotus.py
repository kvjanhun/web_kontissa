import subprocess, os

url = 'https://kaino.kotus.fi/lataa/nykysuomensanalista2024.txt'
subprocess.run(['curl', '-A', 'Mozilla/5.0', '-L', url, '-o', '/tmp/kotus_raw.txt'], check=True)

ALLOWED = set('abcdefghijklmnopqrstuvwxyzäö')
words = set()
with open('/tmp/kotus_raw.txt', encoding='utf-8') as f:
    for line in f:
        word = line.split('\t')[0].strip()
        if len(word) >= 4 and word == word.lower() and all(c in ALLOWED for c in word):
            words.add(word)

os.makedirs('app/wordlists', exist_ok=True)
with open('app/wordlists/kotus_words.txt', 'w', encoding='utf-8') as f:
    for w in sorted(words):
        f.write(w + '\n')
print(f"Saved {len(words)} words")
