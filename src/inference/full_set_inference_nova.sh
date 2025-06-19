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
        --region-name)
            REGION_NAME="$2"
            shift 2
            ;;
        --bucket-owner)
            BUCKET_OWNER="$2"
            shift 2
            ;;
        --temperature)
            TEMPERATURE="$2"
            shift 2
            ;;
        --topp)
            TOPP="$2"
            shift 2
            ;;
        --topk)
            TOPK="$2"
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

# Prepare region parameter if provided
REGION_PARAM=""
if [ ! -z "$REGION_NAME" ]; then
    REGION_PARAM="--region-name $REGION_NAME"
fi

# Determine folder and additional parameters based on setting
case $SETTING in
    "TextNeedlesFromParsedText"|"1")
        FOLDER_TYPE="--text-folder"
        SUBFOLDER="Text_TextNeedles"
        ADDITIONAL_PARAMS=""
        if [ ! -z "$BUCKET_OWNER" ]; then
            ADDITIONAL_PARAMS="--bucket-owner $BUCKET_OWNER"
        fi
        ;;
    "TextNeedlesFromDocumentImages"|"2")
        FOLDER_TYPE="--image-folder"
        SUBFOLDER="Images_TextNeedles"
        ADDITIONAL_PARAMS=""
        if [ ! -z "$BUCKET_OWNER" ]; then
            ADDITIONAL_PARAMS="--bucket-owner $BUCKET_OWNER"
        fi
        ;;
    "TextImagesNeedlesFromDocumentImages"|"3")
        FOLDER_TYPE="--image-folder"
        SUBFOLDER="Images_TextImageNeedles"
        ADDITIONAL_PARAMS=""
        if [ ! -z "$BUCKET_OWNER" ]; then
            ADDITIONAL_PARAMS="--bucket-owner $BUCKET_OWNER"
        fi
        ;;
esac

# Prepare temperature, topp, and topk parameters if provided
TEMPERATURE_PARAM=""
TOPP_PARAM=""
TOPK_PARAM=""
if [ ! -z "$TEMPERATURE" ]; then
    TEMPERATURE_PARAM="--temperature $TEMPERATURE"
fi
if [ ! -z "$TOPP" ]; then
    TOPP_PARAM="--topp $TOPP"
fi
if [ ! -z "$TOPK" ]; then
    TOPK_PARAM="--topk $TOPK"
fi

# Outer loop for NumPages
for N in "${NumPages[@]}"; do
    # Inner loop for Benchmarks
    for Benchmark in "${Benchmarks[@]}"; do
        echo "Start processing ${Benchmark} with ${N} pages"
        mkdir -p "${RESULTS_PATH}/${Benchmark}/${Benchmark}_${N}Pages"

        python3 src/inference/single_doc_inference_nova.py \
            --prompts-file "${DOCUMENT_HAYSTACK_PATH}/${Benchmark}/${Benchmark}_${N}Pages/prompt_questions.txt" \
            ${FOLDER_TYPE} "${DOCUMENT_HAYSTACK_PATH}/${Benchmark}/${Benchmark}_${N}Pages/${SUBFOLDER}" \
            --output-file "${RESULTS_PATH}/${Benchmark}/${Benchmark}_${N}Pages/results.txt" \
            --model-id us.amazon.nova-lite-v1:0 \
            ${REGION_PARAM} \
            ${ADDITIONAL_PARAMS} \
            ${TEMPERATURE_PARAM} \
            ${TOPP_PARAM} \
            ${TOPK_PARAM}

        echo -e "\nCompleted processing ${Benchmark} with ${N} pages"
        echo -e "----------------------------------------\n"
    done
    echo "Completed processing all benchmarks with ${N} pages"
    echo -e "----------------------------------------\n"
done
echo "Completed full processing"
echo "----------------------------------------"
