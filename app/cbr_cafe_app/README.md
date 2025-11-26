# 🌱 CBR Café – Cauca  
Sistema de recomendación agrícola basado en **Razonamiento Basado en Casos (CBR)**  
**Flutter · FastAPI · Python · YAML**

---

## 📌 Descripción General

El proyecto **CBR Café – Cauca** es un sistema de recomendación agronómica diseñado para apoyar decisiones técnicas en el cultivo de café mediante un motor de **Razonamiento Basado en Casos (CBR)**.  
Integra datos agroclimáticos, manejo del cultivo y conocimiento experto para generar recomendaciones técnicas y tradicionales en tres dominios:

- **Almácigos**  
- **Fertilización sin análisis de suelo**  
- **Broca (CBB)**  

La arquitectura está compuesta por:

- **Frontend multiplataforma Flutter** (web y móvil)  
- **API REST construida con FastAPI**  
- **Motor CBR en Python**  
- **Datasets YAML A, B y C** que conforman la base de conocimiento  

---

## 🧱 Arquitectura del Sistema

```
Flutter Web / Flutter Android
        ↓  (HTTP/JSON)
      FastAPI (Servidor)
        ↓
  Motor CBR en Python
        ↓
Datasets YAML (A, B, C)
```

---

## 📁 Estructura del Repositorio

```
/api_cbr/
    api_cbr.py
    cbr_cafe.py
    CBR_Cafe_Cauca_A.yaml
    CBR_Cafe_Cauca_B_historicos.yaml

/flutter_app/
    lib/main.dart
    pubspec.yaml
    android/
    web/
```

---

## 📦 Requisitos

### 🔧 Requisitos del Backend (Python)

- Python **3.10+**
- FastAPI
- Uvicorn
- PyYAML

Instalación:

```bash
pip install fastapi uvicorn pyyaml
```

### 📱 Requisitos del Frontend (Flutter)

- Flutter SDK (3.x o superior)
- Android Studio o VS Code con extensiones Flutter/Dart
- SDK de Android para ejecución móvil
- Chrome para ejecución web

Verificación:

```bash
flutter doctor
```

---

## ▶️ Ejecución del Backend (API CBR)

Ubicado dentro de la carpeta donde está `api_cbr.py`:

```bash
uvicorn api_cbr:app --reload --port 8000
```

Si deseas ejecutarlo directamente:

```bash
python api_cbr.py
```

### ✔ Endpoint Principal

`POST /cbr/recomendar`

Ejemplo de cuerpo JSON:

```json
{
  "data": ["CBR_Cafe_Cauca_A.yaml", "CBR_Cafe_Cauca_B_historicos.yaml"],
  "tipo": "auto",
  "ubicacion": "Popayán",
  "altitud": 1678,
  "mes": "noviembre",
  "sombra": 25,
  "temp_media": 17.6,
  "humedad": 97,
  "prec_total_mm": 192.2,
  "dias_lluvia": 18,
  "brillo_solar": 95,
  "meses_despues_siembra": 10,
  "edad_vivero_meses": 3,
  "luna": "creciente",
  "fase": "vivero_establecimiento",
  "k": 3,
  "kB": 3,
  "usar_extras_b": true
}
```

---

## ▶️ Ejecución del Frontend (Flutter)

Dentro de la carpeta del proyecto Flutter:

### Web:

```bash
flutter run -d chrome
```

### Android:

```bash
flutter run -d android
```

---

## 🌾 Motor de Razonamiento CBR

El archivo `cbr_cafe.py` implementa:

- Normalización por rangos
- Pesos diferenciados por dominio
- Similitud ponderada
- Recuperación k-NN
- Extras históricos (kB)
- Reglas de aplicabilidad por dominio
- Retención automática de casos nuevos (Dataset C)

---

## 🧪 Prueba rápida con Postman

Configurar:

- Método: **POST**
- URL: `http://localhost:8000/cbr/recomendar`
- Body → JSON → pegar el ejemplo del endpoint

---

## 🗂 Datasets

### Dataset A  
Casos base del sistema, modelados a partir de condiciones agroclimáticas del Cauca.

### Dataset B  
Casos históricos por estación meteorológica.

### Dataset C  
Casos retenidos automáticamente por el CBR.

---

## 👨‍💻 Autor

Proyecto desarrollado para asistencia técnica en caficultura en el departamento del Cauca mediante integración de conocimiento experto, datos climáticos y sistemas inteligentes.

---

## ⭐ Contribuciones

Si deseas ampliar el sistema (nuevos dominios, más estaciones, nuevas reglas CBR), puedes abrir un issue o contacto directo.

---

