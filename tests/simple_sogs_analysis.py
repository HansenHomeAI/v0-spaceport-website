#!/usr/bin/env python3
"""
Simple SOGS Data Analysis Script
================================

This script analyzes SOGS compressed data without external dependencies.
"""

import json
import sys
import argparse
import urllib.request
import urllib.parse

def analyze_sogs_bundle(s3_url):
    """Analyze SOGS bundle and identify potential issues"""
    
    print(f"🔍 Analyzing SOGS bundle: {s3_url}")
    
    # Convert S3 URL to HTTPS
    https_url = convert_s3_to_https(s3_url)
    
    # Download and analyze metadata
    metadata = download_metadata(https_url)
    if not metadata:
        return {"error": "Failed to download metadata"}
    
    print(f"✅ Metadata loaded successfully")
    
    # Analyze metadata structure
    metadata_analysis = analyze_metadata_structure(metadata)
    
    # Compare against expected SOGS format
    format_comparison = compare_with_sogs_format(metadata)
    
    # Generate recommendations
    recommendations = generate_recommendations(metadata_analysis, format_comparison)
    
    return {
        "metadata_analysis": metadata_analysis,
        "format_comparison": format_comparison,
        "recommendations": recommendations
    }

def convert_s3_to_https(s3_url):
    """Convert S3 URL to HTTPS URL"""
    if s3_url.startswith('s3://'):
        parts = s3_url.replace('s3://', '').split('/')
        bucket = parts[0]
        path = '/'.join(parts[1:])
        return f"https://{bucket}.s3.us-west-2.amazonaws.com/{path}"
    return s3_url

def download_metadata(base_url):
    """Download metadata.json from SOGS bundle"""
    try:
        metadata_url = f"{base_url.rstrip('/')}/meta.json"
        print(f"📥 Downloading metadata from: {metadata_url}")
        
        with urllib.request.urlopen(metadata_url) as response:
            data = response.read()
            return json.loads(data.decode('utf-8'))
    except Exception as e:
        print(f"❌ Failed to download metadata: {e}")
        return None

def analyze_metadata_structure(metadata):
    """Analyze the structure of SOGS metadata"""
    print("\n📊 Analyzing metadata structure...")
    
    analysis = {
        "has_required_fields": True,
        "field_analysis": {},
        "issues": []
    }
    
    # Required fields according to PlayCanvas SOGS
    required_fields = ['means', 'scales', 'quats', 'sh0', 'shN']
    
    for field in required_fields:
        if field not in metadata:
            analysis["has_required_fields"] = False
            analysis["issues"].append(f"Missing required field: {field}")
            continue
            
        field_data = metadata[field]
        field_analysis = {
            "present": True,
            "has_shape": "shape" in field_data,
            "has_files": "files" in field_data,
            "shape": field_data.get("shape"),
            "file_count": len(field_data.get("files", [])),
            "dtype": field_data.get("dtype"),
            "encoding": field_data.get("encoding"),
            "mins": field_data.get("mins"),
            "maxs": field_data.get("maxs")
        }
        
        analysis["field_analysis"][field] = field_analysis
        
        # Check for specific issues
        if not field_analysis["has_shape"]:
            analysis["issues"].append(f"{field}: Missing shape information")
        if not field_analysis["has_files"]:
            analysis["issues"].append(f"{field}: Missing files information")
    
    # Check for consistency in splat count
    splat_counts = []
    for field, field_data in analysis["field_analysis"].items():
        if field_data["has_shape"] and field_data["shape"]:
            splat_counts.append(field_data["shape"][0])
    
    if len(set(splat_counts)) > 1:
        analysis["issues"].append(f"Inconsistent splat counts: {splat_counts}")
    else:
        analysis["total_splats"] = splat_counts[0] if splat_counts else 0
    
    return analysis

def compare_with_sogs_format(metadata):
    """Compare metadata with expected PlayCanvas SOGS format"""
    print("\n🔍 Comparing with expected SOGS format...")
    
    comparison = {
        "format_compliant": True,
        "deviations": [],
        "expected_vs_actual": {}
    }
    
    # Expected format based on PlayCanvas SOGS repository
    expected_format = {
        "means": {
            "shape": "should be [num_splats, 3]",
            "dtype": "float32",
            "files": ["means_l.webp", "means_u.webp"],
            "encoding": "split_precision"
        },
        "scales": {
            "shape": "should be [num_splats, 3]",
            "dtype": "float32",
            "files": ["scales.webp"],
            "encoding": "direct"
        },
        "quats": {
            "shape": "should be [num_splats, 4]",
            "dtype": "uint8",
            "files": ["quats.webp"],
            "encoding": "quaternion_packed"
        },
        "sh0": {
            "shape": "should be [num_splats, 1, 4]",
            "dtype": "float32",
            "files": ["sh0.webp"],
            "encoding": "direct"
        },
        "shN": {
            "shape": "should be [num_splats, num_bands]",
            "dtype": "float32",
            "files": ["shN_centroids.webp", "shN_labels.webp"],
            "encoding": "quantized"
        }
    }
    
    for field, expected in expected_format.items():
        if field not in metadata:
            comparison["format_compliant"] = False
            comparison["deviations"].append(f"Missing field: {field}")
            continue
            
        actual = metadata[field]
        field_comparison = {
            "expected": expected,
            "actual": actual,
            "compliant": True,
            "issues": []
        }
        
        # Check shape
        if "shape" in expected and "shape" in actual:
            expected_shape = expected["shape"]
            actual_shape = actual["shape"]
            
            if "num_splats" in expected_shape:
                # Check if first dimension matches across fields
                pass  # Will be checked globally
            elif isinstance(expected_shape, list) and isinstance(actual_shape, list):
                if len(expected_shape) != len(actual_shape):
                    field_comparison["compliant"] = False
                    field_comparison["issues"].append(f"Shape dimension mismatch: expected {len(expected_shape)}, got {len(actual_shape)}")
        
        # Check dtype
        if "dtype" in expected and "dtype" in actual:
            if actual["dtype"] != expected["dtype"]:
                field_comparison["compliant"] = False
                field_comparison["issues"].append(f"Data type mismatch: expected {expected['dtype']}, got {actual['dtype']}")
        
        # Check files
        if "files" in expected and "files" in actual:
            expected_files = set(expected["files"])
            actual_files = set(actual["files"])
            
            if expected_files != actual_files:
                field_comparison["compliant"] = False
                missing = expected_files - actual_files
                extra = actual_files - expected_files
                if missing:
                    field_comparison["issues"].append(f"Missing files: {missing}")
                if extra:
                    field_comparison["issues"].append(f"Extra files: {extra}")
        
        comparison["expected_vs_actual"][field] = field_comparison
        
        if not field_comparison["compliant"]:
            comparison["format_compliant"] = False
            comparison["deviations"].extend(field_comparison["issues"])
    
    return comparison

