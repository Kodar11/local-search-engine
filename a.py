from collections import defaultdict
import re
import os
import math

files = [f for f in os.listdir() if f.endswith(".txt")]
total_docs = len(files)
doc_lengths = {}


inverted_index = defaultdict(lambda: defaultdict(list))

# Build index
for filename in files:
    with open(filename, "r", encoding="utf-8") as file:
        words = re.findall(
            r"[a-zA-Z]+(?:'[a-zA-Z]+)?",
            file.read().lower()
        )
        doc_lengths[filename] = len(words)

        for position, word in enumerate(words):
            inverted_index[word][filename].append(position)

avg_doc_length = (
    sum(doc_lengths.values()) /
    len(doc_lengths)
)


query = input("Enter search query: ").lower().split()

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
        print(
            f"{filename} | score={score} | "
            f"matched={matched_terms}/{len(query)} | "
            f"phrase_match={phrase_found}"
        )
else:
    print("No matching files found")