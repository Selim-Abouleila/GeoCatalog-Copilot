import hashlib
import json
import logging
import uuid
import duckdb
import requests
import concurrent.futures
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_content_hash(item: dict) -> str:
    """Computes a stable SHA256 hash of relevant item fields."""
    # usage of a few key fields that determine 'content' change
    keys_to_hash = [
        'id', 'title', 'type', 'owner', 'url', 'access',
        'tags', 'snippet', 'description', 'thumbnail', 
        'extent', 'modified'
    ]
    
    # Extract and sort to ensure stability
    data = {k: item.get(k) for k in keys_to_hash}
    
    # Serialize to JSON with sorted keys
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

def normalize_item(raw: dict, run_id: uuid.UUID) -> dict:
    """Normalizes a raw ArcGIS item dict into the DB schema format."""
    
    # 1. Basic Fields
    now_utc = datetime.now(timezone.utc)
    
    # Handle timestamps (ArcGIS uses epoch ms)
    def ms_to_datetime(ms):
        if ms:
            try:
                return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
            except:
                return None
        return None

    created = ms_to_datetime(raw.get('created'))
    modified = ms_to_datetime(raw.get('modified'))
    
    # Handle Tags
    tags = raw.get('tags', [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(',')]
    tags_json = json.dumps(tags)
    
    # Handle Extent
    # ArcGIS extent: [[xmin, ymin], [xmax, ymax]]
    extent = raw.get('extent')
    xmin = ymin = xmax = ymax = None
    has_extent = False
    
    if extent and isinstance(extent, list) and len(extent) == 2:
        try:
            xmin = float(extent[0][0])
            ymin = float(extent[0][1])
            xmax = float(extent[1][0])
            ymax = float(extent[1][1])
            has_extent = True
        except:
            pass # Malformed extent
            
    # Handle other derived fields
    snippet = raw.get('snippet') or ""
    description = raw.get('description') or ""
    thumbnail = raw.get('thumbnail')
    
    # Calculate Hash
    content_hash = generate_content_hash(raw)
    
    return {
        'item_id': raw.get('id'),
        'title': raw.get('title') or "Untitled",
        'item_type': raw.get('type') or "Unknown",
        'owner': raw.get('owner') or "Unknown",
        'url': raw.get('url'),
        'access': raw.get('access'),
        'created_at': created,
        'modified_at': modified,
        'tags_json': tags_json,
        'tags_count': len(tags),
        'snippet': snippet,
        'snippet_len': len(snippet),
        'description': description,
        'description_len': len(description),
        'thumbnail': thumbnail,
        'has_thumbnail': bool(thumbnail),
        'extent_xmin': xmin,
        'extent_ymin': ymin,
        'extent_xmax': xmax,
        'extent_ymax': ymax,
        'has_extent': has_extent,
        'has_description': bool(description),
        'num_views': raw.get('numViews', 0),
        'content_hash': content_hash,
        'last_seen_run_id': str(run_id),
        'last_seen_at': now_utc
    }

def fetch_items(gis, max_items: int, query: str = None, item_types: List[str] = None) -> List[dict]:
    """Fetches items from ArcGIS."""
    
    # Build Query
    base_query = query if query else 'access:public'
    if item_types:
        types_q = " OR ".join([f'type:"{t}"' for t in item_types])
        base_query = f"({base_query}) AND ({types_q})"
        
    logger.info(f"Fetching max {max_items} items with query: {base_query}")
    
    results = []
    
    try:
        # Paging logic using advanced_search if possible, or basic search
        # For simplicity in this implementation, we'll use search() which handles max_items internally roughly
        # usually up to 10k. 
        # advanced_search is better for deep paging but search() is simpler for the requested verification scope.
        # We will request 100 at a time manually if needed, but gis.content.search does paging.
        
        items = gis.content.search(query=base_query, max_items=max_items, outside_org=True)
        
        for item in items:
            # Normalize to dict right away
            results.append(dict(item))
            
    except Exception as e:
        logger.error(f"Error fetching items: {e}")
        # If basics fail, try a very simple query fallback if it was complex? No, just fail for now or return partial
        pass
        
    return results

def calculate_quality_scores(items: List[dict], run_id: uuid.UUID) -> List[dict]:
    """Calculates quality scores for a batch of items."""
    scores = []
    now = datetime.now(timezone.utc)
    
    for item in items:
        score = 0
        breakdown = {}
        missing = []
        
        # 1. Description (+20)
        if item['has_description']:
            score += 20
            breakdown['has_description'] = 20
        else:
            missing.append('description')
            
        # 2. Tags (+15)
        if item['tags_count'] >= 3:
            score += 15
            breakdown['tags_count'] = 15
        elif item['tags_count'] == 0:
            missing.append('tags')
            
        # 3. Extent (+15)
        if item['has_extent']:
            score += 15
            breakdown['has_extent'] = 15
            
        # 4. Thumbnail (+5)
        if item['has_thumbnail']:
            score += 5
            breakdown['has_thumbnail'] = 5
        else:
            missing.append('thumbnail')
            
        # 5. Snippet Length (+5)
        if 20 <= item['snippet_len'] <= 200:
            score += 5
            breakdown['snippet_len'] = 5
            
        # 6. Title Length (+5)
        if 10 <= len(item.get('title', '')) <= 120:
             score += 5
             breakdown['title_len'] = 5
             
        # 7. Freshness (+20)
        if item['modified_at']:
            age = (now - item['modified_at']).days
            if age <= 180:
                score += 20
                breakdown['freshness'] = 20
        
        # 8. URL (+10)
        if item['url']:
            score += 10
            breakdown['url'] = 10
            
        # Clamp
        score = min(max(score, 0), 100)
        
        scores.append({
            'run_id': str(run_id),
            'item_id': item['item_id'],
            'score': score,
            'breakdown_json': json.dumps(breakdown),
            'missing_json': json.dumps(missing),
            'computed_at': now
        })
        
    return scores

def check_url_health(url: str, timeout: int = 5) -> Dict[str, Any]:
    """Performs a HEAD/GET request to check URL health."""
    try:
        # Try HEAD first
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        # If method not allowed, try GET
        if response.status_code == 405:
            response = requests.get(url, timeout=timeout, stream=True)
            response.close() # Close quickly
            
        if response.status_code < 400:
            return {
                'ok': True,
                'status_code': response.status_code,
                'latency_ms': int(response.elapsed.total_seconds() * 1000),
                'error_message': None
            }
        else:
            return {
                'ok': False,
                'status_code': response.status_code,
                'latency_ms': int(response.elapsed.total_seconds() * 1000),
                'error_message': f"HTTP {response.status_code}"
            }
    except Exception as e:
        return {
            'ok': False,
            'status_code': None,
            'latency_ms': None,
            'error_message': str(e)
        }

def run_health_checks(items: List[dict], run_id: uuid.UUID, max_workers: int = 10) -> List[dict]:
    """Runs concurrent health checks on item URLs."""
    results = []
    
    # Filter items with URLs
    items_to_check = [i for i in items if i.get('url')]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Map futures to item_ids
        future_to_item = {
            executor.submit(check_url_health, item['url']): item 
            for item in items_to_check
        }
        
        for future in concurrent.futures.as_completed(future_to_item):
            item = future_to_item[future]
            try:
                res = future.result()
                res['run_id'] = str(run_id)
                res['item_id'] = item['item_id']
                res['checked_url'] = item['url']
                res['checked_at'] = datetime.now(timezone.utc)
                results.append(res)
            except Exception as e:
                logger.error(f"Health check execution error for {item['item_id']}: {e}")
                
    return results

# --- Main Pipeline Orchestrator ---

def run_snapshot(con: duckdb.DuckDBPyConnection, gis, max_items: int = 200, 
                query: str = None, item_types: List[str] = None,
                enable_history: bool = True, enable_scores: bool = True,
                enable_health: bool = True):
    
    run_id = uuid.uuid4()
    start_time = datetime.now(timezone.utc)
    
    # 1. Create Run
    logger.info(f"Starting run {run_id}")
    con.execute("""
        INSERT INTO runs (run_id, started_at, source, portal_url, org_id, triggered_by, pipeline_version)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (str(run_id), start_time, 'arcgis', gis.url, getattr(gis.properties, 'id', 'unknown'), 'manual', 'v1'))
    
    try:
        # 2. Extraction
        raw_items = fetch_items(gis, max_items, query, item_types)
        logger.info(f"Fetched {len(raw_items)} items")
        
        if not raw_items:
            logger.warning("No items found. Finishing run.")
            con.execute("UPDATE runs SET finished_at = ? WHERE run_id = ?", (datetime.now(timezone.utc), str(run_id)))
            return
        
        # 3. Normalization
        norm_items = [normalize_item(r, run_id) for r in raw_items]
        
        # 4. Upsert items_current
        # DuckDB generic upsert approach (some versions support INSERT OR REPLACE, others ON CONFLICT)
        # Using INSERT OR REPLACE for simplicity with DuckDB > 1.0 logic, or verify constraint
        # The schema has PRIMARY KEY on item_id, so INSERT OR REPLACE works.
        
        # We need to construct the INSERT statement using parameters
        # DuckDB python client can insert from a Pandas DF comfortably, or we can use executemany
        # Let's use executemany with a prepared statement
        
        keys = list(norm_items[0].keys())
        cols = ", ".join(keys)
        placeholders = ", ".join(["?"] * len(keys))
        
        # Prepare data tuple based on keys order
        data_tuples = []
        for item in norm_items:
            data_tuples.append([item[k] for k in keys])
            
        con.executemany(f"INSERT OR REPLACE INTO items_current ({cols}) VALUES ({placeholders})", data_tuples)
        logger.info(f"Upserted {len(norm_items)} items into items_current")
        
        # 5. History (SCD2)
        if enable_history:
            # Process SCD2
            # a) Identify changed items (where content_hash differs from last history record)
            # b) Close old records
            # c) Insert new records
            
            # For MVP, simpler approach:
            # Check latest history for each item. 
            # If no history -> Insert New
            # If history exists and hash matches -> Update last_seen_run_id (Optional optimization, or just do nothing if we only care about changes)
            # If history exists and hash differs -> Close old (valid_to = now), Insert New
            
            # We can do this with SQL set operations more efficiently
            # Create temp table with current batch
            con.execute("CREATE TEMP TABLE stg_items AS SELECT * FROM items_current WHERE last_seen_run_id = ?", (str(run_id),))
            
            # Detect Changes: existing current history with different hash
            # Close old
            con.execute("""
                UPDATE items_history 
                SET valid_to = ?, is_current = false
                WHERE is_current = true
                AND item_id IN (SELECT item_id FROM stg_items)
                AND content_hash != (SELECT content_hash FROM stg_items WHERE stg_items.item_id = items_history.item_id)
            """, (start_time,))
            
            # Insert New Versions (for Changed or New items)
            # Find items where no current history exists (either brand new, or just closed above)
            con.execute("""
                INSERT INTO items_history (
                    item_id, content_hash, valid_from, valid_to, is_current,
                    title, item_type, owner, url, access, modified_at,
                    tags_json, description_len, has_extent, 
                    extent_xmin, extent_ymin, extent_xmax, extent_ymax,
                    first_seen_run_id, last_seen_run_id
                )
                SELECT 
                    s.item_id, s.content_hash, ? as valid_from, NULL as valid_to, true as is_current,
                    s.title, s.item_type, s.owner, s.url, s.access, s.modified_at,
                    s.tags_json, s.description_len, s.has_extent,
                    s.extent_xmin, s.extent_ymin, s.extent_xmax, s.extent_ymax,
                    ? as first_seen_run_id, ? as last_seen_run_id
                FROM stg_items s
                LEFT JOIN items_history h ON s.item_id = h.item_id AND h.is_current = true
                WHERE h.item_id IS NULL
            """, (start_time, str(run_id), str(run_id)))

            # Update last_seen_run_id for unchanged items
            con.execute("""
                UPDATE items_history
                SET last_seen_run_id = ?
                WHERE is_current = true
                AND item_id IN (SELECT item_id FROM stg_items)
            """, (str(run_id),))
            
            con.execute("DROP TABLE stg_items")
            logger.info("Processed SCD2 History")
            
        # 6. Quality Scores
        if enable_scores:
            scores = calculate_quality_scores(norm_items, run_id)
            s_keys = list(scores[0].keys())
            s_cols = ", ".join(s_keys)
            s_ph = ", ".join(["?"] * len(s_keys))
            s_data = [[s[k] for k in s_keys] for s in scores]
            con.executemany(f"INSERT INTO quality_scores ({s_cols}) VALUES ({s_ph})", s_data)
            logger.info(f"Computed {len(scores)} quality scores")
            
        # 7. Health Checks
        if enable_health:
            health_results = run_health_checks(norm_items, run_id)
            if health_results:
                h_keys = list(health_results[0].keys())
                h_cols = ", ".join(h_keys)
                h_ph = ", ".join(["?"] * len(h_keys))
                h_data = [[h[k] for k in h_keys] for h in health_results]
                con.executemany(f"INSERT INTO health_checks ({h_cols}) VALUES ({h_ph})", h_data)
                logger.info(f"Ran {len(health_results)} health checks")
        
        # 8. Finalize Run
        con.execute("UPDATE runs SET finished_at = ? WHERE run_id = ?", (datetime.now(timezone.utc), str(run_id)))
        logger.info("Snapshot Run Complete")
        
    except Exception as e:
        logger.error(f"Snapshot run failed: {e}")
        # Could fail run in DB, but for now we rely on finished_at being null or log errors
        raise e
