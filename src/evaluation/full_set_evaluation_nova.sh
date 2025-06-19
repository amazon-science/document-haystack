#!/bin/bash

# Define the list of Benchmarks
Benchmarks=(
    AIG AmericanAirlines APA BankOfMontreal Barclays
    BlackRock BNYMellon CapitalOne CitiGroup Cofinimmo
    CVS DWS Entain GoldmanSachs HSBC
    JPMorgan Kroger NewRiver PNC Reach
    Sagicor United UPS Vesuvius WoltersKluwer
)

# Define the list of NumPages values
NumPages=(5 10 25 50 75 100 150 200)

# Function to validate setting
validate_setting() {
    local setting=$1
    case $setting in
        "TextNeedlesFromParsedText"|"1") return 0 ;;
        "TextNeedlesFromDocumentImages"|"2") return 0 ;;
        "TextImagesNeedlesFromDocumentImages"|"3") return 0 ;;
        *) echo "Invalid setting. Must be one of: TextNeedlesFromParsedText/1, TextNeedlesFromDocumentImages/2, or TextImagesNeedlesFromDocumentImages/3" >&2; exit 1 ;;
    esac
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --setting)
            SETTING="$2"
            validate_setting "$SETTING"
            shift 2
            ;;
        --document-haystack-path)
            DOCUMENT_HAYSTACK_PATH="$2"
            shift 2
            ;;
        --results-path)
            RESULTS_PATH="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1" >&2
            exit 1
            ;;
    esac
done

# Check if setting is provided
if [ -z "$SETTING" ]; then
    echo "Error: --setting argument is required" >&2
    exit 1
fi

# Set default paths if not provided
DOCUMENT_HAYSTACK_PATH=${DOCUMENT_HAYSTACK_PATH:-"DocumentHaystack"}
RESULTS_PATH=${RESULTS_PATH:-"Results"}

# Determine if alias file should be included based on setting
ALIAS_PARAM=""
if [ "$SETTING" = "TextImagesNeedlesFromDocumentImages" ] || [ "$SETTING" = "3" ]; then
    ALIAS_PARAM="--alias-file src/evaluation/aliases.txt"
fi

# Outer loop for NumPages
for N in "${NumPages[@]}"; do
    num_buckets=$((N < 10 ? N : 10))

    # Inner loop for Benchmarks
    for Benchmark in "${Benchmarks[@]}"; do
        python3 src/evaluation/single_doc_evaluation_nova.py \
            --input-pred "${RESULTS_PATH}/${Benchmark}/${Benchmark}_${N}Pages/results.txt" \
            --input-groundtruth "${DOCUMENT_HAYSTACK_PATH}/${Benchmark}/${Benchmark}_${N}Pages/needles.csv" \
            --output-file "${RESULTS_PATH}/${Benchmark}/${Benchmark}_${N}Pages/results_scores.txt" \
            --depth-analysis \
            ${ALIAS_PARAM} \
            --num-buckets $num_buckets \
            --needles-info-file "${DOCUMENT_HAYSTACK_PATH}/${Benchmark}/${Benchmark}_${N}Pages/needles_info.csv" \
            --n-pages $N
    done
    echo "Completed evaluation of all benchmarks with ${N} pages"
    echo -e "----------------------------------------\n"
done
echo "Completed full evaluation"
echo "----------------------------------------"
