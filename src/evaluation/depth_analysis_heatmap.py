import argparse
import os

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import seaborn as sns

def parse_args():
    parser = argparse.ArgumentParser(description='Generate heatmap of average accuracy distribution.')
    parser.add_argument('--average', action='store_false', help='Include an average column in the heatmap')
    parser.add_argument('--title', type=str, default='Average Accuracy Distribution Across Context Lengths',
                        help='Custom title for the heatmap')
    parser.add_argument('--output', type=str, required=True,
                        help='Path to save the heatmap (e.g., "output/heatmap.png")')
    parser.add_argument('--results-path', type=str, default='Results',
                        help='Path to the results directory (default: Results)')
    return parser.parse_args()

def create_heatmap(result_matrix, args, x_labels, accuracy_ranges):
    plt.figure(figsize=(8, 6))

    custom_cmap = sns.color_palette("RdYlGn", as_cmap=True)

    heatmap = sns.heatmap(result_matrix,
                          square=False,
                          annot=True,
                          fmt='.0%',
                          cmap=custom_cmap,
                          xticklabels=x_labels,
                          yticklabels=accuracy_ranges,
                          vmin=0,
                          vmax=1,
                          linewidths=4,
                          linecolor='white',
                          annot_kws={'color': 'black', 'size': 10},
                          cbar_kws={'format': PercentFormatter(1.0),
                                  'ticks': [0, 0.5, 1.0],
                                  'shrink': 0.8})

    ax = plt.gca()
    ax.tick_params(left=False, bottom=False)

    for t in heatmap.texts:
        current_pos = t.get_position()
        t.set_position((current_pos[0], current_pos[1]))

        if args.average and current_pos[0] == result_matrix.shape[1] - 0.5:
            t.set_weight('bold')

    if args.average:
        ax.get_xticklabels()[-1].set_weight('bold')
        ax.axvline(x=result_matrix.shape[1]-1, color='black', linestyle='--', linewidth=2)

    plt.xlabel('# Pages', labelpad=10)
    plt.ylabel('Depth', labelpad=10)
    plt.xticks(rotation=0)
    plt.yticks(rotation=0)
    plt.tight_layout()

def process_benchmarks(results_path):
    benchmarks = ['AIG', 'AmericanAirlines', 'APA', 'BankOfMontreal', 'Barclays',
                  'BlackRock', 'BNYMellon', 'CapitalOne', 'CitiGroup', 'Cofinimmo',
                  'CVS', 'DWS', 'Entain', 'GoldmanSachs', 'HSBC', 'JPMorgan',
                  'Kroger', 'NewRiver', 'PNC', 'Reach', 'Sagicor', 'United',
                  'UPS', 'Vesuvius', 'WoltersKluwer']

    page_counts = [25, 50, 75, 100, 150, 200]
    accuracy_ranges = ['0-10%', '10-20%', '20-30%', '30-40%', '40-50%',
                      '50-60%', '60-70%', '70-80%', '80-90%', '90-100%']

    result_matrix = np.zeros((len(accuracy_ranges), len(page_counts)))

    for benchmark in benchmarks:
        for i, pages in enumerate(page_counts):
            filepath = os.path.join(results_path, benchmark,
                                  f"{benchmark}_{pages}Pages/results_scores.txt")

            try:
                with open(filepath, 'r') as file:
                    lines = file.readlines()
                    for idx, line in enumerate(lines):
                        if line.strip() == "Depth Analysis":
                            depth_start = idx + 1
                            break

                    for j in range(10):
                        line = lines[depth_start + j].strip()
                        value = float(line.split(': ')[1])
                        result_matrix[j][i] += value

            except FileNotFoundError:
                print(f"Warning: File not found - {filepath}")
                continue
            except Exception as e:
                print(f"Error processing {filepath}: {str(e)}")
                continue

    result_matrix = result_matrix / len(benchmarks)
    return result_matrix, page_counts, accuracy_ranges

def main():
    args = parse_args()

    # Process benchmarks and get result matrix
    result_matrix, page_counts, accuracy_ranges = process_benchmarks(args.results_path)

    if args.average:
        average_column = result_matrix.mean(axis=1).reshape(-1, 1)
        result_matrix = np.hstack((result_matrix, average_column))

    # Prepare x-axis labels
    x_labels = [str(count) for count in page_counts]
    if args.average:
        x_labels.append('Average')

    # Create and save heatmap
    create_heatmap(result_matrix, args, x_labels, accuracy_ranges)

    # Save the figure
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    plt.savefig(args.output, bbox_inches='tight', dpi=300)
    plt.close()

if __name__ == "__main__":
    main()
