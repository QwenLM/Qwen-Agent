#!/usr/bin/env python3
"""
Aggregate results across Shopping and Travel Planning benchmarks
Calculates overall scores by averaging across domains
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


def load_shopping_statistics(domain_dir: Path, model_name: str) -> Optional[Dict[str, Any]]:
    """
    Load statistics for shopping domain
    
    Args:
        domain_dir: Path to shoppingplanning directory
        model_name: Model name
        
    Returns:
        Statistics dictionary with match_rate and weighted_average_case_score
    """
    stats_file = domain_dir / "result_report" / f"{model_name}_statistics.json"
    
    if not stats_file.exists():
        print(f"⚠️  Warning: Shopping statistics file not found: {stats_file}")
        return None
    
    try:
        with open(stats_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract the metrics we need
        total = data.get("total", {})
        return {
            "total": {
                "total_cases": total.get("total_cases", 0),
                "successful_cases": total.get("successful_cases", 0),
                "successful_rate": total.get("successful_rate", 0.0),
                "match_rate": total.get("match_rate", 0.0),  # Main metric for shopping
                "weighted_average_case_score": total.get("weighted_average_case_score", 0.0),  # Main metric for shopping
                "valid": total.get("valid", False),
                "levels_completed": total.get("levels_completed", [])
            }
        }
    except Exception as e:
        print(f"❌ Error loading shopping statistics {stats_file}: {e}")
        return None


def load_travel_statistics(domain_dir: Path, model_name: str, output_dir: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Load statistics for travel domain
    
    Reads evaluation_summary.json for both zh and en languages,
    then calculates average scores.
    
    Args:
        domain_dir: Path to travelplanning directory
        model_name: Model name
        output_dir: Optional custom output directory for travel results
        
    Returns:
        Statistics dictionary with composite_score (as match_rate) and case_acc (as weighted_average_case_score)
    """
    languages = ["zh", "en"]
    language_results = {}
    
    # Determine the results directory
    if output_dir:
        results_base = Path(output_dir)
    else:
        results_base = domain_dir / "results"
    
    for lang in languages:
        summary_file = results_base / f"{model_name}_{lang}" / "evaluation" / "evaluation_summary.json"
        
        if not summary_file.exists():
            print(f"⚠️  Warning: Travel evaluation summary not found for {lang}: {summary_file}")
            continue
        
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metrics = data.get("metrics", {})
            language_results[lang] = {
                "composite_score": metrics.get("composite_score", 0.0),
                "case_acc": metrics.get("case_acc", 0.0),
                "commonsense_score": metrics.get("commonsense_score", 0.0),
                "personalized_score": metrics.get("personalized_score", 0.0),
                "total_test_samples": data.get("total_test_samples", 0),
                "evaluation_success_count": data.get("evaluation_success_count", 0)
            }
        except Exception as e:
            print(f"⚠️  Warning: Error loading travel statistics for {lang}: {e}")
            continue
    
    if not language_results:
        print(f"⚠️  Warning: No travel statistics found for model {model_name}")
        return None
    
    # Calculate average across languages
    num_languages = len(language_results)
    avg_composite_score = sum(r["composite_score"] for r in language_results.values()) / num_languages
    avg_case_acc = sum(r["case_acc"] for r in language_results.values()) / num_languages
    avg_commonsense_score = sum(r["commonsense_score"] for r in language_results.values()) / num_languages
    avg_personalized_score = sum(r["personalized_score"] for r in language_results.values()) / num_languages
    
    # Calculate total cases
    total_cases = sum(r["total_test_samples"] for r in language_results.values())
    successful_cases = sum(r["evaluation_success_count"] for r in language_results.values())
    successful_rate = successful_cases / total_cases if total_cases > 0 else 0.0
    
    return {
        "total": {
            "total_cases": total_cases,
            "successful_cases": successful_cases,
            "successful_rate": successful_rate,
            "match_rate": avg_composite_score,  # composite_score as match_rate
            "weighted_average_case_score": avg_case_acc,  # case_acc as weighted_average_case_score
            "commonsense_score": avg_commonsense_score,  # Average commonsense_score
            "personalized_score": avg_personalized_score,  # Average personalized_score
            "valid": True,  # Assume valid if we have results
            "levels_completed": list(language_results.keys())  # Languages completed
        },
        "language_details": language_results  # Keep language-specific details
    }


