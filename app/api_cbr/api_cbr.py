# api_cbr.py
# ==========================================
# API REST para el CBR Café Cauca
# ==========================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional, List
import uvicorn

# Importa tu script del CBR (asegúrate que el archivo se llame cbr_cafe.py y esté en la misma carpeta)
from cbr_cafe import run_cbr

app = FastAPI(
    title="CBR Café – Cauca",
    description="API REST del sistema de recomendación basado en casos (CBR) para el cultivo de café en el Cauca.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# Esquema de entrada (de acuerdo a tu run_cbr)
# ======================
class CBRRequest(BaseModel):
    data: List[str] = Field(
        default=["CBR_Cafe_Cauca_A.yaml", "CBR_Cafe_Cauca_B_historicos.yaml"],
        description="Rutas a los YAML de casos A y B"
    )
    tipo: Literal["auto", "almacigos", "fertilizacion_sin_analisis", "broca"] = "auto"

    ubicacion: Optional[str] = Field(default=None)
    altitud: float = Field(default=1678)
    mes: Literal[
        "enero","febrero","marzo","abril","mayo","junio",
        "julio","agosto","septiembre","octubre","noviembre","diciembre"
    ] = "noviembre"
    variedad: Optional[str] = Field(default=None)
    sombra: float = Field(default=25.0)

    temp_media: float = 17.6
    humedad: float = 97.0
    prec_total_mm: float = 192.2
    dias_lluvia: Optional[float] = 18.0
    brillo_solar: Optional[float] = 95.0

    meses_despues_siembra: Optional[float] = 10.0
    edad_vivero_meses: Optional[float] = 3.0
    luna: Optional[Literal["nueva","creciente","llena","menguante"]] = "creciente"
    fase: Optional[Literal["vivero_establecimiento","floracion_llenado","cosecha_poscosecha"]] = "vivero_establecimiento"

    k: int = 3
    kB: int = 1
    usar_extras_b: bool = True
    save_case_to: Optional[str] = "CBR_Cafe_Cauca_C.yaml"


# ======================
# Endpoints
# ======================

@app.get("/")
def root():
    return {"mensaje": "API del CBR Café Cauca funcionando"}

@app.post("/cbr/recomendar")
def recomendar_cbr(body: CBRRequest):
    """
    Ejecuta el CBR con los parámetros recibidos.
    Devuelve el mismo JSON que arma run_cbr().
    """
    try:
        params = body.dict()
        resultado = run_cbr(params, verbose=False)
        if not resultado:
            raise HTTPException(status_code=400, detail="No se generó salida desde el CBR (revisa los YAML).")
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ejecutando CBR: {e}")


if __name__ == "__main__":
    # Levantar servidor local
    uvicorn.run(app, host="0.0.0.0", port=8000)
