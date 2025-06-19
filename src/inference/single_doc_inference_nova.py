import argparse
import base64
import json
import mimetypes
import os
import sys
import time

import boto3
import botocore
from botocore.config import Config

IMAGE_EXTENSION = '.jpg'
TEXT_EXTENSION = '.txt'
INFERENCE_ERROR = "UNEXPECTED INFERENCE ERROR"
MAX_RETRIES = 5

def parse_arguments():
    parser = argparse.ArgumentParser(description='Process images and prompts using Bedrock Nova API')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--image-folder', help='Path to the folder containing images')
    group.add_argument('--text-folder', help='Path to the folder containing text files')
    parser.add_argument('--bucket-owner', default=None, help='S3 bucket owner ID (required when using a S3 image folder)')
    parser.add_argument('--prompts-file', required=True, help='Path to the text file containing prompts')
    parser.add_argument('--output-file', required=True, help='Path to the output file')
    parser.add_argument('--model-id', default="us.amazon.nova-lite-v1:0",
                        help='Model ID to use (default: us.amazon.nova-lite-v1:0)')
    parser.add_argument('--read-timeout', type=int, default=60,
                        help='Read timeout in seconds (default: 60)')
    parser.add_argument('--connect-timeout', type=int, default=60,
                        help='Connect timeout in seconds (default: 60)')
    parser.add_argument('--region-name', default="us-east-2",
                        help='AWS region name (default: us-east-2)')
    parser.add_argument('--temperature', type=float, default=1.0, help='Temperature for the model (default: 1.0)')
    parser.add_argument('--topp', type=float, default=1.0, help='Top-p value for the model (default: 1.0)')
    parser.add_argument('--topk', type=int, default=1, help='Top-k value for the model (default: 1)')
    return parser.parse_args()

def custom_sort(filename, is_image=True):
    """Custom sorting function for filenames."""
    extension = IMAGE_EXTENSION if is_image else TEXT_EXTENSION
    try:
        return int(filename.lower().split('_')[-1].split(extension)[0])
    except (ValueError, IndexError):
        file_type = "image" if is_image else "text"
        print(f"Error: Trying to sort a file which is not a {file_type} file.")
        sys.exit(1)

def get_content_from_local_folder(folder_path, is_image=True):
    """Get content (images or text) from a folder in custom sorted order."""
    try:
        extension = IMAGE_EXTENSION if is_image else TEXT_EXTENSION
        # Get all files with the specified extension in the directory
        files = [f for f in os.listdir(folder_path)
                if f.lower().endswith(extension) and not f.startswith('.')]

        # Sort using the custom sort function
        sorted_files = sorted(files, key=lambda x: custom_sort(x, is_image=is_image))

        if not sorted_files:
            file_type = "images" if is_image else "text files"
            print(f"Error: No valid {file_type} found in {folder_path}")
            sys.exit(1)

        if is_image:
            # Convert to full paths for images
            return [os.path.join(folder_path, filename) for filename in sorted_files]
        else:
            # Read and concatenate text from all files
            combined_text = ""
            for filename in sorted_files:
                file_path = os.path.join(folder_path, filename)
                try:
                    with open(file_path, 'r') as f:
                        combined_text += f.read().strip()
                except Exception as e:
                    print(f"Error reading file {filename}: {str(e)}")
                    sys.exit(1)

            if not combined_text:
                print(f"Error: No valid text content found in {folder_path}")
                sys.exit(1)

            return combined_text.strip()

    except Exception as e:
        file_type = "images" if is_image else "text"
        print(f"Error reading {file_type} from folder: {str(e)}")
        sys.exit(1)

def get_content_from_s3_folder(s3_folder, is_image=True):
    """Get all files (images or text) from an S3 folder in custom sorted order."""
    try:
        # Parse S3 URI
        if not s3_folder.startswith('s3://'):
            print(f"Error: Invalid S3 URI format. Must start with 's3://'")
            sys.exit(1)

        s3_parts = s3_folder.replace('s3://', '').split('/')
        bucket_name = s3_parts[0]
        # Join the remaining parts to get the prefix, ensure it ends with '/'
        prefix = '/'.join(s3_parts[1:])
        if prefix and not prefix.endswith('/'):
            prefix += '/'

        # Initialize S3 client
        s3_client = boto3.client('s3')

        # List objects in the S3 folder
        paginator = s3_client.get_paginator('list_objects_v2')
        files = []
        extension = IMAGE_EXTENSION if is_image else TEXT_EXTENSION

        try:
            for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        # Get just the filename from the full path
                        filename = os.path.basename(obj['Key'])
                        # Check if it's the correct file type and not hidden
                        if filename.lower().endswith(extension) and not filename.startswith('.'):
                            files.append(obj['Key'])
        except botocore.exceptions.ClientError as e:
            print(f"Error accessing S3: {str(e)}")
            sys.exit(1)

        if not files:
            file_type = "images" if is_image else "text files"
            print(f"Error: No valid {file_type} found in {s3_folder}")
            sys.exit(1)

        # Sort using the custom sort function
        sorted_files = sorted(files, key=lambda x: custom_sort(os.path.basename(x), is_image=is_image))

        if is_image:
            # Return full S3 URIs for images
            return [f"s3://{bucket_name}/{path}" for path in sorted_files]
        else:
            # Read and concatenate text from all files
            combined_text = ""
            for file_key in sorted_files:
                try:
                    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
                    file_content = response['Body'].read().decode('utf-8')
                    combined_text += file_content.strip()
                except botocore.exceptions.ClientError as e:
                    print(f"Error reading file {file_key} from S3: {str(e)}")
                    sys.exit(1)

            if not combined_text:
                print(f"Error: No valid text content found in {s3_folder}")
                sys.exit(1)

            return combined_text.strip()

    except Exception as e:
        file_type = "images" if is_image else "text"
        print(f"Error reading {file_type} from S3 folder: {str(e)}")
        sys.exit(1)

