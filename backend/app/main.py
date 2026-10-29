import os, json
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timezone, date
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select
from .database import Base, engine, get_db
from .models import Meal, Goal, Preference
from .schemas import MealCreate, MealOut, GoalsIn
from .nutrition import calculate, list_foods, search_usda
from .ai import analyze_image, AIUnavailable

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Food AI Intelligence API", version="0.1.0", description="Nutrition estimates and meal tracking; not a medical diagnostic tool.")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET","POST","PUT","PATCH","DELETE"], allow_headers=["Content-Type"])
MAX_UPLOAD = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024

@app.get("/api/health")
def health(): return {"status":"ok", "ai_configured": bool(os.getenv("OPENAI_API_KEY")), "nutrition_reference_count":len(list_foods())}

@app.get("/api/foods")
def foods(): return {"items":list_foods(), "notice":"Small starter reference table; not a complete IFCT or USDA import."}

@app.get("/api/nutrition/usda-search")
async def usda_search(q: str = Query(min_length=1, max_length=120)):
    key = os.getenv("USDA_API_KEY", "").strip()
    if not key: raise HTTPException(503, "USDA lookup is not configured. Add USDA_API_KEY to backend/.env.")
    try: return {"items": await search_usda(q, key), "source": "USDA FoodData Central"}
    except Exception as e: raise HTTPException(502, f"USDA FoodData Central request failed ({type(e).__name__}).")

@app.post("/api/nutrition/calculate")
def nutrition_calc(payload: dict):
    try: return calculate(str(payload.get("food_key", "")), float(payload.get("grams", 0)))
    except (ValueError, KeyError) as e: raise HTTPException(422, str(e))

@app.post("/api/analyze-image")
async def image_analysis(file: UploadFile = File(...)):
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed: raise HTTPException(415, "Upload a JPEG, PNG, or WebP image.")
    raw = await file.read(MAX_UPLOAD + 1)
    if not raw: raise HTTPException(400, "The uploaded image is empty.")
    if len(raw) > MAX_UPLOAD: raise HTTPException(413, f"Image exceeds the {MAX_UPLOAD//1024//1024} MB limit.")
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(raw)); img.verify()
    except Exception: raise HTTPException(400, "The uploaded file is not a valid readable image.")
    try: return await analyze_image(raw, file.content_type)
    except AIUnavailable as e: raise HTTPException(503, str(e))

@app.get("/api/meals", response_model=list[MealOut])
def get_meals(start: date | None = None, end: date | None = None, db: Session = Depends(get_db)):
    stmt = select(Meal).order_by(Meal.eaten_at.desc())
    meals = db.scalars(stmt).all()
    def in_range(m):
        d = m.eaten_at.date() if m.eaten_at.tzinfo else m.eaten_at.date()
        return (start is None or d >= start) and (end is None or d <= end)
    return [m for m in meals if in_range(m)]

@app.post("/api/meals", response_model=MealOut, status_code=201)
def create_meal(data: MealCreate, db: Session = Depends(get_db)):
    meal = Meal(**data.model_dump(exclude={"eaten_at"}), eaten_at=data.eaten_at or datetime.now(timezone.utc))
    db.add(meal); db.commit(); db.refresh(meal); return meal

@app.put("/api/meals/{meal_id}", response_model=MealOut)
def update_meal(meal_id: int, data: MealCreate, db: Session = Depends(get_db)):
    meal = db.get(Meal, meal_id)
    if not meal: raise HTTPException(404, "Meal not found")
    for k,v in data.model_dump().items(): setattr(meal,k,v)
    db.commit(); db.refresh(meal); return meal

@app.delete("/api/meals/{meal_id}", status_code=204)
def delete_meal(meal_id: int, db: Session = Depends(get_db)):
    meal = db.get(Meal, meal_id)
    if not meal: raise HTTPException(404, "Meal not found")
    db.delete(meal); db.commit()

@app.get("/api/goals")
def get_goals(db: Session = Depends(get_db)):
    g = db.get(Goal, 1)
    if not g: g = Goal(id=1); db.add(g); db.commit(); db.refresh(g)
    return {k:getattr(g,k) for k in ["calories","protein_g","carbs_g","fat_g","fibre_g"]}

@app.put("/api/goals")
def put_goals(data: GoalsIn, db: Session = Depends(get_db)):
    g = db.get(Goal, 1)
    if not g: g = Goal(id=1); db.add(g)
    for k,v in data.model_dump().items(): setattr(g,k,v)
    db.commit(); db.refresh(g)
    return {k:getattr(g,k) for k in data.model_fields}

