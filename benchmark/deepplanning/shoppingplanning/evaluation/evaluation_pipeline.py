import json
import sys
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def load_validation_cases(json_path: Path) -> Dict[str, Any]:
    if not json_path.exists():
        print(f"⚠️  Warning: Validation cases file not found: {json_path}")
        return {}

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except Exception as e:
        print(f"❌ Error: Failed to load validation cases file {json_path}: {e}")
        return {}


def load_cart(cart_path: Path) -> Dict[str, Any]:
    if not cart_path.exists():
        print(f"⚠️  Warning: Cart file not found: {cart_path}")
        return {}

    try:
        with open(cart_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error: Failed to load cart file {cart_path}: {e}")
        return {}


def check_case_completion(messages_path: Path) -> bool:
    """
    Check if a case is completed by examining the last message in messages.json.
    A case is considered incomplete if the last message contains tool_calls.
    
    Args:
        messages_path: Path to messages.json file
        
    Returns:
        True if case is completed (no tool_calls in last message), False otherwise
    """
    if not messages_path.exists():
        # If messages.json doesn't exist, consider it incomplete
        return False
    
    try:
        with open(messages_path, "r", encoding="utf-8") as f:
            messages_data = json.load(f)
        
        messages = messages_data.get("messages", [])
        if not messages:
            # Empty messages, consider incomplete
            return False
        
        # Get the last message
        last_message = messages[-1]
        
        # If last message is a tool response, case is incomplete (waiting for assistant response)
        if last_message.get("role") == "tool":
            return False
        
        # If last message is assistant with tool_calls, case is incomplete (still calling tools)
        if last_message.get("role") == "assistant":
            tool_calls = last_message.get("tool_calls", [])
            if tool_calls:
                return False
        
        # Last message is assistant without tool_calls, case is completed
        return True
    except Exception as e:
        print(f"⚠️  Warning: Failed to check case completion: {e}")
        # On error, consider it incomplete to be safe
        return False


def evaluate_single_case(case_dir: Path) -> Dict[str, Any]:
    case_name = case_dir.name

    print(f"\n{'='*80}")
    print(f"📊 Start evaluation: {case_name}")
    print(f"{'='*80}\n")

    cart_path = case_dir / "cart.json"
    validation_path = case_dir / "validation_cases.json"
    messages_path = case_dir / "messages.json"

    cart = load_cart(cart_path)
    validation_cases = load_validation_cases(validation_path)
    
    # Check if case is completed
    is_completed = check_case_completion(messages_path)

    if not cart or not validation_cases:
        print(f"⚠️  Warning: {case_name} is missing required files, skipping evaluation")
        return {
            "case_name": case_name,
            "success": False,
            "error": "Missing required files",
            "score": 0.0,
            "details": [],
            "is_completed": False,
        }

    cart_items = cart.get("items", [])
    ground_truth_products = validation_cases.get("ground_truth_products", [])

    print(f"  Number of cart items: {len(cart_items)}")
    print(f"  Number of expected products: {len(ground_truth_products)}\n")

    # Extract product_ids from cart (remove duplicates)
    cart_product_ids = set()
    for cart_item in cart_items:
        product_id = cart_item.get("product_id")
        if product_id:
            cart_product_ids.add(product_id)

    # Extract product_ids from ground truth
    ground_truth_product_ids = set()
    for gt_product in ground_truth_products:
        product_id = gt_product.get("product_id")
        if product_id:
            ground_truth_product_ids.add(product_id)

    # Find matches
    matched_product_ids = cart_product_ids & ground_truth_product_ids

    ground_truth_coupons = validation_cases.get("ground_truth_coupons", {})
    cart_coupons = cart.get("used_coupons", [])
    expected_coupons = len(ground_truth_coupons)
    matched_coupons = 0
    matched_coupon_names = set()
    cart_coupon_names = set()
    matched_coupons_list = []

    # Build coupon matching details for report
    for coupon in cart_coupons:
        coupon_name = coupon.get('coupon_name', '')
        quantity = int(coupon.get('quantity', 0))
        cart_coupon_names.add(coupon_name)
        match_flag = (
            coupon_name in ground_truth_coupons and quantity == ground_truth_coupons[coupon_name]
        )
        if match_flag:
            matched_coupons += 1
            matched_coupon_names.add(coupon_name)
        # Always save coupon detail for the report
        matched_coupons_list.append({
            "coupon_name": coupon_name,
            "quantity": quantity,
            "expected_quantity": ground_truth_coupons.get(coupon_name, 0),
            "match": match_flag
        })

    ground_truth_coupon_names = set(ground_truth_coupons.keys())

    # Calculate scores
    matched_count = len(matched_product_ids) + matched_coupons
    expected_count = len(ground_truth_product_ids) + expected_coupons
    coupon_score = matched_coupons / expected_coupons if expected_coupons > 0 else 0.0
    score = matched_count / expected_count if expected_count > 0 else 0.0

    # Find unmatched and extra
    all_ground_truth_ids = ground_truth_product_ids | ground_truth_coupon_names
    all_matched_ids = matched_product_ids | matched_coupon_names
    unmatched_ground_truth_ids = all_ground_truth_ids - all_matched_ids

    all_cart_ids = cart_product_ids | cart_coupon_names
    extra_product_ids = all_cart_ids - all_ground_truth_ids

    # Prepare details for report
    matched_products = list(matched_product_ids)
    unmatched_ground_truth_products = [
        {
            "product_id": gt_product.get("product_id"),
            "name": gt_product.get("name", ""),
        }
        for gt_product in ground_truth_products
        if gt_product.get("product_id") in unmatched_ground_truth_ids
    ]

    extra_products = [
        {
            "product_id": cart_item.get("product_id"),
            "name": cart_item.get("name", ""),
            "quantity": cart_item.get("quantity", 0),
            "price": cart_item.get("price", 0),
        }
        for cart_item in cart_items
        if cart_item.get("product_id") and cart_item.get("product_id") in extra_product_ids
    ]

    # For reporting of ground_truth_coupons, we store as list of dicts for clearer output
    ground_truth_coupon_info = [
        {
            "coupon_name": coupon_name,
            "expected_quantity": quantity
        }
        for coupon_name, quantity in ground_truth_coupons.items()
    ]
    
    result = {
        "case_name": case_name,
        "success": True,
        "score": score,
        "case_score": 1.0 if matched_count == expected_count else 0.0,
        "matched_count": matched_count,
        "expected_count": expected_count,
        "extra_products_count": len(extra_products),
        "matched_products": matched_products,
        "unmatched_ground_truth_products": unmatched_ground_truth_products,
        "extra_products": extra_products,
        "query": validation_cases.get("query", ""),
        "ground_truth_products": ground_truth_products,
        "matched_coupons": matched_coupons_list,  # Save matched coupon details for report
        "ground_truth_coupons": ground_truth_coupon_info,  # Save for report
        "coupon_score": coupon_score,
        "is_completed": is_completed,  # Whether the case completed (no tool_calls in last message)
    }

    print(f"  Cart product IDs: {sorted(cart_product_ids)}")
    print(f"  Expected product IDs: {sorted(ground_truth_product_ids)}")
    print(f"  Matched product IDs: {sorted(matched_product_ids)}")
    print(f"  ✅ Evaluation finished: Score {score:.2%} ({matched_count}/{expected_count})")
    if not is_completed:
        print(f"  ⚠️  Case incomplete: Last message contains tool_calls")
    if extra_products:
        print(f"  ⚠️  Extra products: {len(extra_products)}")
    if unmatched_ground_truth_products:
        print(f"  ⚠️  Unmatched expected products: {len(unmatched_ground_truth_products)}")

    return result


def generate_case_report(evaluation_result: Dict[str, Any], output_dir: Path) -> Path:
    case_name = evaluation_result["case_name"]
    report_path = output_dir / f"{case_name}_report.json"

    report_data = {
        "case_name": case_name,
        "evaluation_time": datetime.now().isoformat(),
        "summary": {
            "score": evaluation_result["score"],
            "matched_count": evaluation_result["matched_count"],
            "expected_count": evaluation_result["expected_count"],
            "extra_products_count": evaluation_result["extra_products_count"],
            "coupon_score": evaluation_result.get("coupon_score", 0.0),
        },
        "query": evaluation_result.get("query", ""),
        "matched_products": evaluation_result.get("matched_products", []),
        "matched_coupons": evaluation_result.get("matched_coupons", []),
        "ground_truth_coupons": evaluation_result.get("ground_truth_coupons", []),
        "unmatched_ground_truth_products": evaluation_result.get("unmatched_ground_truth_products", []),
        "extra_products": evaluation_result.get("extra_products", []),
        "ground_truth_products": evaluation_result.get("ground_truth_products", []),
    }

    # Save all case-report content into the result
    # Optionally: update the evaluation_result with a copy as report_data
    evaluation_result["case_report"] = report_data  # this will also show up in summary if needed

    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  ❌ Failed to save report: {e}")

    return report_path


def generate_summary_report(all_results: List[Dict[str, Any]], output_dir: Path) -> Path:
    summary_path = output_dir / "summary_report.json"

    total_cases = len(all_results)
    successful_cases = sum(1 for r in all_results if r.get("case_score", 0.0) == 1.0)
    failed_cases = total_cases - successful_cases

    scores = [r.get("case_score", 0.0) for r in all_results]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    max_score = max(scores) if scores else 0.0
    min_score = min(scores) if scores else 0.0
    average_case_score = sum(r.get("case_score", 0.0) for r in all_results) / len(all_results) if all_results else 0.0

    total_matched = sum(r.get("matched_count", 0) for r in all_results)
    total_expected = sum(r.get("expected_count", 0) for r in all_results)
    total_extra = sum(r.get("extra_products_count", 0) for r in all_results)
    
    # Count incomplete cases (cases that didn't complete)
    incomplete_cases = sum(1 for r in all_results if not r.get("is_completed", True))
    incomplete_rate = incomplete_cases / total_cases if total_cases > 0 else 0.0
    # Model is valid if incomplete rate is <= 10%
    is_valid = incomplete_rate <= 0.1

    # Optionally, detailed_results can include the full evaluation_result including case_report
    summary_data = {
        "evaluation_time": datetime.now().isoformat(),
        "overall_statistics": {
            "total_cases": total_cases,
            "successful_cases": successful_cases,
            "failed_cases": failed_cases,
            "average_score": avg_score,
            "average_case_score": average_case_score,
            "max_score": max_score,
            "min_score": min_score,
            "total_matched_products": total_matched,
            "total_expected_products": total_expected,
            "total_extra_products": total_extra,
            "overall_match_rate": total_matched / total_expected if total_expected > 0 else 0.0,
            "incomplete_cases": incomplete_cases,
            "incomplete_rate": incomplete_rate,
            "valid": is_valid,
        },
        "case_results": [
            {
                "case_name": r["case_name"],
                "success": r.get("case_score", 0.0) == 1.0,
                "score": r.get("score", 0.0),
                "matched_count": r.get("matched_count", 0),
                "expected_count": r.get("expected_count", 0),
                "extra_products_count": r.get("extra_products_count", 0),
                "error": r.get("error", None),
                "case_score": r.get("case_score", 0.0),
                "is_completed": r.get("is_completed", True),
            }
            for r in all_results
        ],
        "detailed_results": all_results,
    }

    try:
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*80}")
        print(f"📊 Overall Evaluation Report")
        print(f"{'='*80}")
        print(f"  Total cases: {total_cases}")
        print(f"  Successful cases: {successful_cases}")
        print(f"  Failed cases: {failed_cases}")
        print(f"  Average score: {avg_score:.2%}")
        print(f"  Average case score: {average_case_score:.2%}")
        print(f"  Max score: {max_score:.2%}")
        print(f"  Min score: {min_score:.2%}")
        print(f"  Overall match rate: {summary_data['overall_statistics']['overall_match_rate']:.2%}")
        print(f"  Total matched products: {total_matched}/{total_expected}")
        print(f"  Total extra products: {total_extra}")
        print(f"  Incomplete cases: {incomplete_cases} ({incomplete_rate:.2%})")
        print(f"  Model valid: {is_valid} {'✅' if is_valid else '❌ (incomplete rate > 10%)'}")
        print(f"  💾 Summary report saved: {summary_path}")
        print(f"{'='*80}\n")
    except Exception as e:
        print(f"  ❌ Failed to save summary report: {e}")

    return summary_path


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate shopping agent performance.")
    parser.add_argument(
        "--database_dir",
        type=str,
        default="database_1202_wrong",
        help="Name of the database directory (under database_infered/), can be relative or absolute.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=None,
        help="Directory for evaluation report output (optional, defaults to database_dir name).",
    )
    parser.add_argument(
        "--case_filter",
        type=str,
        nargs="+",
        help="Only evaluate the specified cases (e.g. case_1 case_2), evaluate all if not specified.",
    )

    args = parser.parse_args()

    # Determine root directory (shopping_benchmark/)
    script_dir = Path(__file__).resolve().parent.parent

    # Handle database_dir (absolute or relative)
    database_dir_path = Path(args.database_dir)
    if database_dir_path.is_absolute():
        database_dir = database_dir_path
        database_dir_name = database_dir_path.name
    else:
        database_dir = script_dir / "database_infered" / args.database_dir
        database_dir_name = args.database_dir

    # If output_dir arg is not set, use database_dir name
    output_dir_name = database_dir_name if args.output_dir is None else args.output_dir

    # Output directory is always under result_report
    # Note: We'll create it only if the model is valid
    output_dir = script_dir / "result_report" / output_dir_name

    if not database_dir.exists():
        print(f"❌ Error: Database directory does not exist: {database_dir}")
        print(f"   Script dir: {script_dir}")
        print(f"   Expected path: {script_dir / 'database_infered' / args.database_dir}")
        sys.exit(1)

    # Get all case directories
    case_dirs = sorted(
        [d for d in database_dir.iterdir() if d.is_dir() and d.name.startswith("case_")]
    )

    if args.case_filter:
        case_dirs = [d for d in case_dirs if d.name in args.case_filter]

    if not case_dirs:
        print(f"⚠️  Warning: No case directories found.")
        sys.exit(1)

    print(f"🚀 Starting evaluation...")
    print(f"  Database directory: {database_dir}")
    print(f"  Output directory: {output_dir}")
    print(f"  Number of cases: {len(case_dirs)}\n")

    all_results = []
    for case_dir in case_dirs:
        try:
            result = evaluate_single_case(case_dir)
            all_results.append(result)
        except Exception as e:
            print(f"❌ Error while evaluating {case_dir.name}: {e}")
            import traceback

            traceback.print_exc()
            all_results.append(
                {
                    "case_name": case_dir.name,
                    "success": False,
                    "error": str(e),
                    "score": 0.0,
                    "is_completed": False,
                }
            )

    # Calculate if model is valid
    incomplete_cases = sum(1 for r in all_results if not r.get("is_completed", True))
    total_cases = len(all_results)
    incomplete_rate = incomplete_cases / total_cases if total_cases > 0 else 0.0
    is_valid = incomplete_rate <= 0.1

    # Always create output directory and generate reports (for debugging purposes)
    # Note: is_valid flag is still recorded in summary_report.json
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate per-case reports
    for result in all_results:
        if result.get("success"):
            generate_case_report(result, output_dir)
    
    # Generate summary report (includes is_valid flag)
    generate_summary_report(all_results, output_dir)
    
    # Print warning if model is invalid
    if not is_valid:
        print(f"\n⚠️  Warning: Model is invalid (incomplete rate {incomplete_rate:.2%} > 10%)")
        print(f"   Reports are still saved for debugging purposes.")

    print("✅ All evaluations completed!")


if __name__ == "__main__":
    main()
