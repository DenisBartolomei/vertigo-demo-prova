"""
Script di migrazione per sessioni feedback bloccate.

Questo script trova tutte le sessioni che sono in stato "Feedback in elaborazione"
ma hanno tutti i dati necessari per essere processate dal batch (gap_analysis,
enriched_gaps, cv_analysis_report, case_evaluation_report) e le migra allo stato
"Feedback in coda batch (può richiedere fino a 24h)" in modo che possano essere
trovate dal batch processor.

Uso:
    python scripts/migrate_feedback_status.py [--dry-run] [--tenant-id TENANT_ID]

Opzioni:
    --dry-run: Mostra solo le sessioni che verrebbero migrate senza modificarle
    --tenant-id: Migra solo per un tenant specifico (default: tutti i tenant)
"""

import sys
import os
from typing import List, Dict, Optional

# Aggiungi il percorso root al path per importare i moduli
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.data_manager import db
from services.tenant_data_manager import SESSION_STATUS

def find_sessions_to_migrate(tenant_id: Optional[str] = None) -> List[Dict]:
    """
    Trova tutte le sessioni che devono essere migrate.
    
    Args:
        tenant_id: ID del tenant specifico (None = tutti i tenant)
    
    Returns:
        Lista di dizionari con informazioni sulle sessioni da migrare
    """
    if db is None:
        print("❌ Errore: Database non disponibile")
        return []
    
    sessions_to_migrate = []
    
    # Trova tutte le collection di sessioni
    collections = db.list_collection_names()
    session_collections = [c for c in collections if c.endswith("_sessions")]
    
    if tenant_id:
        # Filtra per tenant specifico
        target_collection = f"{tenant_id}_sessions"
        if target_collection not in session_collections:
            print(f"❌ Nessuna collection trovata per tenant: {tenant_id}")
            return []
        session_collections = [target_collection]
    
    for collection_name in session_collections:
        collection = db[collection_name]
        tenant_id_from_collection = collection_name.replace("_sessions", "")
        
        # Query per trovare sessioni da migrare
        query = {
            "stages.status": "Feedback in elaborazione",
            "stages.gap_analysis": {"$exists": True},
            "stages.enriched_gaps": {"$exists": True},
            "stages.cv_analysis_report": {"$exists": True},
            "stages.case_evaluation_report": {"$exists": True},
            "stages.feedback_report_path": {"$exists": False}  # Non ancora generato
        }
        
        sessions = list(collection.find(query, {
            "_id": 1,
            "candidate_name": 1,
            "position_id": 1,
            "stages.status": 1
        }))
        
        for session in sessions:
            sessions_to_migrate.append({
                "session_id": session["_id"],
                "tenant_id": tenant_id_from_collection,
                "collection_name": collection_name,
                "candidate_name": session.get("candidate_name", "N/A"),
                "position_id": session.get("position_id", "N/A"),
                "current_status": session.get("stages", {}).get("status", "N/A")
            })
    
    return sessions_to_migrate

def migrate_sessions(sessions: List[Dict], dry_run: bool = False) -> Dict:
    """
    Migra le sessioni allo stato corretto.
    
    Args:
        sessions: Lista di sessioni da migrare
        dry_run: Se True, non modifica il database
    
    Returns:
        Dizionario con statistiche della migrazione
    """
    if db is None:
        print("❌ Errore: Database non disponibile")
        return {"success": 0, "failed": 0, "errors": []}
    
    stats = {
        "total": len(sessions),
        "success": 0,
        "failed": 0,
        "errors": []
    }
    
    if dry_run:
        print(f"\n🔍 DRY RUN: Verranno migrate {len(sessions)} sessioni\n")
        for session in sessions:
            print(f"  - {session['session_id']} ({session['tenant_id']}): {session['candidate_name']}")
        return stats
    
    print(f"\n🔄 Migrazione di {len(sessions)} sessioni...\n")
    
    for session in sessions:
        try:
            collection = db[session["collection_name"]]
            
            # Aggiorna lo stato
            result = collection.update_one(
                {"_id": session["session_id"]},
                {
                    "$set": {
                        "stages.status": SESSION_STATUS["FEEDBACK_BATCH_PENDING"]
                    }
                }
            )
            
            if result.modified_count > 0:
                stats["success"] += 1
                print(f"✅ Migrata: {session['session_id']} ({session['tenant_id']}) - {session['candidate_name']}")
            else:
                stats["failed"] += 1
                error_msg = f"Sessione {session['session_id']} non trovata o già aggiornata"
                stats["errors"].append(error_msg)
                print(f"⚠️  {error_msg}")
        
        except Exception as e:
            stats["failed"] += 1
            error_msg = f"Errore migrazione {session['session_id']}: {str(e)}"
            stats["errors"].append(error_msg)
            print(f"❌ {error_msg}")
    
    return stats

def main():
    """Funzione principale"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migra sessioni feedback bloccate allo stato corretto per batch processing"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra solo le sessioni che verrebbero migrate senza modificarle"
    )
    parser.add_argument(
        "--tenant-id",
        type=str,
        default=None,
        help="Migra solo per un tenant specifico (default: tutti i tenant)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Script di Migrazione Stati Feedback")
    print("=" * 60)
    
    if args.dry_run:
        print("🔍 Modalità DRY RUN - nessuna modifica verrà effettuata\n")
    
    # Trova sessioni da migrare
    print("🔍 Ricerca sessioni da migrare...")
    sessions = find_sessions_to_migrate(tenant_id=args.tenant_id)
    
    if not sessions:
        print("\n✅ Nessuna sessione da migrare trovata.")
        return
    
    print(f"\n📊 Trovate {len(sessions)} sessioni da migrare")
    
    # Raggruppa per tenant
    by_tenant = {}
    for session in sessions:
        tenant = session["tenant_id"]
        if tenant not in by_tenant:
            by_tenant[tenant] = []
        by_tenant[tenant].append(session)
    
    print(f"   Distribuite su {len(by_tenant)} tenant(s):")
    for tenant, tenant_sessions in by_tenant.items():
        print(f"   - {tenant}: {len(tenant_sessions)} sessioni")
    
    # Chiedi conferma se non è dry-run
    if not args.dry_run:
        print("\n⚠️  ATTENZIONE: Questa operazione modificherà il database.")
        response = input("Procedere con la migrazione? (s/N): ")
        if response.lower() != 's':
            print("❌ Migrazione annullata.")
            return
    
    # Esegui migrazione
    stats = migrate_sessions(sessions, dry_run=args.dry_run)
    
    # Mostra statistiche finali
    print("\n" + "=" * 60)
    print("Riepilogo Migrazione")
    print("=" * 60)
    print(f"Totale sessioni: {stats['total']}")
    print(f"✅ Migrate con successo: {stats['success']}")
    print(f"❌ Fallite: {stats['failed']}")
    
    if stats["errors"]:
        print(f"\n⚠️  Errori ({len(stats['errors'])}):")
        for error in stats["errors"][:10]:  # Mostra solo i primi 10
            print(f"   - {error}")
        if len(stats["errors"]) > 10:
            print(f"   ... e altri {len(stats['errors']) - 10} errori")

if __name__ == "__main__":
    main()








