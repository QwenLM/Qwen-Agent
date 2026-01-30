"""
Convert agent reports to structured JSON format for evaluation

This module uses an LLM to parse the agent's natural language travel plans
and convert them into structured JSON format required by the evaluation module.
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import openai

# Add parent directory to path to import prompts and call_llm utilities
sys.path.insert(0, str(Path(__file__).parent.parent / 'agent'))
from prompts import get_format_convert_prompt
from call_llm import load_model_config, create_client


# Load environment variables from .env file
def _load_env_from_dotenv() -> None:
    """
    Load environment variables from .env file if exists
    
    Searches for .env in the following order:
    1. Domain directory (travelplanning/)
    2. Project root (parent of domain)
    """
    try:
        # Try domain directory first
        domain_root = Path(__file__).parent.parent
        domain_dotenv = domain_root / '.env'
        
        # Try project root
        project_root = domain_root.parent
        project_dotenv = project_root / '.env'
        
        # Use project root .env if it exists, otherwise domain .env
        dotenv_path = project_dotenv if project_dotenv.exists() else domain_dotenv
        
        if not dotenv_path.exists():
            return
        
        for line in dotenv_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and value and key not in os.environ:
                    os.environ[key] = value
    except Exception as e:
        pass  # Silently ignore if .env loading fails

# Load .env at module import time
_load_env_from_dotenv()


def extract_json_from_response(text: str) -> Optional[str]:
    """Extract JSON content from model output (looks for <JSON>...</JSON> tags)"""
    if not text:
        return None
    
    # Try to extract from <JSON> tags
    match = re.search(r"<JSON>([\s\S]*?)</JSON>", text)
    if match:
        return match.group(1).strip()
    
    # If no tags, return as-is and let caller try to parse
    return text


def process_single_report(
    report_file: Path,
    output_dir: Path,
    model_name: str,
    client: openai.OpenAI,
    format_prompt: str,
    print_lock: Lock,
    max_retries: int = 30
) -> Dict:
    """
    Process a single report file and convert to JSON
    
    Args:
        report_file: Input report file path
        output_dir: Output directory for converted JSON
        model_name: Model name for API call
        client: OpenAI client instance
        format_prompt: Format conversion prompt
        print_lock: Thread-safe print lock
        max_retries: Maximum number of retries for JSON parsing errors
        
    Returns:
        Processing result dictionary
    """
    sample_id = None
    
    # Extract sample_id from filename (format: id_X.txt)
    filename = report_file.name
    match = re.match(r'id_(\d+)\.txt', filename)
    if match:
        sample_id = match.group(1)
    else:
        # Try without id_ prefix
        match = re.match(r'(\d+)_final_answer\.txt', filename)
        if match:
            sample_id = match.group(1)
        else:
            sample_id = report_file.stem.replace('_final_answer', '')
    
    # Retry loop for JSON parsing errors
    for attempt in range(max_retries + 1):
        try:
            if attempt == 0:
                with print_lock:
                    print(f"\n{'='*80}")
                    print(f"🚀 [Thread Started] Processing Sample ID: {sample_id}")
                    print(f"   Input File: {report_file.name}")
                    print(f"{'='*80}")
            else:
                with print_lock:
                    print(f"🔄 Sample {sample_id} JSON parsing failed, retry attempt {attempt}...")
            
            # Read raw text
            raw_text = report_file.read_text(encoding='utf-8')
            
            # Construct messages
            messages = [
                {"role": "system", "content": format_prompt},
                {"role": "user", "content": raw_text},
            ]
            
            # Call LLM for conversion
            resp = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=10240
            )
            
            content = resp.choices[0].message.content or ""
            
            # Extract JSON
            json_payload = extract_json_from_response(content)
            if not json_payload:
                # If no tags and can't parse directly, fail this attempt
                try:
                    json.loads(content)
                    json_payload = content
                except Exception as e:
                    raise ValueError(f"LLM did not return content with <JSON> tags, and direct parsing failed: {e}")
            
            # Validate JSON (this is the key step for retry)
            parsed = json.loads(json_payload)
            
            # If successful, save and exit loop
            output_file = output_dir / f'id_{sample_id}_converted.json'
            output_file.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding='utf-8')
            
            with print_lock:
                print(f"✅ Sample {sample_id} conversion completed (attempt {attempt + 1})")
                print(f"   Output File: {output_file.name}\n")
            
            return {
                'success': True,
                'sample_id': sample_id,
                'input_file': str(report_file),
                'output_file': str(output_file)
            }
        
        except (json.JSONDecodeError, ValueError) as e:
            # Catch JSON parsing errors and our ValueError
            # If last attempt, record failure and exit
            if attempt >= max_retries:
                with print_lock:
                    print(f"❌ Sample {sample_id} failed after {max_retries + 1} attempts: {e}\n")
                
                return {
                    'success': False,
                    'sample_id': sample_id,
                    'input_file': str(report_file),
                    'error': str(e)
                }
            # If not last attempt, continue to next retry
            time.sleep(1)  # Brief delay to avoid rapid requests
            
        except Exception as e:
            # Catch other unexpected errors (e.g., network issues)
            if attempt >= max_retries:
                with print_lock:
                    print(f"❌ Sample {sample_id} encountered unexpected error: {e}\n")
                
                return {
                    'success': False,
                    'sample_id': sample_id,
                    'input_file': str(report_file),
                    'error': str(e)
                }
            time.sleep(1)


def convert_reports(
    result_dir: Path,
    language: str = 'zh',
    workers: int = 10,
    skip_existing: bool = False,
    verbose: bool = False,
) -> Dict:
    """
    Convert multiple report files to JSON format
    
    Note: This function always uses qwen-plus for conversion
    
    Args:
        result_dir: Result directory containing 'reports' subdirectory
        language: Language for prompts ('zh' or 'en')
        workers: Number of concurrent workers
        skip_existing: Skip files that already have output
        verbose: Enable verbose output
        
    Returns:
        dict: {'total': int, 'converted': int, 'skipped': int, 'results': list}
    """
    # Set reports_dir and output_dir based on result_dir
    reports_dir = result_dir / 'reports'
    output_dir = result_dir / 'converted_plans'
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Always use qwen-plus for conversion
    conversion_model = 'qwen-plus'
    
    # Load model config and create client
    model_config = load_model_config(conversion_model)
    client = create_client(conversion_model, model_config)
    
    # Get actual model name for API call
    actual_model_name = model_config.get('model_name', conversion_model)
    
    # Get format prompt
    format_prompt = get_format_convert_prompt(language)
    
    # Find all report files
    report_files = list(reports_dir.glob('id_*.txt'))
    
    if not report_files:
        print(f"⚠️  No report files found in {reports_dir}")
        return {'total': 0, 'converted': 0, 'skipped': 0, 'success': 0, 'failed': 0, 'results': []}
    
    # Track original count and filtered files
    original_count = len(report_files)
    skipped_count = 0
    
    # Filter out existing files if skip_existing is True
    if skip_existing:
        filtered_files = []
        for report_file in report_files:
            # Extract sample_id
            match = re.match(r'id_(\d+)\.txt', report_file.name)
            if match:
                sample_id = match.group(1)
            else:
                sample_id = report_file.stem.replace('_final_answer', '')
            
            # Check if output file already exists
            output_file = output_dir / f'id_{sample_id}_converted.json'
            if not output_file.exists():
                filtered_files.append(report_file)
        
        skipped_count = original_count - len(filtered_files)
        report_files = filtered_files
        
        if skipped_count > 0:
            print(f"⏭️  Skipped {skipped_count} existing files")
        
        if not report_files:
            print(f"✅ All files already converted, nothing to process")
            return {'total': original_count, 'converted': 0, 'skipped': skipped_count, 'success': 0, 'failed': 0, 'results': []}
    
    print(f"\n{'='*80}")
    print(f"📊 Found {len(report_files)} report files to convert")
    print(f"🚀 Using {workers} concurrent workers")
    print(f"📂 Input Directory: {reports_dir}")
    print(f"📂 Output Directory: {output_dir}")
    print(f"🌐 Language: {language}")
    print(f"🤖 Conversion Model: {actual_model_name}")
    print(f"{'='*80}\n")
    
    # Create print lock
    print_lock = Lock()
    
    # Record start time
    start_time = time.time()
    
    # Use thread pool for parallel processing
    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Submit all tasks
        future_to_file = {}
        for report_file in report_files:
            future = executor.submit(
                process_single_report,
                report_file,
                output_dir,
                actual_model_name,
                client,
                format_prompt,
                print_lock
            )
            future_to_file[future] = report_file
        
        # Collect results (in completion order)
        for future in as_completed(future_to_file):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                report_file = future_to_file[future]
                with print_lock:
                    print(f"❌ File {report_file.name} encountered uncaught exception: {e}\n")
                results.append({
                    'success': False,
                    'sample_id': report_file.name,
                    'error': str(e)
                })
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Statistics
    success_count = sum(1 for r in results if r['success'])
    failed_count = len(results) - success_count
    
    print(f"\n{'='*80}")
    print(f"✅ All report conversions completed!")
    print(f"{'='*80}")
    print(f"📊 Statistics:")
    print(f"   - Total Files: {len(report_files)}")
    print(f"   - Success: {success_count}")
    print(f"   - Failed: {failed_count}")
    print(f"   - Total Time: {elapsed_time:.2f} seconds")
    print(f"   - Average Time: {elapsed_time/len(report_files):.2f} seconds/file")
    print(f"   - Output Directory: {output_dir}")
    print(f"{'='*80}\n")
    
    return {
        'total': original_count,
        'converted': success_count,
        'skipped': skipped_count,
        'success': success_count,
        'failed': failed_count,
        'results': results,
        'elapsed_time': elapsed_time,
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Convert report files to JSON format (always uses qwen-plus)'
    )
    parser.add_argument('--result-dir', type=Path, required=True,
                       help='Result directory containing reports/ subdirectory')
    parser.add_argument('--language', type=str, default='zh', choices=['zh', 'en'],
                       help='Language for prompts (zh or en)')
    parser.add_argument('--workers', type=int, default=10,
                       help='Number of concurrent workers')
    parser.add_argument('--skip-existing', action='store_true',
                       help='Skip files that already have output')
    
    args = parser.parse_args()
    
    result = convert_reports(
        result_dir=args.result_dir,
        language=args.language,
        workers=args.workers,
        skip_existing=args.skip_existing,
    )
    
    print(f"Conversion completed: {result['success']}/{result['total']} succeeded")

