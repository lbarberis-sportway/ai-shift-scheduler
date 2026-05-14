from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
import os
import jwt

# Add the current directory to path to import solver
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from cp_sat.solver import solve_schedule, analyze_history, DAY_NAMES
from db_manager import (
    learn_patterns,
    get_top_patterns,
    get_top_patterns_by_day,
    get_employee_preferred_patterns_by_day,
    get_stats,
)

# Per far funzionare il routing sia locale che su Vercel:
# Su Vercel le chiamate arrivano con il prefisso /api/
API_PREFIX = "/api" if os.environ.get("VERCEL") else ""

app = FastAPI()

# Sicurezza CORS: accetta accessi solo dal tuo Frontend su Vercel o locale
frontend_url = os.environ.get("FRONTEND_URL")
if frontend_url:
    allowed_origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        frontend_url.rstrip('/')
    ]
else:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Verification logic for Supabase (Dynamic JWKS)
security = HTTPBearer()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET")

# Initialize JWK Client if SUPABASE_URL is provided
jwks_client = None
if SUPABASE_URL:
    jwks_url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
    # Supabase Kong gateway requires the apikey header even for JWKS
    headers = {"apikey": os.environ.get("SUPABASE_ANON_KEY", "")}
    jwks_client = jwt.PyJWKClient(jwks_url, headers=headers)

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Local fallback or old method if URL is missing
    if not SUPABASE_URL and not SUPABASE_JWT_SECRET:
        return True
    
    token = credentials.credentials
    
    try:
        if jwks_client:
            # Modern way: fetch the public key from Supabase JWKS
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token, 
                signing_key.key, 
                algorithms=["HS256", "RS256", "ES256"], 
                options={"verify_aud": False}
            )
        else:
            # Legacy way: use the static secret
            payload = jwt.decode(
                token, 
                SUPABASE_JWT_SECRET, 
                algorithms=["HS256"], 
                options={"verify_aud": False}
            )
        return payload
        
    except Exception as e:
        print(f"🔐 JWT Auth Error: {str(e)}")
        raise HTTPException(
            status_code=401, 
            detail=f"Autenticazione fallita: {str(e)}. Controlla SUPABASE_URL su Render."
        )

class OptimizeRequest(BaseModel):
    employees: List[Dict[str, Any]]
    settings: Dict[str, Any]

@app.post("/api/optimize")
@app.post("/optimize")
async def optimize(request: OptimizeRequest, user=Depends(verify_token)):
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
                'employee_id': str(emp.get('ID', '')).strip(),
                'name': emp.get('Nome Cognome', emp.get('Nome', 'Sconosciuto')).strip(),
                'contract_min': int(contract_hours * 60),
                'contract_hours': contract_hours,
                'preferences': emp.get('Esigenze/Preferenze', ''),
                'fixed_rests': str(emp.get('Riposo Fisso', '')).strip(),
                'vacation_days': str(emp.get('Ferie', '')).strip(),
                'history': history,
                'raw': emp,  # Keep original for pattern extraction
            })
        
        # === STEP 4: BUILD per-employee per-day pattern map ===
        employee_day_patterns = {}
        employees_with_history = 0
        for ep in processed_people:
            emp_id = ep.get('employee_id', '')
            if not emp_id:
                continue
            day_map = {}
            has_any = False
            for day_name in DAY_NAMES:
                day_pats = get_employee_preferred_patterns_by_day(
                    emp_id, day_name, limit=8, min_day_patterns=3
                )
                if day_pats:
                    day_map[day_name] = day_pats
                    has_any = True
            if has_any:
                employee_day_patterns[emp_id] = day_map
                employees_with_history += 1
        print(f"📅 Day-pattern map built for {employees_with_history}/{len(processed_people)} employees")

        # === STEP 5: SOLVE with accumulated knowledge ===
        results, status = solve_schedule(
            processed_people,
            request.settings,
            db_patterns=db_patterns,
            employee_day_patterns=employee_day_patterns,
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

@app.get("/api/stats")
@app.get("/stats")
async def stats(user=Depends(verify_token)):
    """Get pattern database statistics."""
    return get_stats()

@app.get("/")
@app.head("/")
async def root():
    """Health check per Render.com"""
    return {"status": "ok", "message": "Backend AI is running on Render!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
