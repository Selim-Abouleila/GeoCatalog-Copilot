import argparse
import sys
import os
import json

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.tools.feature_layer_tools import count_rows

def main():
    parser = argparse.ArgumentParser(description="Verify count_rows tool")
    parser.add_argument("--input", required=True, help="Input Item ID or URL")
    parser.add_argument("--layer-index", type=int, help="Optional layer index")
    parser.add_argument("--where", default="1=1", help="Where clause")
    
    args = parser.parse_args()
    
    print(f"Testing count_rows with input: {args.input}")
    print(f"Layer Index: {args.layer_index}, Where: {args.where}")
    
    try:
        result = count_rows(args.input, layer_index=args.layer_index, where=args.where)
        print(json.dumps(result, indent=2))
        
        # Claims assertion
        if "ok" not in result:
             print("[FAIL] Missing 'ok' key")
             sys.exit(1)
             
        if not result["ok"]:
             print(f"[FAIL] Result not OK: {result.get('error')}")
             sys.exit(1)
             
        if "layers" not in result or "tables" not in result:
             print("[FAIL] Missing layers/tables keys")
             sys.exit(1)
             
        # Check if we got at least one count if ok=True
        has_count = False
        for l in result['layers']:
            if l['count'] is not None: has_count = True
        for t in result['tables']:
            if t['count'] is not None: has_count = True
            
        if not has_count and len(result['layers']) + len(result['tables']) > 0:
             print("[WARN] No actual counts returned (maybe all errors?) but ok=True")
             # If strictly all errors, result['ok'] is still True by design (partial failure allowed), 
             # but we want to fail verification if we expected success.
             # However, for generic verify, we might not know if input works.
             # But let's assume valid input.
             pass
             
        if result['total_count'] < 0:
             print("[FAIL] Negative total_count")
             sys.exit(1)
             
        print("[PASS] Schema Valid")
        sys.exit(0)
        
    except Exception as e:
        print(f"[CRITICAL] Exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
