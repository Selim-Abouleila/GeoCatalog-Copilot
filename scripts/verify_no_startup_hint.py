
import sys

def verify_no_startup_hint():
    target_string = "Try: 'count rows"
    file_path = "app.py"
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        if target_string in content:
            print(f"[FAIL] Found forbidden string: \"{target_string}\" in {file_path}")
            sys.exit(1)
        else:
            print(f"[OK] Forbidden string \"{target_string}\" not found.")
            sys.exit(0)
            
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_no_startup_hint()
