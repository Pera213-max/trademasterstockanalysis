import redis
import os

try:
    # Connect to Redis
    r = redis.Redis(host='trademaster-redis', password='FIgfgjifjgIKSJvfvRDEWTYT!GHUgiui_GFYf', decode_responses=True)
    
    # Define patterns to clear (only analysis/fundamentals, keep history)
    patterns = [
        'fi:analysis:*', 
        'fi:fundamentals:*', 
        'fi:rankings*', 
        'fi:quick:*', 
        'fi:potential:*', 
        'fi:movers*',
        'fi:screener*'
    ]
    
    keys = []
    for p in patterns:
        found = r.keys(p)
        if found:
            keys.extend(found)
            print(f"Found {len(found)} keys for pattern {p}")
    
    if keys:
        print(f"Deleting total {len(keys)} keys...")
        # Delete explicitly in batches to be safe or all at once
        r.delete(*keys)
        print("Successfully deleted specific cache keys.")
    else:
        print("No matching keys found to delete.")
        
except Exception as e:
    print(f"Error clearing cache: {e}")
