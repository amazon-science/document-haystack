# Document Haystack Benchmark

This repository contains the inference and evaluation scripts for the paper “[Document Haystack: A Long Context Multimodal Image/Document Understanding Vision LLM Benchmark](https://arxiv.org/abs/2507.15882)”.

## 📑 Abstract Paper

The proliferation of multimodal Large Language Models has significantly advanced the ability to analyze and understand complex data inputs from different modalities. However, the processing of long documents remains under-explored, largely due to a lack of suitable benchmarks. To address this, we introduce Document Haystack, a comprehensive benchmark designed to evaluate the performance of Vision Language Models (VLMs) on long, visually complex documents. Document Haystack features documents ranging from 5 to 200 pages and strategically inserts pure text or multimodal text+image "needles" at various depths within the documents to challenge VLMs' retrieval capabilities. Comprising 400 document variants and a total of 8,250 questions, it is supported by an objective, automated evaluation framework. We detail the construction and characteristics of the Document Haystack dataset, present results from prominent VLMs and discuss potential research avenues in this area.

## 🎯 Benchmark Overview

### Dataset

The Document Haystack dataset can be found at [AmazonScience/document-haystack](https://huggingface.co/datasets/AmazonScience/document-haystack) on Hugging Face.

### Key Features
- **Document Formats**: Text, Image, PDF
- **Document Range**: 5-200 pages
- **Dataset Size**: 400 document variants
- **Question Pool**: 8,250 evaluation questions
- **Needle Types**:
  - Pure text
  - Multimodal (text + image)
- **Automated Evaluation Framework**

### Benchmark Structure
- Strategic needle placement at various document depths
- Three inference and evaluation settings:
  1. TextNeedlesFromParsedText
  2. TextNeedlesFromDocumentImages
  3. TextImagesNeedlesFromDocumentImages

## 📁 Project Structure

```
.
├── src/
│   ├── evaluation/           # Evaluation and analysis scripts
│   │   ├── aliases.txt                    # Alias definitions for TextImagesNeedlesFromDocumentImages evaluation
│   │   ├── depth_analysis_heatmap.py      # Generates heatmap visualizations
│   │   ├── full_set_evaluation_nova.sh    # Batch evaluation script
│   │   ├── print_average_scores.sh        # Computes average performance
│   │   └── single_doc_evaluation.py       # Single document evaluation
│   └── inference/           # Model inference scripts
│       ├── full_set_inference_nova.sh     # Batch inference script
│       └── single_doc_inference_nova.py   # Single document inference
```

## 🚀 Getting Started

### Prerequisites

#### Document Haystack Dataset

First, download the Document Haystack dataset. When running the scripts below, provide the path to your local Document Haystack dataset, or optionally to your S3 Document Haystack folder when running inference.

#### General Requirements
- Python 3.x
- Required Python packages for evaluation:
  - `matplotlib`
  - `numpy`
  - `seaborn`

#### For Default Implementation (using Amazon Bedrock)
- AWS Account with Bedrock access
- `boto3` package

> **Note**: The AWS account and Bedrock access are only required if you run the scripts as provided (which use the Nova Lite model via Amazon Bedrock). If you modify the scripts to use your own models or different APIs, these AWS-specific requirements are not needed. See the [Model Adaptation](#-model-adaptation) section for details on using different models.

### Installation

1. Clone the repository:
```bash
git clone $REPO_LINK
```

2. Install required dependencies:
```bash
pip install boto3 matplotlib numpy seaborn
```

## 📊 Usage

### Running Inference

```bash
./src/inference/full_set_inference_nova.sh \
    --setting TextNeedlesFromParsedText \
    --document-haystack-path /path/to/documents \
    --results-path /path/to/results \
    [--region-name aws-region] \
    [--bucket-owner aws-account-id] \
    [--temperature temperature-value] \
    [--topp topp-value] \
    [--topk topk-value]
```

Available settings:
- `TextNeedlesFromParsedText` (1)
- `TextNeedlesFromDocumentImages` (2)
- `TextImagesNeedlesFromDocumentImages` (3)

Optional arguments:
- `--region-name`: Required if running inference from an S3 folder and/or to configure the region of your boto client
- `--bucket-owner`: Required if running inference from an S3 folder; specifies the AWS account ID
- `--temperature`: Optional; temperature value for the model.
- `--topp`: Optional; top-p value for the model.
- `--topk`: Optional; top-k value for the model.

Note: The script supports inference from S3 folders. In this case, `--document-haystack-path` should point to the S3 document haystack folder (e.g., s3://my-bucket/document-haystack).

### Running Evaluation

```bash
./src/evaluation/full_set_evaluation_nova.sh \
    --setting TextNeedlesFromParsedText \
    --document-haystack-path /path/to/documents \
    --results-path /path/to/results
```

Available settings:
- `TextNeedlesFromParsedText` (1)
- `TextNeedlesFromDocumentImages` (2)
- `TextImagesNeedlesFromDocumentImages` (3)

### Generating Performance Reports

```bash
./src/evaluation/print_average_scores.sh  \
    --results-path /path/to/results
```

### Creating Depth Analysis Heatmap

```bash
python src/evaluation/depth_analysis_heatmap.py \
    --output /path/to/heatmap.png \
    --title "Custom Heatmap Title" \
    --results-path /path/to/results
```

## 🔄 Model Adaptation

To use a different model instead of Amazon Bedrock's Nova model, you'll need to:

1. Modify the `main()` function in `single_doc_inference_nova.py` to use your preferred API client instead of `boto3` and `bedrock-runtime`.
2. Adapt the `process_nova_request()` function to match your model's API requirements.
3. Ensure your modified implementation maintains the same output format and structure for compatibility with evaluation scripts.

#### Results Directory Structure
```
Results/
├── AIG/
│   ├── AIG_5Pages/
│   │   ├── results.txt         # Raw model outputs (see format below)
│   │   └── results_scores.txt  # Evaluation results
│   ├── AIG_10Pages/
│   └── ...
├── AmericanAirlines/
│   ├── AmericanAirlines_5Pages/
│   └── ...
└── ...
```

#### Single Document Output Format

Each document's inference results (results.txt) should follow this format:

```text
#1
Prompt: [Your prompt text here]
Output: [Model response here]

#2
Prompt: [Your prompt text here]
Output: [Model response here]
...
```

#### Key Requirements

- Maintain the exact question ID format (#1, #2, etc.)
- Include both "Prompt:" and "Output:" labels
- Preserve blank lines between entries
- Follow the Results directory structure exactly as shown
- Handle both text and image inputs according to your model's capabilities

## 📝 License

This project is licensed under the CC-BY-NC-4.0 License - see the LICENSE file for details.

## 📧 Contact

For any questions or concerns, please open an issue in the repository.

## 📚 Citation

If you use this work in any way, please cite:

```bibtex
@article{huybrechts2025document,
  title={Document Haystack: A Long Context Multimodal Image/Document Understanding Vision LLM Benchmark},
  author={Huybrechts, Goeric and Ronanki, Srikanth and Jayanthi, Sai Muralidhar and Fitzgerald, Jack and Veeravanallur, Srinivasan},
  journal={arXiv preprint arXiv:2507.15882},
  year={2025}
}
```

## 👥 Authors

Amazon AGI
- **Goeric Huybrechts**
- **Srikanth Ronanki**
- **Sai Muralidhar Jayanthi**
- **Jack Fitzgerald**
- **Srinivasan Veeravanallur**