def aggregate_model_results(model_name: str, project_root: Path, travel_output_dir: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Aggregate results for a model across all domains
    
    Args:
        model_name: Model name
        project_root: Project root directory
        travel_output_dir: Optional custom output directory for travel results
        
    Returns:
        Aggregated results dictionary
    """
    # Load statistics from each domain
    shopping_stats = load_shopping_statistics(project_root / "shoppingplanning", model_name)
    travel_stats = load_travel_statistics(project_root / "travelplanning", model_name)
    
    # Check if we have at least one domain's results
    domains_found = []
    if shopping_stats:
        domains_found.append("shopping")
    if travel_stats:
        domains_found.append("travel")
    
    if not domains_found:
        print(f"❌ Error: No statistics found for model {model_name}")
        return None
    
    print(f"✓ Found statistics for domains: {', '.join(domains_found)}")
    
    # Prepare aggregated results
    aggregated = {
        "model_name": model_name,
        "aggregation_time": datetime.now().isoformat(),
        "domains": {},
        "overall": {}
    }
    
    # Add domain-specific results
    if shopping_stats:
        aggregated["domains"]["shopping"] = {
            "total_cases": shopping_stats["total"]["total_cases"],
            "successful_cases": shopping_stats["total"]["successful_cases"],
            "successful_rate": shopping_stats["total"]["successful_rate"],
            "match_rate": shopping_stats["total"]["match_rate"],
            "weighted_average_case_score": shopping_stats["total"]["weighted_average_case_score"],
            "valid": shopping_stats["total"]["valid"],
            "levels_completed": shopping_stats["total"]["levels_completed"]
        }
    
    if travel_stats:
        travel_domain_data = {
            "total_cases": travel_stats["total"]["total_cases"],
            "successful_cases": travel_stats["total"]["successful_cases"],
            "successful_rate": travel_stats["total"]["successful_rate"],
            "composite_score": travel_stats["total"]["match_rate"],  # Average composite_score across zh and en
            "case_acc": travel_stats["total"]["weighted_average_case_score"],  # Average case_acc across zh and en
            "commonsense_score": travel_stats["total"]["commonsense_score"],  # Average commonsense_score across zh and en
            "personalized_score": travel_stats["total"]["personalized_score"],  # Average personalized_score across zh and en
            "valid": travel_stats["total"]["valid"],
            "languages_completed": travel_stats["total"]["levels_completed"]  # Languages: ["zh", "en"]
        }
        # Add language-specific details if available
        if "language_details" in travel_stats:
            travel_domain_data["language_details"] = travel_stats["language_details"]
        aggregated["domains"]["travel"] = travel_domain_data
    
    # Calculate overall averages across domains
    num_domains = len(domains_found)
    
    # Collect metrics for averaging
    total_cases = 0
    successful_cases = 0
    successful_rates = []
    
    # Domain-specific metrics
    shopping_match_rate = None
    shopping_weighted_score = None
    travel_composite_score = None
    travel_case_acc = None
    travel_commonsense_score = None
    travel_personalized_score = None
    
    all_valid = True
    
    for domain in domains_found:
        domain_stats = shopping_stats if domain == "shopping" else travel_stats
        total_cases += domain_stats["total"]["total_cases"]
        successful_cases += domain_stats["total"]["successful_cases"]
        successful_rates.append(domain_stats["total"]["successful_rate"])
        all_valid = all_valid and domain_stats["total"]["valid"]
        
        # Store domain-specific metrics
        if domain == "shopping":
            shopping_match_rate = domain_stats["total"]["match_rate"]
            shopping_weighted_score = domain_stats["total"]["weighted_average_case_score"]
        elif domain == "travel":
            travel_composite_score = domain_stats["total"]["match_rate"]  # This is avg composite_score
            travel_case_acc = domain_stats["total"]["weighted_average_case_score"]  # This is avg case_acc
            travel_commonsense_score = domain_stats["total"]["commonsense_score"]  # This is avg commonsense_score
            travel_personalized_score = domain_stats["total"]["personalized_score"]  # This is avg personalized_score
    
    # Calculate overall metrics
    aggregated["overall"] = {
        "total_cases": total_cases,
        "successful_cases": successful_cases,
        "successful_rate": sum(successful_rates) / num_domains,
        "valid": all_valid,
        "domains_completed": domains_found,
        "num_domains": num_domains
    }
    
    # Add domain-specific metrics to overall
    if shopping_match_rate is not None:
        aggregated["overall"]["shopping_match_rate"] = shopping_match_rate
        aggregated["overall"]["shopping_weighted_average_case_score"] = shopping_weighted_score
    
    if travel_composite_score is not None:
        aggregated["overall"]["travel_composite_score"] = travel_composite_score
        aggregated["overall"]["travel_case_acc"] = travel_case_acc
        aggregated["overall"]["travel_commonsense_score"] = travel_commonsense_score
        aggregated["overall"]["travel_personalized_score"] = travel_personalized_score
    
    # Calculate cross-domain averages (if both domains exist)
    if shopping_match_rate is not None and travel_composite_score is not None:
        # avg_acc: average of shopping weighted_average_case_score and travel case_acc
        aggregated["overall"]["avg_acc"] = (shopping_weighted_score + travel_case_acc) / 2
    
    return aggregated


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Aggregate results across domains")
    parser.add_argument(
        "--model_name",
        type=str,
        required=True,
        help="Model name to aggregate results for"
    )
    parser.add_argument(
        "--travel-output-dir",
        type=str,
        default=None,
        help="Custom output directory for travel domain results (optional)"
    )
    
    args = parser.parse_args()
    
    # Get project root directory
    project_root = Path(__file__).resolve().parent
    
    print(f"\n{'='*80}")
    print(f"📊 Aggregating Results for Model: {args.model_name}")
    print(f"{'='*80}\n")
    
    # Aggregate results
    aggregated = aggregate_model_results(args.model_name, project_root, args.travel_output_dir)
    
    if aggregated is None:
        print(f"❌ Failed to aggregate results for model {args.model_name}")
        sys.exit(1)
    
    # Save aggregated results
    output_dir = project_root / "aggregated_results"
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"{args.model_name}_aggregated.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(aggregated, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Aggregated results saved to: {output_file}\n")
        
        # Print summary
        print(f"{'='*80}")
        print(f"📊 Summary for {args.model_name}")
        print(f"{'='*80}")
        print(f"\nDomains completed: {', '.join(aggregated['overall']['domains_completed'])}")
        print(f"\nOverall Metrics:")
        print(f"  Total cases: {aggregated['overall']['total_cases']}")
        print(f"  Successful cases: {aggregated['overall']['successful_cases']}")
        print(f"  Successful rate: {aggregated['overall']['successful_rate']:.4f} ({aggregated['overall']['successful_rate']:.2%})")
        
        # Show cross-domain average if both domains exist
        if 'avg_acc' in aggregated['overall']:
            print(f"\nCross-Domain Metric ⭐:")
            print(f"  avg_acc (shopping weighted_score + travel case_acc) / 2: {aggregated['overall']['avg_acc']:.4f} ({aggregated['overall']['avg_acc']:.2%})")
        
        # Show individual domain metrics
        if 'shopping_match_rate' in aggregated['overall']:
            print(f"\nShopping Domain Metrics:")
            print(f"  Match rate ⭐: {aggregated['overall']['shopping_match_rate']:.4f} ({aggregated['overall']['shopping_match_rate']:.2%})")
            print(f"  Weighted average case score ⭐: {aggregated['overall']['shopping_weighted_average_case_score']:.4f} ({aggregated['overall']['shopping_weighted_average_case_score']:.2%})")
        
        if 'travel_composite_score' in aggregated['overall']:
            print(f"\nTravel Domain Metrics (averaged across zh and en):")
            print(f"  Composite score ⭐: {aggregated['overall']['travel_composite_score']:.4f} ({aggregated['overall']['travel_composite_score']:.2%})")
            print(f"  Case accuracy ⭐: {aggregated['overall']['travel_case_acc']:.4f} ({aggregated['overall']['travel_case_acc']:.2%})")
            print(f"  Commonsense score: {aggregated['overall']['travel_commonsense_score']:.4f} ({aggregated['overall']['travel_commonsense_score']:.2%})")
            print(f"  Personalized score: {aggregated['overall']['travel_personalized_score']:.4f} ({aggregated['overall']['travel_personalized_score']:.2%})")
        
        print(f"\nModel valid: {aggregated['overall']['valid']} {'✅' if aggregated['overall']['valid'] else '❌'}")
        
        print(f"\nPer-Domain Breakdown:")
        for domain, stats in aggregated['domains'].items():
            if domain == "shopping":
                print(f"  Shopping:")
                print(f"    Total cases: {stats['total_cases']}")
                print(f"    Successful rate: {stats['successful_rate']:.4f} ({stats['successful_rate']:.2%})")
                print(f"    Match rate ⭐: {stats['match_rate']:.4f} ({stats['match_rate']:.2%})")
                print(f"    Weighted average case score ⭐: {stats['weighted_average_case_score']:.4f} ({stats['weighted_average_case_score']:.2%})")
                if "levels_completed" in stats:
                    print(f"    Levels: {', '.join(map(str, stats['levels_completed']))}")
            
            elif domain == "travel":
                print(f"  Travel:")
                print(f"    Total cases: {stats['total_cases']}")
                print(f"    Successful rate: {stats['successful_rate']:.4f} ({stats['successful_rate']:.2%})")
                print(f"    Composite score (avg) ⭐: {stats['composite_score']:.4f} ({stats['composite_score']:.2%})")
                print(f"    Case accuracy (avg) ⭐: {stats['case_acc']:.4f} ({stats['case_acc']:.2%})")
                print(f"    Commonsense score (avg): {stats['commonsense_score']:.4f} ({stats['commonsense_score']:.2%})")
                print(f"    Personalized score (avg): {stats['personalized_score']:.4f} ({stats['personalized_score']:.2%})")
                
                # Show language details for travel domain
                if "language_details" in stats:
                    print(f"    Languages: {', '.join(stats['languages_completed'])}")
                    for lang, lang_stats in stats['language_details'].items():
                        print(f"      {lang.upper()}:")
                        print(f"        Composite score: {lang_stats['composite_score']:.4f}")
                        print(f"        Case accuracy: {lang_stats['case_acc']:.4f}")
                        print(f"        Commonsense score: {lang_stats['commonsense_score']:.4f}")
                        print(f"        Personalized score: {lang_stats['personalized_score']:.4f}")
        
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"❌ Failed to save aggregated results: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

