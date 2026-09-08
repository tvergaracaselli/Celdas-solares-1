# Laboratorio virtual — Celda p-n de silicio (Problema 2.2)

Proyecto 1, "Celdas Solares Fotovoltaicas", UAI 2026-2. Semilla **S = 3**.

## Cómo correrlo

```bash
pip install -r requirements.txt
streamlit run app.py
```

Para desplegarlo en Streamlit Community Cloud: sube esta carpeta a un
repositorio de GitHub (los 4 archivos: `app.py`, `fisica.py`,
`constantes.py`, `requirements.txt`) y conéctalo en
https://share.streamlit.io — el `app.py` es el archivo principal.

## Arquitectura

```
constantes.py   → único módulo de constantes físicas (todas con unidad y fuente,
                   Anexo A/B del enunciado). Nada de números sueltos en el resto del código.
fisica.py        → modelo físico puro, sin nada de Streamlit:
                     - óptica: n(λ), k(λ), α(λ), R(λ), espectro AM1.5G, Beer-Lambert
                     - transporte: D, L, potencial y ancho de zona de deplección
                     - colección: fc(x) por tramos (emisor/deplección/base)
                     - EQE/IQE: versión "rápida" (trapecios, solo para visualización)
                       y versión "precisa" (integral analítica por tramos, la que se
                       usa para todo número que se reporta o valida)
                     - diodo: J0, ecuación implícita J(V) con Rs/Rp, parámetros de celda
                     - malla frontal de dedos de plata (sombra + Rs)
                     - temperatura: Eg(T), ni(T), movilidad(T), J0(T), Voc analítico
app.py           → interfaz Streamlit: sidebar con TODOS los parámetros compartidos
                   (st.session_state), y 5 pestañas (st.tabs):
                     1) Absorción y Generación   — animación de fotones cayendo (Canvas/JS)
                        + G(x) + mapa 2D G(x,λ) + balance de fotones
                     2) Eficiencia Cuántica (EQE/IQE) — fc(x), EQE/IQE, mapa de sectores 8×8
                     3) Curva I-V                — barrido de voltaje animado (Plotly frames),
                        malla frontal, Jsc/Voc/FF/η
                     4) Mapa de Sectores y Defectos — contaminación localizada + dedo roto,
                        propagados a la curva I-V global
                     5) Validación                — V1-V7 automáticas con veredicto ✅/❌
```

El **estado se comparte entre pestañas** vía `st.session_state`: cambiar
`Sf`, `τₙ`, `Rs`, el número de dedos, etc. en la barra lateral (o los
defectos en la pestaña 4) recalcula automáticamente las 5 pestañas.

## Animación temporal real

- **Pestaña 1**: Canvas HTML5 + JavaScript (`st.components.v1.html`) con
  fotones que caen físicamente, se absorben a una profundidad muestreada
  de la distribución exponencial de Beer-Lambert, y generan pares
  electrón-hueco visibles (no es un gráfico estático que cambia con un
  slider: hay movimiento continuo con `requestAnimationFrame`).
- **Pestaña 3**: curva J-V/P-V animada con `plotly.graph_objects.Frame`
  — un punto recorre la curva mientras se barre el voltaje.

## Datos ópticos y espectrales

La simulación usa archivos de datos entregados junto con el código:

- `datos/Schinke.csv`: índice de refracción complejo del silicio,
  con columnas n(λ) y k(λ), rango 250–1450 nm. El coeficiente
  de absorción se calcula en código mediante:

  \[
  \alpha(\lambda)=\frac{4\pi k(\lambda)}{\lambda}.
  \]

- `datos/astmg173.xls`: espectro solar ASTM G173-03, hoja
  `SMARTS2`, columna `Global tilt`, correspondiente a AM1.5G.

Los datos se interpolan sobre una malla espectral de 300–1200 nm.
No se extrapola fuera del rango de Schinke, ya que el rango de
simulación queda completamente cubierto.

También noten que `τₚ` del emisor **no** viene en la Tabla A.1 de la
semilla (solo asigna `τ_SRH` de volumen); se declaró 1 µs como valor
típico de un emisor n⁺ fuertemente dopado — coméntenlo en la
presentación como una decisión de modelamiento propia.

## Fichas de librerías (para la diapositiva de la presentación)

| Librería | Qué modelo implementa aquí | Supuestos | Entradas → Salidas |
|---|---|---|---|
| **NumPy** | Álgebra vectorial: mallas de λ y x, exponenciales de Beer-Lambert, cosh/sinh de la colección | Ninguno físico (herramienta numérica) | Arrays de parámetros → arrays de campos físicos |
| **SciPy (`optimize.brentq`)** | Resuelve la ecuación **implícita** del diodo J=J₀[exp((V-RsJ)/nVt)-1]+(V-RsJ)/Rp-JL, punto a punto | La raíz es única en el intervalo de búsqueda (monotonía del residuo en J); se amplía el intervalo automáticamente si no la contiene | (V, J₀, n, T, Rs, Rp, JL) → J(V) |
| **Plotly (`graph_objects`)** | Todos los gráficos interactivos (zoom, hover) y la animación del barrido J-V/P-V vía `Frames` | — (visualización) | Arrays físicos → gráfico interactivo/animado |
| **Streamlit** | Capa de interfaz web: sidebar, pestañas, `session_state` compartido, `components.v1.html` para inyectar el Canvas/JS de fotones | Reejecuta el script completo en cada interacción (arquitectura reactiva) | Interacción del usuario → recomputación de `fisica.py` → render |
| **HTML5 Canvas + JavaScript** (embebido) | Animación de fotones cayendo y absorbiéndose (muestreo Monte Carlo de la ley de Beer-Lambert, hecho en el navegador para que sea fluido) | Profundidad de absorción muestreada como `-ln(rand)/α(λ)`, consistente con P(absorción en x)∝α·e^(−αx) | α(λ) precalculado en Python (tabla de 46 puntos) → interpolación lineal en JS |
