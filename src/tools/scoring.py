def quality_score(item_dict):
    """
    Calculates a quality score for an ArcGIS item based on its metadata.
    
    Args:
        item_dict (dict): The item dictionary returned by search_items.
        
    Returns:
        int: A score between 0 and 100.
    """
    score = 0
    
    # 1. Title check (shouldn't be empty, effectively guaranteed by search but good to check)
    if item_dict.get('title'):
        score += 20
        
    # 2. Snippet (summary) check
    if item_dict.get('snippet'):
        score += 30
        
    # 3. Description check
    if item_dict.get('description'):
        score += 30
        
    # 4. Tags check
    tags = item_dict.get('tags', [])
    if tags:
        score += 10
        if len(tags) >= 3:
            score += 10
            
    return min(score, 100)