@app.get("/api/preferences")
def get_preferences(db: Session = Depends(get_db)):
    rows = db.scalars(select(Preference)).all()
    return {r.key:json.loads(r.value) for r in rows}

@app.put("/api/preferences")
def put_preferences(data: dict, db: Session = Depends(get_db)):
    allowed = {"theme", "language", "portionUnit", "nutritionDisplay"}
    if any(k not in allowed for k in data): raise HTTPException(422,"Unsupported preference key")
    for k,v in data.items():
        row=db.get(Preference,k)
        if row: row.value=json.dumps(v)
        else: db.add(Preference(key=k,value=json.dumps(v)))
    db.commit(); return get_preferences(db)

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    today = datetime.now().date()
    meals = db.scalars(select(Meal).order_by(Meal.eaten_at.desc())).all()
    today_meals = [m for m in meals if m.eaten_at.date() == today]
    g = db.get(Goal,1) or Goal(id=1)
    totals = {k:round(sum(getattr(m,k) for m in today_meals),1) for k in ["calories","protein_g","carbs_g","fat_g","fibre_g"]}
    weekly=[]
    from datetime import timedelta
    for offset in reversed(range(7)):
        d=today-timedelta(days=offset)
        daymeals=[m for m in meals if m.eaten_at.date()==d]
        weekly.append({"date":d.isoformat(),"label":d.strftime("%a"),"calories":round(sum(m.calories for m in daymeals),1),"meals":len(daymeals)})
    return {"date":today.isoformat(),"totals":totals,"goals":{k:getattr(g,k) for k in ["calories","protein_g","carbs_g","fat_g","fibre_g"]},"weekly":weekly,"recent":meals[:5],"meal_distribution":{t:sum(1 for m in meals if m.meal_type==t) for t in ["breakfast","lunch","dinner","snack"]}}

@app.post("/api/chat")
async def chat(payload: dict, db: Session = Depends(get_db)):
    message = str(payload.get("message", "")).strip()
    if not message: raise HTTPException(422,"Message is required")
    api_key=os.getenv("OPENAI_API_KEY","").strip()
    if not api_key: raise HTTPException(503,"AI chat is not configured. Add OPENAI_API_KEY to backend/.env.")
    import httpx
    recent=db.scalars(select(Meal).order_by(Meal.eaten_at.desc()).limit(10)).all()
    context=[{"name":m.name,"calories":m.calories,"protein_g":m.protein_g,"carbs_g":m.carbs_g,"fat_g":m.fat_g,"fibre_g":m.fibre_g} for m in recent]
    base=os.getenv("OPENAI_BASE_URL","https://api.openai.com/v1").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            r=await client.post(f"{base}/chat/completions",headers={"Authorization":f"Bearer {api_key}"},json={"model":os.getenv("CHAT_MODEL","gpt-4o-mini"),"messages":[{"role":"system","content":"You are a cautious general nutrition assistant. Do not diagnose or prescribe. Distinguish general advice from recorded values; do not invent nutrition facts. Recent saved meals (may be empty): "+json.dumps(context)},{"role":"user","content":message}]})
        r.raise_for_status(); return {"answer":r.json()["choices"][0]["message"]["content"]}
    except Exception as e: raise HTTPException(502,f"AI chat request failed ({type(e).__name__}); no answer was generated.")

@app.get("/api/graph")
def graph(db: Session = Depends(get_db)):
    foods=list_foods(); nodes=[]; edges=[]
    for f in foods:
        nodes.append({"id":f["key"],"label":f["name"],"type":"food"})
        for nutrient,key in [("protein","protein_g"),("carbohydrate","carbs_g"),("fat","fat_g"),("fibre","fibre_g")]:
            nid="nutrient:"+nutrient
            if not any(n["id"]==nid for n in nodes): nodes.append({"id":nid,"label":nutrient.title(),"type":"nutrient"})
            edges.append({"source":f["key"],"target":nid,"label":f"{f[key]} g / 100 g"})
    g=db.get(Goal,1)
    if g:
        nodes.append({"id":"goal:calories","label":f"Calorie goal {g.calories:g} kcal","type":"goal"}); edges.append({"source":"goal:calories","target":"nutrient:carbohydrate","label":"daily target context"})
    return {"nodes":nodes,"edges":edges}
