import re

# --- Apollo.io jaise static ranges ---

EMPLOYEE_RANGES = [
    ('', 'Any Employees'),
    ('1-10', '1-10'),
    ('11-50', '11-50'),
    ('51-200', '51-200'),
    ('201-500', '201-500'),
    ('501-1000', '501-1,000'),
    ('1001-5000', '1,001-5,000'),
    ('5001-10000', '5,001-10,000'),
    ('10001+', '10,001+'),
]

REVENUE_RANGES = [
    ('', 'Any Revenue'),
    ('$0-1M', '$0-1M'),
    ('$1M-5M', '$1M-5M'),
    ('$5M-10M', '$5M-10M'),
    ('$10M-25M', '$10M-25M'),
    ('$25M-50M', '$25M-50M'),
    ('$50M-100M', '$50M-100M'),
    ('$100M-500M', '$100M-500M'),
    ('$500M-1B', '$500M-1B'),
    ('$1B+', '$1B+'),
]


def parse_value(value_str):
    """
    Ek string (jaise '$10M' ya '5,000') ko ek number mein convert karta hai.
    """
    if not value_str:
        return 0
    
    # Comma, dollar sign, aur spaces ko hata dein
    value_str = str(value_str).strip().upper()
    value_str = re.sub(r'[,\$ ]', '', value_str)
    
    if 'B' in value_str:
        num_str = re.sub(r'B', '', value_str)
        num = float(num_str) if num_str else 0
        return int(num * 1_000_000_000)
    if 'M' in value_str:
        num_str = re.sub(r'M', '', value_str)
        num = float(num_str) if num_str else 0
        return int(num * 1_000_000)
    if 'K' in value_str:
        num_str = re.sub(r'K', '', value_str)
        num = float(num_str) if num_str else 0
        return int(num * 1_000)
    
    try:
        # Number ke alawa kuch bhi ho (jaise 'abc') toh 0 return karein
        return int(float(value_str))
    except ValueError:
        return 0

def parse_range_to_tuple(range_str):
    """
    Ek range string (jaise '51-200' ya '$1M-5M' ya '10001+') ko (min, max) tuple mein convert karta hai.
    """
    if not range_str:
        return (None, None)

    range_str = str(range_str).strip()
    
    # Plus (+) notation ke liye (e.g., '10001+')
    if range_str.endswith('+'):
        min_val_str = range_str[:-1]
        min_val = parse_value(min_val_str)
        return (min_val, float('inf')) # max = infinity

    # Range notation ke liye (e.g., '51-200' or '$1M-5M')
    if '-' in range_str:
        parts = range_str.split('-')
        if len(parts) == 2:
            min_val = parse_value(parts[0])
            max_val = parse_value(parts[1])
            # Agar range galat likhi ho (e.g., "500-200")
            return (min(min_val, max_val), max(min_val, max_val))
            
    # Single value ke liye (e.g., '100' or '$5M')
    val = parse_value(range_str)
    if val is None:
        return (None, None)
    return (val, val) # min aur max same hain

def check_range_overlap(filter_range_str, db_value_str):
    """
    Do range strings ko compare karta hai aur check karta hai agar woh overlap karte hain.
    filter_range_str: User ne jo select kiya (e.g., '51-200')
    db_value_str: Database mein jo value hai (e.g., '100' or '75-150')
    """
    if not filter_range_str or not db_value_str:
        return False
        
    try:
        # Filter range ko parse karein (e.g., '51-200')
        f_min, f_max = parse_range_to_tuple(filter_range_str)
        
        # Database value ko parse karein (e.g., '100' or '75-150')
        db_min, db_max = parse_range_to_tuple(db_value_str)

        # Agar parsing fail hui (invalid text)
        if f_min is None or db_min is None:
            return False

        # Overlap logic: (StartA <= EndB) and (EndA >= StartB)
        return (f_min <= db_max) and (f_max >= db_min)

    except Exception as e:
        print(f"Error checking range overlap ({filter_range_str} vs {db_value_str}): {e}")
        return False