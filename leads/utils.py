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
    
    # Handle B (Billion)
    if 'B' in value_str:
        num_str = re.sub(r'[B+]', '', value_str)
        try:
            num = float(num_str) if num_str else 0
            return int(num * 1_000_000_000)
        except ValueError:
            return 0
    
    # Handle M (Million)
    if 'M' in value_str:
        num_str = re.sub(r'[M+]', '', value_str)
        try:
            num = float(num_str) if num_str else 0
            return int(num * 1_000_000)
        except ValueError:
            return 0
    
    # Handle K (Thousand)
    if 'K' in value_str:
        num_str = re.sub(r'[K+]', '', value_str)
        try:
            num = float(num_str) if num_str else 0
            return int(num * 1_000)
        except ValueError:
            return 0
    
    # Handle + at the end (remove it)
    value_str = value_str.rstrip('+')
    
    try:
        return int(float(value_str))
    except (ValueError, TypeError):
        return 0


def parse_range_to_tuple(range_str):
    """
    Ek range string ko (min, max) tuple mein convert karta hai.
    Examples:
    - '51-200' -> (51, 200)
    - '$1M-5M' -> (1000000, 5000000)
    - '10001+' -> (10001, inf)
    - '100' -> (100, 100)
    """
    if not range_str:
        return (None, None)

    range_str = str(range_str).strip()
    
    # Plus (+) notation ke liye (e.g., '10001+')
    if range_str.endswith('+'):
        min_val_str = range_str[:-1]
        min_val = parse_value(min_val_str)
        return (min_val, float('inf'))

    # Range notation ke liye (e.g., '51-200' or '$1M-5M')
    if '-' in range_str:
        parts = range_str.split('-', 1)  # Only split once
        if len(parts) == 2:
            min_val = parse_value(parts[0])
            max_val = parse_value(parts[1])
            # Ensure min <= max
            return (min(min_val, max_val), max(min_val, max_val))
    
    # Single value ke liye (e.g., '100' or '$5M')
    val = parse_value(range_str)
    if val == 0:
        return (None, None)
    return (val, val)


def check_range_overlap(filter_range_str, db_value_str):
    """
    Do range strings ko compare karta hai aur check karta hai agar woh overlap karte hain.
    
    Args:
        filter_range_str: User ne jo select kiya (e.g., '51-200')
        db_value_str: Database mein jo value hai (e.g., '100' or '75-150')
    
    Returns:
        bool: True if ranges overlap, False otherwise
    """
    if not filter_range_str or not db_value_str:
        return False
    
    try:
        # Filter range ko parse karein
        f_min, f_max = parse_range_to_tuple(filter_range_str)
        
        # Database value ko parse karein
        db_min, db_max = parse_range_to_tuple(db_value_str)
        
        # Agar koi bhi value None hai toh False return karein
        if f_min is None or db_min is None:
            return False
        
        # Overlap logic: (StartA <= EndB) and (EndA >= StartB)
        return (f_min <= db_max) and (f_max >= db_min)
    
    except Exception as e:
        print(f"Error in check_range_overlap({filter_range_str}, {db_value_str}): {e}")
        return False


def check_multiple_ranges(filter_ranges_list, db_value_str):
    """
    Multiple filter ranges mein se kisi ek se bhi match ho toh True return karta hai.
    
    Args:
        filter_ranges_list: List of filter range strings (e.g., ['51-200', '501-1000'])
        db_value_str: Database value string (e.g., '150')
    
    Returns:
        bool: True if any filter range matches, False otherwise
    """
    if not filter_ranges_list or not db_value_str:
        return False
    
    for filter_range in filter_ranges_list:
        if check_range_overlap(filter_range, db_value_str):
            return True
    
    return False