def read_prompts(prompts_file):
    """Read prompts from either a local file or S3 location."""
    try:
        if prompts_file.startswith('s3://'):
            # Parse S3 URI
            s3_parts = prompts_file.replace('s3://', '').split('/')
            bucket_name = s3_parts[0]
            key = '/'.join(s3_parts[1:])

            # Initialize S3 client
            s3_client = boto3.client('s3')

            try:
                # Get the object from S3
                response = s3_client.get_object(Bucket=bucket_name, Key=key)
                # Read the content and decode it
                content = response['Body'].read().decode('utf-8')
                # Split into lines, remove empty lines and whitespace
                prompts = [line.strip() for line in content.splitlines() if line.strip()]
            except botocore.exceptions.ClientError as e:
                print(f"Error accessing S3 file {prompts_file}: {str(e)}")
                sys.exit(1)
        else:
            # Read from local file
            with open(prompts_file, 'r') as f:
                # Read prompts and remove empty lines and leading/trailing whitespace
                prompts = [line.strip() for line in f.readlines() if line.strip()]

        if not prompts:
            print(f"Error: No valid prompts found in {prompts_file}")
            sys.exit(1)

        return prompts

    except FileNotFoundError:
        print(f"Error: Could not find prompts file at {prompts_file}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading prompts file: {str(e)}")
        sys.exit(1)

def process_nova_request(
        client,
        content,
        prompt_question,
        model_id,
        with_images=True,
        is_s3=False,
        bucket_owner=None,
        temperature=1.0,
        topp=1.0,
        topk=1,
):
    message_list = [
        {
            "role": "user",
            "content": []
        }
    ]

    if with_images:
        # Process images
        for img_path in content:
            mime_type, _ = mimetypes.guess_type(img_path)
            if mime_type is None:
                mime_type = 'image/jpg'

            if is_s3:
                message_list[0]["content"].append({
                    "image": {
                        "format": mime_type.split('/')[-1],
                        "source": {
                            "s3Location": {
                                "uri": img_path,
                                "bucketOwner": bucket_owner
                            }
                        }
                    }
                })
            else:
                with open(img_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                message_list[0]["content"].append({
                    "image": {
                        "format": mime_type.split('/')[-1],
                        "source": {
                            "bytes": encoded_string
                        }
                    }
                })
            full_prompt = f"{content}\n{prompt_question}"

        message_list[0]["content"].append({"text": prompt_question})
    else:
        # Prepend text content to prompt
        full_prompt = f"{content}\n{prompt_question}"
        message_list[0]["content"].append({"text": full_prompt})

    inference_config = {"temperature": temperature, "topP": topp, "topK": topk}
    native_request = {
        "schemaVersion": "messages-v1",
        "messages": message_list,
        "inferenceConfig": inference_config,
    }

    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            response = client.invoke_model(
                modelId=model_id,
                body=json.dumps(native_request)
            )
            model_response = json.loads(response["body"].read())
            return model_response["output"]["message"]["content"][0]["text"]
        except Exception as e:
            retry_count += 1
            print(f"Try {retry_count}/{MAX_RETRIES}, unexpected inference error: {str(e)}")
            if retry_count == MAX_RETRIES:
                print(f"Failed prompt \"{prompt_question}\" due to API error")
                return INFERENCE_ERROR

    print(f"Failed prompt \"{prompt_question}\" due to API error")
    return INFERENCE_ERROR

def main():
    args = parse_arguments()

    # Set up boto3 Bedrock client
    boto_config = Config(
        region_name=args.region_name,
        read_timeout=args.read_timeout,
        connect_timeout=args.connect_timeout
    )
    client = boto3.client("bedrock-runtime", config=boto_config)

    # Get content based on input type
    if args.image_folder:
        with_images = True
        if args.image_folder.startswith('s3://'):
            content = get_content_from_s3_folder(args.image_folder, is_image=True)
            is_s3 = True
        else:
            content = get_content_from_local_folder(args.image_folder, is_image=True)
            is_s3 = False
    else:  # text folder
        with_images = False
        if args.text_folder.startswith('s3://'):
            content = get_content_from_s3_folder(args.text_folder, is_image=False)
            is_s3 = True
        else:
            content = get_content_from_local_folder(args.text_folder, is_image=False)
            is_s3 = False

    # Read prompts from file
    prompts = read_prompts(args.prompts_file)

    with open(args.output_file, 'w') as out:
        # Process each prompt
        for i, prompt in enumerate(prompts):
            print(f"\nProcessing prompt {i+1}/{len(prompts)}: {prompt}")

            # Process the request
            output = process_nova_request(
                client,
                content,
                prompt,
                args.model_id,
                with_images,
                is_s3,
                args.bucket_owner,
                args.temperature,
                args.topp,
                args.topk
            )

            # Write to output file
            try:
                out.write(f"#{i+1}\nPrompt: {prompt}\nOutput: {output}\n\n")
            except IOError as e:
                print(f"Error writing to output file: {str(e)}")
                sys.exit(1)

            print(f"Output: {output}")

if __name__ == "__main__":
    main()
