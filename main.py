#!/usr/bin/env python3
"""
Auto Form Fill - Main Orchestrator
Handles end-to-end workflow for form filling automation.
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Import modules
try:
    from calibrator import match_template
    from ocr.extractor import extract_data_from_image
    from filler import fill_form
    from printer import save_filled_form
except ImportError as e:
    print(f"ERROR: Failed to import required modules: {e}")
    print("Ensure all modules (calibrator, ocr.extractor, filler, printer) are available.")
    sys.exit(1)


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load and parse JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}")


def validate_template(template: Dict[str, Any]) -> None:
    """Validate template structure."""
    if 'fields' not in template:
        raise ValueError("Template missing 'fields' key")
    if not isinstance(template['fields'], list):
        raise ValueError("Template 'fields' must be a list")
    
    for i, field in enumerate(template['fields']):
        if not isinstance(field, dict):
            raise ValueError(f"Field {i} must be a dictionary")
        if 'name' not in field:
            raise ValueError(f"Field {i} missing 'name' key")
        if 'pixel_bbox' not in field:
            raise ValueError(f"Field {i} missing 'pixel_bbox' key")


def merge_data(extracted_data: Dict[str, str], override_data: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Merge extracted data with user overrides."""
    merged = extracted_data.copy()
    if override_data:
        merged.update(override_data)
    return merged


def main():
    """Main orchestrator function."""
    parser = argparse.ArgumentParser(
        description="Auto Form Fill - Extract data from forms and fill them automatically",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--image', 
        required=True, 
        help='Path to input form image'
    )
    parser.add_argument(
        '--template', 
        required=True, 
        help='Path to template JSON file'
    )
    parser.add_argument(
        '--output', 
        required=True, 
        help='Path for output filled form (PDF or image)'
    )
    parser.add_argument(
        '--data', 
        help='Path to JSON file with data overrides'
    )
    parser.add_argument(
        '--debug', 
        action='store_true', 
        help='Enable debug mode for OCR processing'
    )
    
    args = parser.parse_args()
    
    print("🚀 Starting Auto Form Fill workflow...")
    
    # Step 1: Validate input files
    print("📋 Step 1: Validating input files...")
    
    if not os.path.exists(args.image):
        print(f"❌ ERROR: Image file not found: {args.image}")
        sys.exit(1)
    
    if not os.path.exists(args.template):
        print(f"❌ ERROR: Template file not found: {args.template}")
        sys.exit(1)
    
    if args.data and not os.path.exists(args.data):
        print(f"❌ ERROR: Data file not found: {args.data}")
        sys.exit(1)
    
    print("✅ Input files validated")
    
    # Step 2: Load template
    print("📄 Step 2: Loading template...")
    
    try:
        # Try to match template automatically first
        if hasattr(match_template, '__call__'):
            print("🔍 Attempting automatic template matching...")
            try:
                template = match_template(args.image)
                print("✅ Template matched automatically")
            except Exception as e:
                print(f"⚠️  Automatic matching failed: {e}")
                print("📁 Loading template from specified path...")
                template = load_json_file(args.template)
        else:
            print("📁 Loading template from specified path...")
            template = load_json_file(args.template)
        
        validate_template(template)
        print(f"✅ Template loaded successfully with {len(template['fields'])} fields")
        
    except Exception as e:
        print(f"❌ ERROR: Failed to load template: {e}")
        sys.exit(1)
    
    # Step 3: Extract data from image
    print("🔍 Step 3: Extracting data from image...")
    
    try:
        extracted_data = extract_data_from_image(args.image, template)
        print(f"✅ Data extraction completed. Found {len(extracted_data)} fields:")
        
        for field_name, value in extracted_data.items():
            display_value = value[:50] + "..." if len(value) > 50 else value
            print(f"   • {field_name}: '{display_value}'")
            
    except Exception as e:
        print(f"❌ ERROR: Data extraction failed: {e}")
        sys.exit(1)
    
    # Step 4: Load and merge override data
    print("🔄 Step 4: Processing data overrides...")
    
    override_data = None
    if args.data:
        try:
            override_data = load_json_file(args.data)
            print(f"✅ Loaded {len(override_data)} override values")
            for key, value in override_data.items():
                print(f"   • {key}: '{value}'")
        except Exception as e:
            print(f"❌ ERROR: Failed to load override data: {e}")
            sys.exit(1)
    else:
        print("ℹ️  No override data provided")
    
    # Merge data
    final_data = merge_data(extracted_data, override_data)
    print(f"✅ Data merged successfully. Final dataset has {len(final_data)} fields")
    
    # Step 5: Fill form
    print("✏️  Step 5: Filling form...")
    
    try:
        filled_image = fill_form(args.image, template, final_data)
        print("✅ Form filled successfully")
        
    except Exception as e:
        print(f"❌ ERROR: Form filling failed: {e}")
        sys.exit(1)
    
    # Step 6: Save output
    print("💾 Step 6: Saving filled form...")
    
    try:
        # Create output directory if it doesn't exist
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        save_filled_form(filled_image, str(output_path))
        print(f"✅ Filled form saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ ERROR: Failed to save output: {e}")
        sys.exit(1)
    
    # Success summary
    print("\n🎉 Auto Form Fill completed successfully!")
    print(f"📊 Summary:")
    print(f"   • Input image: {args.image}")
    print(f"   • Template: {args.template}")
    print(f"   • Fields processed: {len(final_data)}")
    print(f"   • Output saved: {args.output}")
    
    if override_data:
        print(f"   • Override values: {len(override_data)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        sys.exit(1)