import argparse
from math import ceil, floor
import re

def parse_arguments():
    parser = argparse.ArgumentParser(description="Evaluate predictions against groundtruth.")
    parser.add_argument("--input-pred", required=True, help="Input file containing predictions")
    parser.add_argument("--input-groundtruth", required=True, help="Input file containing groundtruths")
    parser.add_argument("--output-file", required=True, help="Output file to summarize the score")
    parser.add_argument("--depth-analysis", action="store_true", help="Perform depth analysis of accuracy")
    parser.add_argument("--alias-file", help="Optional alias file")
    parser.add_argument("--num-buckets", type=int, default=10, help="Number of buckets for depth analysis")
    parser.add_argument("--needles-info-file", help="CSV file containing needle page information")
    parser.add_argument("--n-pages", type=int, help="Total number of pages")
    return parser.parse_args()

def extract_quoted_substring(text):
    pattern = r'"(.*?)"'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    else:
        return None

def parse_needles_info(file_path):
    """Parse the needles info CSV file and return the page numbers."""
    pages = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            parts = line.strip().split(',')
            page = int(parts[1])
            pages.append(page)
    return pages

def parse_alias_file(file_path):
    """Parse the alias file and return a dictionary of aliases."""
    aliases = {}

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            parts = line.split('"')
            if len(parts) > 1:
                key = parts[1]
                values = [v.strip() for v in parts[2:] if v.strip()]
                aliases[key.lower()] = values

    return aliases

def get_aliases(needle, aliases):
    """Get aliases for the given needle."""
    return aliases.get(needle.lower(), [])

def check_answer(needle, LLM_result, aliases):
    """Checks if the needle or its aliases are present in the LLM_result."""
    needle = needle.lower()
    LLM_result = LLM_result.lower()

    if needle in LLM_result:
        return 1

    aliases_list = get_aliases(needle, aliases)
    for alias in aliases_list:
        if alias in LLM_result:
            return 1

    return 0

def parse_input_pred_file(file_path):
    """Parse the input prediction file and return a list of tuples (prompt_id, prompt, output)."""
    entries = []
    current_entry = []

    PROMPT_TEXT = "Prompt: "
    OUTPUT_TEXT = "Output: "

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if line.startswith('#'):
                if current_entry:
                    entries.append(tuple(current_entry))
                    current_entry = []
                prompt_id = line[1:]
                current_entry.append(int(prompt_id))
            elif line.startswith(PROMPT_TEXT):
                prompt = line[len(PROMPT_TEXT):].strip()
                current_entry.append(prompt)
            elif line.startswith(OUTPUT_TEXT):
                output = line[len(OUTPUT_TEXT):].strip()
                current_entry.append(output)
            elif line != "":
                # Multi-line LLM output
                current_entry[-1] += " " + line.strip()

        if current_entry:
            entries.append(tuple(current_entry))

    return entries

def parse_input_groundtruth_file(file_path):
    """Parse the input groundtruth file and return the list of results."""
    results = []

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            result = extract_quoted_substring(line)
            results.append(result)

    return results

def calculate_bucket_accuracy(scores, num_buckets=10, needles_info=None, n_pages=None):
    """
    Calculate accuracy for each bucket of scores.
    If needles_info and n_pages are provided, buckets are determined by page numbers.
    """
    if needles_info is None or n_pages is None:
        # Original bucket calculation based on position in the list
        bucket_accuracies = []
        bucket_size = ceil(len(scores) / num_buckets)

        for i in range(num_buckets):
            start_idx = i * bucket_size
            end_idx = min((i + 1) * bucket_size, len(scores))
            bucket_scores = scores[start_idx:end_idx]
            if bucket_scores:
                accuracy = sum(bucket_scores) / len(bucket_scores)
                bucket_accuracies.append(accuracy)
            else:
                bucket_accuracies.append("No scores")
    else:
        # Calculate buckets based on page numbers
        bucket_scores = [[] for _ in range(num_buckets)]
        pages_per_bucket = n_pages / num_buckets

        # Pair scores with their corresponding pages and assign to buckets
        for score, page in zip(scores, needles_info):
            bucket_idx = min(floor((page - 1) / pages_per_bucket), num_buckets - 1)
            bucket_scores[bucket_idx].append(score)

        # Calculate average accuracy for each bucket
        bucket_accuracies = [
            sum(bucket)/len(bucket) if bucket else "No scores"
            for bucket in bucket_scores
        ]

    # Assert that difference between any two bucket sizes is at most 1
    bucket_sizes = [len(bucket) for bucket in bucket_scores]
    assert sum(bucket_sizes) == len(scores)
    assert max(bucket_sizes) - min(bucket_sizes) <= 1, \
        f"Bucket size difference is too large. Bucket sizes: {bucket_sizes}"

    return bucket_accuracies

def main():
    args = parse_arguments()

    # Validate needles_info_file and n_pages
    if (args.needles_info_file is None) != (args.n_pages is None):
        raise ValueError("Both needles_info_file and n_pages must be provided together")

    # Parse input files
    pred_entries = parse_input_pred_file(args.input_pred)
    groundtruth_entries = parse_input_groundtruth_file(args.input_groundtruth)

    # Parse needles info file if provided
    needles_info = None
    if args.needles_info_file:
        needles_info = parse_needles_info(args.needles_info_file)
        if len(needles_info) != len(pred_entries):
            raise ValueError("Number of entries in needles info file doesn't match predictions")

    # Parse alias file if provided
    aliases = {}
    if args.alias_file:
        aliases = parse_alias_file(args.alias_file)

    # Check if the number of entries match
    if len(pred_entries) != len(groundtruth_entries):
        raise ValueError("The number of entries in the input files does not match.")

    # Evaluate and write results to output file
    scores = []
    with open(args.output_file, 'w', encoding='utf-8') as out_file:
        for i, (pred_id, pred_prompt, pred_output) in enumerate(pred_entries):
            groundtruth_result = groundtruth_entries[i]

            if i + 1 != pred_id:
                raise ValueError(f"Prompt IDs do not match for entry {i+1}")

            score = check_answer(groundtruth_result, pred_output, aliases)
            out_file.write(f"{i+1}. {pred_prompt} {score}\n")
            scores.append(score)

        # If depth analysis is requested, calculate and write bucket accuracies
        if args.depth_analysis:
            bucket_accuracies = calculate_bucket_accuracy(
                scores, args.num_buckets, needles_info, args.n_pages)
            out_file.write("\nDepth Analysis\n")
            for i, accuracy in enumerate(bucket_accuracies):
                start_percent = max(round(i * (100 / args.num_buckets)), 0)
                end_percent = min(round((i + 1) * (100 / args.num_buckets)), 100)
                accuracy = f"{accuracy:.2f}" if isinstance(accuracy, float) else str(accuracy)
                out_file.write(f"{start_percent}-{end_percent}% accuracy: {accuracy}\n")

        # Calculate and write the average accuracy
        average_accuracy = sum(scores) / len(scores)
        out_file.write(f"\nAverage accuracy: {average_accuracy:.2f}\n")

if __name__ == "__main__":
    main()
