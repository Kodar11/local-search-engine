from collections import defaultdict
import re
import os
import math

from pypdf import PdfReader
from docx import Document
from bs4 import BeautifulSoup



class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_word = False


class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        node = self.root

        for ch in word:
            if ch not in node.children:
                node.children[ch] = TrieNode()

            node = node.children[ch]

        node.is_word = True

    def starts_with(self, prefix):
        node = self.root

        for ch in prefix:
            if ch not in node.children:
                return []

            node = node.children[ch]

        results = []

        def dfs(curr_node, current_word):
            if curr_node.is_word:
                results.append(current_word)

            for ch, child in curr_node.children.items():
                dfs(child, current_word + ch)

        dfs(node, prefix)

        return results


def levenshtein(a, b):
    rows = len(a) + 1
    cols = len(b) + 1

    dp = [[0] * cols for _ in range(rows)]

    for i in range(rows):
        dp[i][0] = i

    for j in range(cols):
        dp[0][j] = j

    for i in range(1, rows):
        for j in range(1, cols):

            if a[i - 1] == b[j - 1]:
                cost = 0
            else:
                cost = 1

            dp[i][j] = min(
                dp[i - 1][j] + 1,      # delete
                dp[i][j - 1] + 1,      # insert
                dp[i - 1][j - 1] + cost # replace
            )

    return dp[-1][-1]

def extract_text(filename):
    ext = os.path.splitext(filename)[1].lower()

    try:
        if ext in [".txt", ".md"]:
            with open(
                filename,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as f:
                return f.read()

        elif ext == ".pdf":
            reader = PdfReader(filename)

            text = ""

            for page in reader.pages:
                text += page.extract_text() or ""

            return text

        elif ext == ".docx":
            doc = Document(filename)

            return "\n".join(
                p.text
                for p in doc.paragraphs
            )

        elif ext == ".html":
            with open(
                filename,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as f:

                soup = BeautifulSoup(
                    f.read(),
                    "html.parser"
                )

                return soup.get_text()

    except Exception as e:
        print(
            f"Error reading {filename}: {e}"
        )

    return ""



SUPPORTED_EXTENSIONS = (
    ".txt",
    ".md",
    ".pdf",
    ".docx",
    ".html"
)

files = [
    f for f in os.listdir()
    if f.lower().endswith(
        SUPPORTED_EXTENSIONS
    )
]

if not files:
    print("No supported files found")
    raise SystemExit(0)

total_docs = len(files)
doc_lengths = {}
documents = {}

inverted_index = defaultdict(lambda: defaultdict(list))
trie = Trie()


# Build index
for filename in files:
    text = extract_text(filename)
    documents[filename] = text

    words = re.findall(
        r"[a-zA-Z]+(?:'[a-zA-Z]+)?",
        text.lower()
    )       
    doc_lengths[filename] = len(words)

    for position, word in enumerate(words):
        inverted_index[word][filename].append(position)

    for word in set(words):
        trie.insert(word)

avg_doc_length = (
    sum(doc_lengths.values()) /
    len(doc_lengths)
)

prefix = input("Autocomplete: ").lower()

print(
    trie.starts_with(prefix)[:10]
) 

query = input("Enter search query: ").lower().split()

expanded_query = []

for word in query:

    if word in inverted_index:
        expanded_query.append(word)

    else:
        prefix_matches = trie.starts_with(word)

        if prefix_matches:
            expanded_query.extend(prefix_matches)
        else:

            best_word = None
            best_distance = float("inf")

            for indexed_word in inverted_index:

                distance = levenshtein(
                    word,
                    indexed_word
                )

                if distance < best_distance:
                    best_distance = distance
                    best_word = indexed_word

            if best_distance <= 2:
                expanded_query.append(best_word)
            else:
                expanded_query.append(word)

query = expanded_query

results = []

for filename in files:
    matched_terms = 0
    score = 0

    # Partial matching
    for word in query:
        if filename in inverted_index[word]:

            matched_terms += 1

            tf = len(inverted_index[word][filename])

            docs_with_word = len(inverted_index[word])

            idf = math.log(
                            (total_docs - docs_with_word + 0.5) /
                            (docs_with_word + 0.5) + 1
                        )

            k1 = 1.5
            b = 0.75

            doc_length = doc_lengths[filename]

            bm25 = idf * (
                tf * (k1 + 1)
            ) / (
                tf +
                k1 * (
                    1 - b +
                    b * (doc_length / avg_doc_length)
                )
            )

            score += bm25

    if matched_terms == 0:
        continue

    # Phrase bonus
    phrase_found = False

    if len(query) > 1:
        first_word = query[0]

        if filename in inverted_index[first_word]:
            first_word_positions = inverted_index[first_word][filename]

            for start_pos in first_word_positions:
                match = True

                for i in range(1, len(query)):
                    word = query[i]

                    if filename not in inverted_index[word]:
                        match = False
                        break

                    positions = inverted_index[word][filename]

                    if start_pos + i not in positions:
                        match = False
                        break

                if match:
                    phrase_found = True
                    break

    if phrase_found:
        score += 100

    results.append(
        (
            score,
            matched_terms,
            filename,
            phrase_found
        )
    )

results.sort(reverse=True)

if results:
    print("\nResults:\n")

    for score, matched_terms, filename, phrase_found in results:
        print(f"{filename} | score={score:.2f} | "
            f"matched={matched_terms}/{len(query)} | "
            f"phrase_match={phrase_found}")

        content = documents[filename]

        snippet = ""

        for word in query:

            pos = content.lower().find(word.lower())

            if pos != -1:

                start = max(0, pos - 50)
                end = min(len(content), pos + 50)

                snippet = content[start:end]

                break

        if snippet:
            print(f"Snippet: ...{snippet}...")

        print()
    
else:
    print("No matching files found")