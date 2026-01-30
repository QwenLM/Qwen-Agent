#!/usr/bin/env python3
"""
Score statistics script
Calculate total scores for a model across all levels
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def parse_folder_name(folder_name: str) -> Optional[tuple]:
    """
    Parse folder name to extract model name, difficulty level, and timestamp
    Format: database_{model_name}_level{1|2|3}_{timestamp}
    Returns: (model_name, level, timestamp) or None
    """
    # Match format: database_xxx_level1/2/3_xxx
    pattern = r'^database_(.+?)_level([123])_(\d+)$'
    match = re.match(pattern, folder_name)
    if match:
        model_name = match.group(1)
        level = int(match.group(2))
        timestamp = match.group(3)
        return model_name, level, timestamp
    return None


def read_summary_report(report_path: Path) -> Optional[Dict[str, Any]]:
    """
    Read summary_report.json file
    Returns: Dictionary containing statistics
    """
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        overall_stats = data.get('overall_statistics', {})
        
        return {
            'total_cases': overall_stats.get('total_cases', 0),
            'successful_cases': overall_stats.get('successful_cases', 0),
            'failed_cases': overall_stats.get('failed_cases', 0),
            'total_matched_products': overall_stats.get('total_matched_products', 0),
            'total_expected_products': overall_stats.get('total_expected_products', 0),
            'total_extra_products': overall_stats.get('total_extra_products', 0),
            'average_case_score': overall_stats.get('average_case_score', 0.0),
            'overall_match_rate': overall_stats.get('overall_match_rate', 0.0),
            'incomplete_cases': overall_stats.get('incomplete_cases', 0),
            'incomplete_rate': overall_stats.get('incomplete_rate', 0.0),
            'valid': overall_stats.get('valid', False),
        }
    except Exception as e:
        print(f"❌ Error reading {report_path}: {e}")
        return None


def calculate_model_statistics(model_name: str, result_report_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Calculate total scores for a specified model across all levels
    
    Args:
        model_name: Model name
        result_report_dir: Path to result_report directory
        
    Returns:
        Dictionary containing statistics, or None if model data is incomplete
    """
    if not result_report_dir.exists():
        print(f"❌ Error: Directory {result_report_dir} does not exist")
        return None
    
    # Store data for each level, format: {level: [(timestamp, folder_name, result), ...]}
    level_candidates = {}
    
    # Iterate through all subdirectories to find all level data for this model
    for folder in result_report_dir.iterdir():
        if not folder.is_dir():
            continue
        
        # Parse folder name
        parsed = parse_folder_name(folder.name)
        if parsed is None:
            continue
        
        folder_model_name, level, timestamp = parsed
        
        # Only process data for the specified model
        if folder_model_name != model_name:
            continue
        
        # Read summary_report.json
        report_path = folder / "summary_report.json"
        if not report_path.exists():
            print(f"⚠️  Warning: {report_path} does not exist, skipping")
            continue
        
        result = read_summary_report(report_path)
        if result is None:
            continue
        
        # Store candidate results
        if level not in level_candidates:
            level_candidates[level] = []
        level_candidates[level].append((int(timestamp), folder.name, result))
    
    # For each level, select the result with the latest timestamp
    level_data = {}
    for level, candidates in level_candidates.items():
        # Sort by timestamp in descending order, take the latest
        candidates.sort(key=lambda x: x[0], reverse=True)
        timestamp, folder_name, result = candidates[0]
        level_data[level] = {
            'folder_name': folder_name,
            'timestamp': timestamp,
            **result
        }
    
    # Check if all three levels are complete
    if set(level_data.keys()) != {1, 2, 3}:
        missing_levels = {1, 2, 3} - set(level_data.keys())
        print(f"⚠️  Warning: Model {model_name} does not have complete level data. Missing levels: {missing_levels}")
        # Even if incomplete, calculate statistics for existing levels
        if not level_data:
            return None
    
    # Aggregate data from all levels
    total_cases_sum = sum(level_data[level]['total_cases'] for level in level_data.keys())
    successful_cases_sum = sum(level_data[level]['successful_cases'] for level in level_data.keys())
    failed_cases_sum = sum(level_data[level]['failed_cases'] for level in level_data.keys())
    total_matched_products_sum = sum(level_data[level]['total_matched_products'] for level in level_data.keys())
    total_expected_products_sum = sum(level_data[level]['total_expected_products'] for level in level_data.keys())
    total_extra_products_sum = sum(level_data[level]['total_extra_products'] for level in level_data.keys())
    incomplete_cases_sum = sum(level_data[level]['incomplete_cases'] for level in level_data.keys())
    
    # Calculate weighted average of average_case_score (weighted by case count)
    weighted_avg_score = 0.0
    if total_cases_sum > 0:
        weighted_avg_score = sum(
            level_data[level]['average_case_score'] * level_data[level]['total_cases']
            for level in level_data.keys()
        ) / total_cases_sum
    
    # Calculate success rate
    successful_rate = successful_cases_sum / total_cases_sum if total_cases_sum > 0 else 0.0
    
    # Calculate match rate
    match_rate = total_matched_products_sum / total_expected_products_sum if total_expected_products_sum > 0 else 0.0
    
    # Calculate incomplete rate
    incomplete_rate = incomplete_cases_sum / total_cases_sum if total_cases_sum > 0 else 0.0
    
    # Check if all levels are valid
    all_valid = all(level_data[level]['valid'] for level in level_data.keys())
    
    # Build result
    result = {
        'model_name': model_name,
        'statistics_time': datetime.now().isoformat(),
        'levels': {
            f'level_{level}': {
                'folder_name': level_data[level]['folder_name'],
                'total_cases': level_data[level]['total_cases'],
                'successful_cases': level_data[level]['successful_cases'],
                'failed_cases': level_data[level]['failed_cases'],
                'total_matched_products': level_data[level]['total_matched_products'],
                'total_expected_products': level_data[level]['total_expected_products'],
                'total_extra_products': level_data[level]['total_extra_products'],
                'average_case_score': level_data[level]['average_case_score'],
                'overall_match_rate': level_data[level]['overall_match_rate'],
                'incomplete_cases': level_data[level]['incomplete_cases'],
                'incomplete_rate': level_data[level]['incomplete_rate'],
                'valid': level_data[level]['valid'],
            }
            for level in sorted(level_data.keys())
        },
        'total': {
            'total_cases': total_cases_sum,
            'successful_cases': successful_cases_sum,
            'failed_cases': failed_cases_sum,
            'total_matched_products': total_matched_products_sum,
            'total_expected_products': total_expected_products_sum,
            'total_extra_products': total_extra_products_sum,
            'successful_rate': successful_rate,
            'match_rate': match_rate,
            'weighted_average_case_score': weighted_avg_score,
            'incomplete_cases': incomplete_cases_sum,
            'incomplete_rate': incomplete_rate,
            'valid': all_valid,
            'levels_completed': sorted(level_data.keys()),
        }
    }
    
    return result


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Calculate statistics for a model across all levels")
    parser.add_argument(
        "--model_name",
        type=str,
        required=True,
        help="Model name to calculate statistics for"
    )
    parser.add_argument(
        "--result_report_dir",
        type=str,
        default=None,
        help="Path to result_report directory (default: script_dir/result_report)"
    )
    
    args = parser.parse_args()
    
    # Determine root directory
    script_dir = Path(__file__).resolve().parent.parent
    
    # Set result_report directory
    if args.result_report_dir:
        result_report_dir = Path(args.result_report_dir)
        if result_report_dir.is_absolute():
            pass
        else:
            result_report_dir = script_dir / args.result_report_dir
    else:
        result_report_dir = script_dir / "result_report"
    
    print(f"\n{'='*80}")
    print(f"📊 Calculating Statistics for Model: {args.model_name}")
    print(f"{'='*80}")
    print(f"  Result report directory: {result_report_dir}")
    print()
    
    # Calculate statistics
    statistics = calculate_model_statistics(args.model_name, result_report_dir)
    
    if statistics is None:
        print(f"❌ Failed to calculate statistics for model {args.model_name}")
        sys.exit(1)
    
    # Save results to result_report directory
    output_file = result_report_dir / f"{args.model_name}_statistics.json"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(statistics, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Statistics saved to: {output_file}")
        print()
        
        # Print summary
        print(f"{'='*80}")
        print(f"📊 Summary for {args.model_name}")
        print(f"{'='*80}")
        print(f"  Levels completed: {', '.join(map(str, statistics['total']['levels_completed']))}")
        print(f"  Total cases: {statistics['total']['total_cases']}")
        print(f"  Successful cases: {statistics['total']['successful_cases']}")
        print(f"  Failed cases: {statistics['total']['failed_cases']}")
        print(f"  Successful rate: {statistics['total']['successful_rate']:.4f} ({statistics['total']['successful_rate']:.2%})")
        print(f"  Match rate: {statistics['total']['match_rate']:.4f} ({statistics['total']['match_rate']:.2%})")
        print(f"  Weighted average case score: {statistics['total']['weighted_average_case_score']:.4f} ({statistics['total']['weighted_average_case_score']:.2%})")
        print(f"  Total matched products: {statistics['total']['total_matched_products']}/{statistics['total']['total_expected_products']}")
        print(f"  Total extra products: {statistics['total']['total_extra_products']}")
        print(f"  Incomplete cases: {statistics['total']['incomplete_cases']} ({statistics['total']['incomplete_rate']:.2%})")
        print(f"  Model valid: {statistics['total']['valid']} {'✅' if statistics['total']['valid'] else '❌'}")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"❌ Failed to save statistics: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