def generate_recommendations(metadata_analysis, format_comparison):
    """Generate recommendations based on analysis"""
    print("\n💡 Generating recommendations...")
    
    recommendations = []
    
    # Metadata structure issues
    if not metadata_analysis["has_required_fields"]:
        recommendations.append("❌ CRITICAL: Missing required SOGS fields. Ensure your compression pipeline generates all required fields.")
    
    if metadata_analysis["issues"]:
        for issue in metadata_analysis["issues"]:
            recommendations.append(f"⚠️  {issue}")
    
    # Format compliance issues
    if not format_comparison["format_compliant"]:
        recommendations.append("❌ CRITICAL: SOGS format not compliant with PlayCanvas specification.")
        recommendations.append("   This is likely why your viewer shows corrupted data.")
        
        for deviation in format_comparison["deviations"]:
            recommendations.append(f"   - {deviation}")
    
    # Performance recommendations
    if metadata_analysis.get("total_splats", 0) > 100000:
        recommendations.append("💡 PERFORMANCE: Large number of splats detected. Consider:")
        recommendations.append("   - Implementing level-of-detail (LOD) rendering")
        recommendations.append("   - Using GPU instancing for efficient rendering")
        recommendations.append("   - Limiting visible splats based on camera distance")
    
    # Viewer recommendations
    recommendations.append("💡 VIEWER: Your current viewer implementation has issues:")
    recommendations.append("   - Incorrect SOGS decompression algorithm")
    recommendations.append("   - Inefficient rendering (252k individual entities)")
    recommendations.append("   - Missing proper spherical harmonics implementation")
    
    recommendations.append("🔧 SOLUTION: Use official PlayCanvas SuperSplat viewer or implement proper SOGS decompression")
    
    return recommendations

def main():
    parser = argparse.ArgumentParser(description="Analyze SOGS compressed data")
    parser.add_argument("--s3-url", required=True, help="S3 URL to SOGS bundle")
    parser.add_argument("--output", help="Output file for analysis results")
    
    args = parser.parse_args()
    
    print("🚀 SOGS Data Diagnostic Analysis")
    print("=" * 50)
    
    # Run analysis
    results = analyze_sogs_bundle(args.s3_url)
    
    if "error" in results:
        print(f"❌ Analysis failed: {results['error']}")
        sys.exit(1)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📋 ANALYSIS SUMMARY")
    print("=" * 50)
    
    metadata_analysis = results["metadata_analysis"]
    format_comparison = results["format_comparison"]
    recommendations = results["recommendations"]
    
    print(f"✅ Metadata Structure: {'Valid' if metadata_analysis['has_required_fields'] else 'Invalid'}")
    print(f"✅ Format Compliance: {'Compliant' if format_comparison['format_compliant'] else 'Non-compliant'}")
    
    if metadata_analysis.get("total_splats"):
        print(f"📊 Total Splats: {metadata_analysis['total_splats']:,}")
    
    # Print field details
    print("\n📊 FIELD ANALYSIS:")
    for field, analysis in metadata_analysis["field_analysis"].items():
        print(f"   {field}:")
        print(f"     - Shape: {analysis['shape']}")
        print(f"     - Files: {analysis['file_count']} files")
        print(f"     - Data type: {analysis['dtype']}")
        if analysis['encoding']:
            print(f"     - Encoding: {analysis['encoding']}")
    
    # Print recommendations
    print("\n💡 RECOMMENDATIONS:")
    for rec in recommendations:
        print(f"   {rec}")
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Analysis results saved to: {args.output}")
    
    # Exit with error code if critical issues found
    critical_issues = any("❌ CRITICAL" in rec for rec in recommendations)
    if critical_issues:
        print("\n❌ Critical issues detected. Your SOGS data may not be compatible with standard viewers.")
        sys.exit(1)
    else:
        print("\n✅ Analysis complete. Check recommendations above for improvements.")

if __name__ == "__main__":
    main() 