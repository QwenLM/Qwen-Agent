"""
Evaluation Script for Converted Travel Plans
Evaluates both commonsense and hard constraints with parallel processing
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from .constraints_commonsense import eval_commonsense, EVALUATION_DIMENSIONS
from .constraints_hard import eval_hard


def calculate_weighted_score(commonsense_results: Dict[str, Tuple[bool, Optional[str]]]) -> Dict[str, Any]:
    """
    Calculate weighted commonsense score based on EVALUATION_DIMENSIONS.
    
    Scoring rule (one-vote veto per dimension):
    - If ALL checks in a dimension pass → dimension score = 1.0
    - If ANY check in a dimension fails → dimension score = 0.0
    - Total weighted score = Σ(dimension_score × weight)
    
    Args:
        commonsense_results: Dict of {check_name: (passed, error_message)}
    
    Returns:
        Dict containing:
        - total_weighted_score: float (0.0-1.0)
        - dimension_scores: {dimension_name: score}
        - dimension_details: {dimension_name: {passed, total, weight, checks}}
    """
    dimension_scores = {}
    dimension_details = {}
    total_weighted_score = 0.0
    
    for dim_name, dim_config in EVALUATION_DIMENSIONS.items():
        weight = dim_config["weight"]
        checks = dim_config["checks"]
        
        passed_count = 0
        total_count = 0
        check_details = []
        
        for check_name in checks:
            if check_name in commonsense_results:
                passed, msg = commonsense_results[check_name]
                if passed is not None:
                    total_count += 1
                    if passed:
                        passed_count += 1
                    check_details.append({
                        "name": check_name,
                        "passed": passed,
                        "message": msg
                    })
        
        # One-vote veto: all checks must pass for dimension score = 1.0
        dim_score = 1.0 if (total_count > 0 and passed_count == total_count) else 0.0
        dimension_scores[dim_name] = dim_score
        
        dimension_details[dim_name] = {
            "passed": passed_count,
            "total": total_count,
            "weight": weight,
            "score": dim_score,
            "weighted_score": dim_score * weight,
            "checks": check_details
        }
        
        total_weighted_score += dim_score * weight
    
    return {
        "total_weighted_score": total_weighted_score,
        "dimension_scores": dimension_scores,
        "dimension_details": dimension_details
    }


def calculate_hard_score(hard_results: Dict[str, Tuple[bool, Optional[str]]]) -> Dict[str, Any]:
    """
    Calculate hard constraint score using one-vote veto rule.
    
    Scoring rule:
    - If ALL hard constraints pass → score = 1.0
    - If ANY hard constraint fails → score = 0.0
    
    Args:
        hard_results: Dict of {constraint_name: (passed, error_message)}
    
    Returns:
        Dict containing:
        - score: float (0.0 or 1.0)
        - constraints: dict of {constraint_name: {"passed": bool, "message": str or None}}
    """
    passed_count = 0
    total = 0
    constraints = {}
    
    for constraint_name, (ok, msg) in hard_results.items():
        if ok is None:
            continue
        total += 1
        constraints[constraint_name] = {
            "passed": ok,
            "message": msg
        }
        if ok:
            passed_count += 1
    
    # One-vote veto: all must pass for score = 1.0
    score = 1.0 if (total > 0 and passed_count == total) else 0.0
    
    return {
        "score": score,
        "constraints": constraints
    }


def process_single_evaluation(
    plan_file: Path,
    test_samples: List[Dict],
    output_dir: Path,
    database_dir: Path,
    print_lock: Lock
) -> Dict[str, Any]:
    """
    Evaluate a single sample
    
    Args:
        plan_file: Converted plan JSON file
        test_samples: List of test samples (contains meta_info)
        output_dir: Output directory
        database_dir: Database root directory
        print_lock: Print lock for thread-safe console output
        
    Returns:
        Evaluation result dictionary
    """
    sample_id = None
    try:
        # Extract sample_id from filename (format: id_X_converted.json)
        filename = plan_file.name
        match = re.match(r'id_(\d+)_converted\.json', filename)
        if match:
            sample_id = match.group(1)
        else:
            sample_id = plan_file.stem.replace('_converted', '').replace('id_', '')
        
        with print_lock:
            print(f"\n{'='*80}")
            print(f"🚀 [Thread Started] Evaluating Sample ID: {sample_id}")
            print(f"   Plan File: {plan_file.name}")
            print(f"{'='*80}")
        
        # Find corresponding meta_info
        meta = None
        for sample in test_samples:
            if str(sample.get('id')) == str(sample_id):
                meta = sample.get('meta_info', {})
                break
        
        if meta is None:
            raise ValueError(f"meta_info not found for sample {sample_id}")
        
        # Set database path
        sample_database_path = database_dir / f'id_{sample_id}'
        if not sample_database_path.exists():
            # Try without id_ prefix
            sample_database_path = database_dir / sample_id
            if not sample_database_path.exists():
                raise FileNotFoundError(f"Database directory does not exist: {sample_database_path}")
        
        # Read plan
        plan = json.loads(plan_file.read_text(encoding='utf-8'))
        
        # Execute evaluation, pass database_path directly to avoid multi-threading conflicts
        commonsense = eval_commonsense(plan, meta, database_dir=sample_database_path)
        hard = eval_hard(plan, meta)
        
        # Calculate weighted commonsense score
        weighted_result = calculate_weighted_score(commonsense)
        commonsense_score = weighted_result["total_weighted_score"]
        
        # Calculate hard constraint score (one-vote veto)
        hard_result = calculate_hard_score(hard)
        personalized_score = hard_result["score"]
        
        # Calculate composite score (average of commonsense and personalized)
        composite_score = (commonsense_score + personalized_score) / 2
        
        # Calculate case_acc (one-vote veto: both must be 1.0)
        case_acc = 1.0 if (commonsense_score == 1.0 and personalized_score == 1.0) else 0.0
        
        # Build evaluation result
        eval_result = {
            "sample_id": sample_id,
            "scores": {
                "commonsense_weighted_score": commonsense_score,
                "personalized_score": personalized_score,
                "composite_score": composite_score,
                "case_acc": case_acc,
            },
            "commonsense_dimension_scores": weighted_result["dimension_scores"],
            "commonsense_dimension_details": weighted_result["dimension_details"],
            "personalized_dimension_score": hard_result,
        }
        
        # Save evaluation result
        output_file = output_dir / f'id_{sample_id}_score.json'
        output_file.write_text(json.dumps(eval_result, ensure_ascii=False, indent=2), encoding='utf-8')
        
        # Count hard constraints for display
        hard_passed = sum(1 for c in hard_result["constraints"].values() if c["passed"])
        hard_total = len(hard_result["constraints"])
        
        with print_lock:
            print(f"✅ Sample {sample_id} evaluation completed")
            print(f"   Commonsense (Weighted): {commonsense_score:.2%}")
            print(f"   Personalized Constraints (0/1): {personalized_score:.0%} ({hard_passed}/{hard_total})")
            print(f"   Final Score: {composite_score:.2%}")
            print(f"   Output File: {output_file.name}\n")
        
        return {
            'success': True,
            'sample_id': sample_id,
            'scores': eval_result['scores'],
            'commonsense_dimension_details': eval_result['commonsense_dimension_details'],
            'personalized_dimension_score': eval_result['personalized_dimension_score'],
        }
        
    except Exception as e:
        with print_lock:
            print(f"❌ Sample {sample_id or plan_file.name} evaluation failed: {e}\n")
        
        return {
            'success': False,
            'sample_id': sample_id or plan_file.name,
            'error': str(e)
        }


def evaluate_plans(
    result_dir: Path,
    test_data_path: Path,
    database_dir: Path,
    workers: int = 10,
    verbose: bool = False,
) -> Dict:
    """
    Evaluate multiple converted plans
    
    Args:
        result_dir: Result directory containing 'converted_plans' subdirectory
        test_data_path: Path to test data JSON (contains meta_info)
        database_dir: Database root directory
        workers: Number of concurrent workers
        verbose: Enable verbose output
        
    Returns:
        dict: Evaluation summary with statistics
    """
    # Set plans_dir and output_dir based on result_dir
    plans_dir = result_dir / 'converted_plans'
    output_dir = result_dir / 'evaluation'
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Read test data
    print(f"\nLoading test data from {test_data_path}")
    with open(test_data_path, 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    
    # Ensure test_data is a list
    if isinstance(test_data, dict):
        test_samples = [test_data]
    elif isinstance(test_data, list):
        test_samples = test_data
    else:
        raise ValueError("test_data.json format error: should be a dict or list")
    
    total_test_samples = len(test_samples)
    
    # Create a set of valid sample IDs
    valid_sample_ids = set(str(sample.get('id')) for sample in test_samples)
    
    # Find all plan files
    all_plan_files = list(plans_dir.glob('id_*_converted.json'))
    if not all_plan_files:
        # Try without id_ prefix
        all_plan_files = list(plans_dir.glob('*_converted.json'))
    
    if not all_plan_files:
        print(f"⚠️  No plan files found in {plans_dir}")
        return {'total': 0, 'success': 0, 'failed': 0, 'results': []}
    
    # Filter plan files to only include those in the test data
    plan_files = []
    skipped_files = []
    for plan_file in all_plan_files:
        # Extract sample_id from filename
        match = re.match(r'id_(\d+)_converted\.json', plan_file.name)
        if match:
            sample_id = match.group(1)
        else:
            sample_id = plan_file.stem.replace('_converted', '').replace('id_', '')
        
        if sample_id in valid_sample_ids:
            plan_files.append(plan_file)
        else:
            skipped_files.append((plan_file.name, sample_id))
    
    if not plan_files:
        print(f"⚠️  No plan files match the test data samples in {plans_dir}")
        return {'total': 0, 'success': 0, 'failed': 0, 'results': []}
    
    print(f"\n{'='*80}")
    print(f"📊 Evaluation Overview:")
    print(f"   - Total samples in test data: {total_test_samples}")
    print(f"   - Total plan files found: {len(all_plan_files)}")
    print(f"   - Plan files to evaluate (in test data): {len(plan_files)}")
    if skipped_files:
        print(f"   - Plan files skipped (not in test data): {len(skipped_files)}")
    print(f"   - Delivery rate: {len(plan_files)/total_test_samples:.2%}")
    print(f"🚀 Using {workers} threads for parallel processing")
    print(f"📂 Input Directory: {plans_dir}")
    print(f"📂 Output Directory: {output_dir}")
    print(f"📂 Database Directory: {database_dir}")
    print(f"📋 Test Data File: {test_data_path.name}")
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
        for plan_file in plan_files:
            future = executor.submit(
                process_single_evaluation,
                plan_file,
                test_samples,
                output_dir,
                database_dir,
                print_lock
            )
            future_to_file[future] = plan_file
        
        # Collect results (in completion order)
        for future in as_completed(future_to_file):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                plan_file = future_to_file[future]
                with print_lock:
                    print(f"❌ File {plan_file.name} encountered uncaught exception: {e}\n")
                results.append({
                    'success': False,
                    'sample_id': plan_file.name,
                    'error': str(e)
                })
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Statistics
    success_count = sum(1 for r in results if r['success'])
    failed_count = len(results) - success_count
    valid_results = [r for r in results if r['success']]
    
    # Calculate metrics
    sum_commonsense_weighted = 0.0
    sum_personalized_score = 0.0
    sum_composite_score = 0.0
    sum_case_acc = 0.0
    commonsense_perfect_count = 0
    personalized_perfect_count = 0
    final_pass_count = 0
    
    # Initialize dimension statistics
    dimension_stats = {dim: {'sum_score': 0.0, 'perfect_count': 0, 'weight': cfg['weight']} 
                       for dim, cfg in EVALUATION_DIMENSIONS.items()}
    
    for r in valid_results:
        # Accumulate scores
        commonsense_score = r['scores']['commonsense_weighted_score']
        personalized_score = r['scores']['personalized_score']
        composite_score = r['scores']['composite_score']
        case_acc = r['scores']['case_acc']
        
        sum_commonsense_weighted += commonsense_score
        sum_personalized_score += personalized_score
        sum_composite_score += composite_score
        sum_case_acc += case_acc
        
        # Count perfect scores
        if commonsense_score == 1.0:
            commonsense_perfect_count += 1
        if personalized_score == 1.0:
            personalized_perfect_count += 1
        if commonsense_score == 1.0 and personalized_score == 1.0:
            final_pass_count += 1
        
        # Accumulate dimension-level statistics
        if 'commonsense_dimension_details' in r:
            for dim_name, dim_detail in r['commonsense_dimension_details'].items():
                if dim_name in dimension_stats:
                    dim_score = dim_detail.get('score', 0.0)
                    dimension_stats[dim_name]['sum_score'] += dim_score
                    if dim_score == 1.0:
                        dimension_stats[dim_name]['perfect_count'] += 1
    
    # Average scores across all test samples
    commonsense_avg = sum_commonsense_weighted / total_test_samples if total_test_samples > 0 else 0.0
    personalized_avg = sum_personalized_score / total_test_samples if total_test_samples > 0 else 0.0
    final_avg = sum_composite_score / total_test_samples if total_test_samples > 0 else 0.0
    case_acc_avg = sum_case_acc / total_test_samples if total_test_samples > 0 else 0.0
    
    # Calculate dimension-level metrics
    dimension_metrics = {}
    for dim_name, stats in dimension_stats.items():
        dimension_metrics[dim_name] = {
            'weight': stats['weight'],
            'score': stats['sum_score'] / total_test_samples if total_test_samples > 0 else 0.0,
            'perfect_count': stats['perfect_count']
        }
    
    # Delivery rate
    delivery_rate = len(plan_files) / total_test_samples if total_test_samples > 0 else 0.0
    
    # Count error occurrences
    error_stats = {}
    for result in valid_results:
        sample_id = result.get('sample_id', 'unknown')
        
        # Count commonsense constraint errors
        if 'commonsense_dimension_details' in result:
            for dim_name, dim_detail in result['commonsense_dimension_details'].items():
                for check in dim_detail.get('checks', []):
                    if not check.get('passed') and check.get('message'):
                        error_type = f"[Commonsense] {check['name']}"
                        if error_type not in error_stats:
                            error_stats[error_type] = {
                                'count': 0,
                                'samples': [],
                                'messages': []
                            }
                        error_stats[error_type]['count'] += 1
                        error_stats[error_type]['samples'].append(sample_id)
                        error_stats[error_type]['messages'].append(check['message'])
        
        # Count hard constraint errors
        if 'personalized_dimension_score' in result:
            for constraint_name, constraint_info in result['personalized_dimension_score'].get('constraints', {}).items():
                if not constraint_info.get('passed') and constraint_info.get('message'):
                    error_type = f"[Hard] {constraint_name}"
                    if error_type not in error_stats:
                        error_stats[error_type] = {
                            'count': 0,
                            'samples': [],
                            'messages': []
                        }
                    error_stats[error_type]['count'] += 1
                    error_stats[error_type]['samples'].append(sample_id)
                    error_stats[error_type]['messages'].append(constraint_info['message'])
    
    # Sort by occurrence count (descending)
    sorted_errors = sorted(error_stats.items(), key=lambda x: x[1]['count'], reverse=True)
    
    print(f"\n{'='*80}")
    print(f"✅ All samples evaluated!")
    print(f"{'='*80}")
    print(f"📊 Statistics:")
    print(f"   - Total samples in test data: {total_test_samples}")
    print(f"   - Plan files evaluated: {len(plan_files)}")
    print(f"   - Evaluation success: {success_count}")
    print(f"   - Evaluation failed: {failed_count}")
    print(f"   - Total Time: {elapsed_time:.2f} seconds")
    print(f"   - Average Time: {elapsed_time/len(plan_files):.2f} seconds/sample" if plan_files else "   - N/A")
    print(f"\n📈 Evaluation Metrics:")
    print(f"   Delivery Rate: {delivery_rate:.2%} ({len(plan_files)}/{total_test_samples} samples)")
    print(f"   ")
    print(f"   Commonsense Constraints (Weighted): {commonsense_avg:.2%}")
    print(f"   ")
    print(f"   Commonsense By Dimension:")
    for dim_name, metrics in dimension_metrics.items():
        print(f"      • {dim_name} (weight={metrics['weight']:.0%}): {metrics['score']:.2%}")
    print(f"   ")
    print(f"   Personalized Constraints (0/1): {personalized_avg:.2%}")
    print(f"   ")
    print(f"   ┌───────────────────────────────────────────────────────────┐")
    print(f"   │ composite score = (Commonsense + Personalized) / 2 = {final_avg:.2%}     │")
    print(f"   │ Final Passed (Both=1.0) = {case_acc_avg:.2%}                     │")
    print(f"   └───────────────────────────────────────────────────────────┘")
    
    # Output error statistics
    if sorted_errors:
        print(f"\n❌ Error Statistics (sorted by occurrence count):")
        print(f"{'='*80}")
        for i, (error_type, error_info) in enumerate(sorted_errors[:10], 1):  # Show top 10
            print(f"{i}. {error_type}")
            print(f"   Occurrences: {error_info['count']}")
            print(f"   Affected Samples: {', '.join(error_info['samples'][:5])}", end="")
            if len(error_info['samples']) > 5:
                print(f" (and {len(error_info['samples']) - 5} more)")
            else:
                print()
            # Show first error message as example
            if error_info['messages']:
                sample_msg = error_info['messages'][0]
                if len(sample_msg) > 100:
                    sample_msg = sample_msg[:100] + "..."
                print(f"   Example Message: {sample_msg}")
            print()
    else:
        print(f"\n✨ No constraint violations found!")
    
    print(f"\n📂 Output Directory: {output_dir}")
    print(f"{'='*80}\n")
    
    # Save evaluation summary
    summary_path = output_dir / 'evaluation_summary.json'
    
    # Build serializable error statistics data
    error_stats_serializable = [
        {
            'rank': i + 1,
            'error_type': error_type,
            'count': error_info['count'],
            'affected_samples': error_info['samples'],
            'sample_messages': error_info['messages']
        }
        for i, (error_type, error_info) in enumerate(sorted_errors)
    ]
    
    summary_data = {
        'total_test_samples': total_test_samples,
        'plan_files_found': len(plan_files),
        'evaluation_success_count': success_count,
        'evaluation_failed_count': failed_count,
        'elapsed_time': elapsed_time,
        'max_workers': workers,
        'metrics': {
            'delivery_rate': delivery_rate,
            'commonsense_score': commonsense_avg,
            'commonsense_dimensions': dimension_metrics,
            'personalized_score': personalized_avg,
            'composite_score': final_avg,
            'case_acc': case_acc_avg
        },
        'error_statistics': error_stats_serializable,
        'results': results
    }
    summary_path.write_text(json.dumps(summary_data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"📄 Evaluation summary saved to: {summary_path}\n")
    
    return {
        'total': len(plan_files),
        'success': success_count,
        'failed': failed_count,
        'average_score': final_avg,
        'pass_rate': (final_pass_count / total_test_samples * 100) if total_test_samples > 0 else 0.0,
        'results': results,
        'metrics': summary_data['metrics'],
        'elapsed_time': elapsed_time,
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Evaluate converted travel plans')
    parser.add_argument('--plans-dir', type=Path, required=True,
                       help='Directory containing converted plan JSON files')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Output directory for evaluation results')
    parser.add_argument('--test-data', type=Path, required=True,
                       help='Test data JSON file (contains meta_info)')
    parser.add_argument('--database-dir', type=Path, required=True,
                       help='Database root directory')
    parser.add_argument('--workers', type=int, default=10,
                       help='Number of concurrent workers')
    
    args = parser.parse_args()
    
    result = evaluate_plans(
        plans_dir=args.plans_dir,
        output_dir=args.output_dir,
        test_data_path=args.test_data,
        database_dir=args.database_dir,
        workers=args.workers,
    )
    
    print(f"Evaluation completed: {result['success']}/{result['total']} succeeded")
    print(f"composite score: {result['metrics']['composite_score']:.2%}")

