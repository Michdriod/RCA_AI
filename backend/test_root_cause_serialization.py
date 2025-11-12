#!/usr/bin/env python3
"""Test that contributing_factors is omitted when empty."""

import sys
import json

sys.path.insert(0, '/Users/mac/Desktop/RCA_AI/backend')

from app.models.root_cause import RootCause

def test_contributing_factors_omitted_when_empty():
    """Test that empty contributing_factors is not in JSON output."""
    print("=" * 70)
    print("Testing RootCause Serialization")
    print("=" * 70)
    
    # Case 1: Empty factors
    rc1 = RootCause(
        summary="Test root cause without factors",
        contributing_factors=[]
    )
    json1 = rc1.model_dump()
    print("\nCase 1: Empty contributing_factors")
    print(f"  Input: contributing_factors=[]")
    print(f"  Output JSON: {json.dumps(json1, indent=2)}")
    print(f"  'contributing_factors' in output: {'contributing_factors' in json1}")
    
    # Case 2: With factors
    rc2 = RootCause(
        summary="Test root cause with factors",
        contributing_factors=["Factor 1", "Factor 2"]
    )
    json2 = rc2.model_dump()
    print("\nCase 2: With contributing_factors")
    print(f"  Input: contributing_factors=['Factor 1', 'Factor 2']")
    print(f"  Output JSON: {json.dumps(json2, indent=2)}")
    print(f"  'contributing_factors' in output: {'contributing_factors' in json2}")
    
    print("\n" + "=" * 70)
    print("Results:")
    print("=" * 70)
    
    if 'contributing_factors' not in json1:
        print("  ✓ Empty factors correctly omitted from JSON")
    else:
        print("  ✗ Empty factors still present in JSON")
    
    if 'contributing_factors' in json2 and len(json2['contributing_factors']) == 2:
        print("  ✓ Non-empty factors correctly included in JSON")
    else:
        print("  ✗ Non-empty factors missing or incorrect")
    
    print("=" * 70)

if __name__ == "__main__":
    test_contributing_factors_omitted_when_empty()
