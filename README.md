# 🌱 CBR Café – Cauca  
Repositorio general del sistema de recomendación basado en **Razonamiento Basado en Casos (CBR)** para el cultivo de café en el departamento del Cauca. Este repositorio reúne los datasets, modelos de similitud, scripts generadores y módulos necesarios para ejecutar, adaptar y extender el prototipo.

---

## 📁 Estructura del Repositorio

```
/
├── datasets/
│   ├── CBR_Cafe_Cauca_A.yaml
│   ├── CBR_Cafe_Cauca_B_historicos.yaml
│   └── generador_dataset_A/
│         └── generador_dataset_A.py
│
├── modelos/
│   ├── distancia_euclidiana.py
│   └── similitud_coseno.py
│
├── api/
│   └── api_cbr.py
│
└── README_GENERAL.md
```

---

## 📂 1. datasets/

Este directorio almacena los archivos YAML que conforman la **base de conocimiento del sistema CBR**.

### 🔹 Dataset A — Casos simulados del Cauca
- Archivo: `CBR_Cafe_Cauca_A.yaml`
- Contiene cientos de casos para almácigos, fertilización y broca.
- Representa condiciones agroclimáticas simuladas coherentes con el departamento del Cauca.
- Incluye variables como temperatura, humedad, precipitación, altitud, sombra, fases fenológicas y más.

#### Generación automática del Dataset A
El dataset puede regenerarse utilizando:

📌 `datasets/generador_dataset_A/generador_dataset_A.py`

Este script:
- Simula condiciones climáticas basadas en altitud y mes.
- Construye casos por dominio agrícola.
- Asigna recomendaciones técnicas y tradicionales.
- Genera archivos adicionales:
  - `CBR_Cafe_Cauca_A_preview.csv`
  - `grafico_validacion.png`

---

### 🔹 Dataset B — Casos históricos
- Archivo: `CBR_Cafe_Cauca_B_historicos.yaml`
- Contiene datos históricos asociados a estaciones meteorológicas.
- Usado para recuperación complementaria (kB) basada en similitudes climáticas.

---

## 📂 2. modelos/

Este directorio contiene módulos reutilizables para cálculos de similitud, empleados por el motor CBR o para integración externa.

### 🔹 distancia_euclidiana.py
Implementa **distancia euclidiana ponderada y normalizada**, adecuada para medir similitud entre vectores climáticos o agronómicos.  
Permite:
- Definir pesos por variable.
- Adaptar fácilmente nuevos dominios o modelos.

### 🔹 similitud_coseno.py
Implementa la **similitud del coseno**, útil para comparaciones basadas en dirección del vector más que en magnitud.

Ambos modelos están listos para reutilización directa en:
- La app Flutter
- Scripts de validación
- Extensiones del motor CBR  

---

## 📂 3. api/

### 🔹 api_cbr.py  
Implementación de la **API REST** que expone el motor de razonamiento.  

Funciones principales:
- Recibe solicitudes JSON desde clientes web/móviles.
- Ejecuta `run_cbr()` para procesar la consulta.
- Envía recomendaciones, similitudes y casos relevantes.
- Permite retención de nuevos casos (Dataset C).

---

## 🚀 Ejecución del Backend

Instalar dependencias:

```bash
pip install fastapi uvicorn pyyaml
```

Ejecutar API:

```bash
uvicorn api_cbr:app --reload --port 8000
```

Endpoint principal:

```
POST /cbr/recomendar
```

---

## 📝 Uso de los Modelos de Similitud

```python
from modelos.distancia_euclidiana import calcular_similitud_euclidiana
from modelos.similitud_coseno import similitud_coseno
```

Ambos scripts pueden usarse para pruebas, investigación o construcción de motores alternativos.

---

## 🧪 Regeneración del Dataset A

```bash
python datasets/generador_dataset_A/generador_dataset_A.py
```

Salida:
- Nuevo `CBR_Cafe_Cauca_A.yaml`
- CSV de vista previa
- Gráfico de validación

---

## 📌 Finalidad del Repositorio

Este repositorio permite:

- Reproducir completamente el sistema CBR agrícola.
- Analizar y extender la base de conocimiento del Cauca.
- Integrar módulos con apps externas (Flutter/Web/API).
- Desarrollar nuevos modelos de similitud o dominios agrícolas.
- Facilitar investigación en sistemas expertos y agricultura digital.

---

## 📄 Licencia
(Agregar MIT, Apache 2.0 o equivalente)

---

## 👨‍💻 Autor
Proyecto desarrollado como prototipo para integrar conocimiento agronómico y datos climáticos mediante técnicas de inteligencia artificial aplicada al sector cafetero del Cauca.
