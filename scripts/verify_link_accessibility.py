
import sys
import re

def verify_link_accessibility():
    print("Verifying link accessibility code compliance...")
    
    # 1. Scrape source files
    files_to_check = [
        "app.py",
        "src/ui/results_cards.py"
    ]
    
    found_issues = []
    
    for fpath in files_to_check:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Check for Forbidden "Selected:" replacing title pattern
            # We look for something like 'if is_sel: st.info(f"Selected: ...")'
            # Or simplified regex for "Selected: {item" 
            
            # This regex looks for string literals starting with "Selected: " inside st calls
            # It's a heuristic.
            if re.search(r'Selected:\s*\{[^}]*title', content):
                found_issues.append(f"{fpath}: Found 'Selected: {{title}}' pattern which suggests replacing title.")
                
            if re.search(r'Selected:\s*["\']\s*\+\s*item', content):
                 found_issues.append(f"{fpath}: Found 'Selected: ' + item pattern.")

        except FileNotFoundError:
            # src/ui/results_cards.py might not exist yet, which is fine first run
            if fpath != "src/ui/results_cards.py":
                found_issues.append(f"{fpath}: File not found.")

    if found_issues:
        for i in found_issues:
            print(f"[FAIL] {i}")
        sys.exit(1)
        
    print("[OK] No forbidden 'Selected:' title replacement patterns found.")
    sys.exit(0)

if __name__ == "__main__":
    verify_link_accessibility()
