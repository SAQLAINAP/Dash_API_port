import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.storage.postgres import SessionLocal, create_tables, upsert_model, clear_leaderboard, insert_leaderboard_entry

def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0

def safe_int(val):
    try:
        return int(val.replace(',',''))
    except:
        return 0

def migrate_registry():
    print("Migrating Registry (registry/latest.json)...")
    path = "registry/latest.json"
    if not os.path.exists(path):
        print("No registry file found.")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    db = SessionLocal()
    try:
        count = 0
        for item in data:
            name = item.get('model')
            if not name: continue
            
            provider = item.get('provider', 'Unknown')
            
            # Extract fields
            pricing = item.get('fields', {}).get('pricing', {}).get('value', {})
            inp = safe_float(pricing.get('input', 0))
            out = safe_float(pricing.get('output', 0))
            
            ctx = item.get('fields', {}).get('context_window', {}).get('value', 0)
            if isinstance(ctx, str): ctx = safe_int(ctx)
            
            model_data = {
                'name': name,
                'provider': provider,
                'input_price': inp,
                'output_price': out,
                'context_window': ctx,
                'config': item  # Store full original JSON for backup/extra fields
            }
            
            upsert_model(db, model_data)
            count += 1
        print(f"Successfully migrated {count} models.")
    except Exception as e:
        print(f"Error migrating registry: {e}")
    finally:
        db.close()

def migrate_leaderboard():
    print("Migrating Leaderboard (registry/leaderboard.json)...")
    path = "registry/leaderboard.json"
    if not os.path.exists(path):
        print("No leaderboard file found.")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    db = SessionLocal()
    try:
        clear_leaderboard(db) # Reset leaderboard on migration
        count = 0
        for item in data:
            try:
                # Ensure rank is int
                rank_str = str(item.get('rank', '0'))
                if not rank_str.isdigit(): continue
                
                # Ensure score is int (sometimes it acts up)
                score = item.get('arena_score')
                if isinstance(score, str):
                    if not score.isdigit(): score = 0
                    else: score = int(score)
                
                entry = {
                    'rank': int(rank_str),
                    'model': item.get('model'),
                    'arena_score': score,
                    'ci_95': item.get('ci_95'),
                    'category': item.get('category', 'Overall')
                }
                insert_leaderboard_entry(db, entry)
                count += 1
            except Exception as e:
                print(f"Skipping row: {item} | Error: {e}")
        
        db.commit()
        print(f"Successfully migrated {count} leaderboard entries.")
    except Exception as e:
        print(f"Error migrating leaderboard: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Initializing Database...")
    create_tables()
    migrate_registry()
    migrate_leaderboard()
    print("Migration Complete!")
