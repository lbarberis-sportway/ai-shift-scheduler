from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import sys
import os

# Add the current directory to path to import solver
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from cp_sat.solver import solve_schedule, analyze_history
from db_manager import learn_patterns, get_top_patterns, get_stats

app = FastAPI()

# Enable CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OptimizeRequest(BaseModel):
    employees: List[Dict[str, Any]]
    settings: Dict[str, Any]

@app.post("/optimize")
async def optimize(request: OptimizeRequest):
    try:
        # === STEP 1: LEARN from the imported CSV ===
        # Store all patterns from this import into the database
        store_open = request.settings.get('openTime', '09:30')
        store_close = request.settings.get('closeTime', '19:30')
        
        num_learned = learn_patterns(
            request.employees,
            store_open_str=store_open,
            store_close_str=store_close,
            source_file='webapp_import'
        )
        print(f"📚 Learned {num_learned} pattern occurrences from this import")
        
        # === STEP 2: RETRIEVE accumulated patterns from DB ===
        db_patterns = get_top_patterns(limit=30, min_frequency=1)
        print(f"🧠 Retrieved {len(db_patterns)} patterns from memory")
        
        # === STEP 3: Pre-process employees for the solver ===
        processed_people = []
        for emp in request.employees:
            try:
                contract_hours = float(str(emp.get('Ore Contratto', '0')).replace(',', '.'))
            except:
                contract_hours = 0
            
            history = analyze_history(emp)
            
            processed_people.append({
                'name': emp.get('Nome', 'Sconosciuto'),
                'contract_min': int(contract_hours * 60),
                'contract_hours': contract_hours,
                'preferences': emp.get('Esigenze/Preferenze', ''),
                'history': history,
                'raw': emp,  # Keep original for pattern extraction
            })
        
        # === STEP 4: SOLVE with accumulated knowledge ===
        results, status = solve_schedule(
            processed_people,
            request.settings,
            db_patterns=db_patterns  # Pass learned patterns to solver
        )
        
        if not results:
            raise HTTPException(status_code=400, detail=f"Nessuna soluzione trovata: {status}")
        
        # Get stats for logging
        stats = get_stats()
        print(f"📊 DB Stats: {stats['total_patterns']} patterns, {stats['total_imports']} imports, {stats['total_employees_tracked']} employees tracked")
        
        return {
            "status": status,
            "schedule": results,
            "learning": {
                "patternsLearnedThisImport": num_learned,
                "totalPatternsInMemory": stats['total_patterns'],
                "totalImports": stats['total_imports'],
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during optimization: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def stats():
    """Get pattern database statistics."""
    return get_stats()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
