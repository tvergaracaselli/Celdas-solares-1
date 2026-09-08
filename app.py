# -*- coding: utf-8 -*-
"""
app.py — Laboratorio virtual de caracterización de una celda p-n de silicio
(Problema 2.2, Proyecto 1 "Celdas Solares Fotovoltaicas", UAI 2026-2)

Arquitectura:
    constantes.py -> todas las constantes físicas y parámetros de semilla
    fisica.py     -> modelo físico puro (óptica, colección, diodo, temperatura)
    app.py (este) -> capa de interfaz Streamlit: sidebar, pestañas, animaciones

Estado compartido entre pestañas: st.session_state guarda todos los
parámetros físicos (geometría, dopajes, Sf/Sr, τ, Rs/Rp, malla frontal,
defectos). Lo que el usuario cambia en una pestaña se refleja de
inmediato en las demás, porque todas leen del mismo session_state.
"""
import json
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

import constantes as c
import fisica as f

st.set_page_config(page_title="Celda p-n de Silicio — Laboratorio Virtual",
                    layout="wide", initial_sidebar_state="expanded")

# ============================================================
# ESTADO COMPARTIDO (valores por defecto = semilla S = 3)
# ============================================================
DEFAULTS = dict(
    NA=c.NA_BASE_DEFAULT, ND=c.ND_EMISOR_DEFAULT,
    dn_um=c.D_N_EMISOR_UM, Wp_um=c.W_P_BASE_UM_DEFAULT,
    tau_n_us=c.TAU_SRH_VOLUMEN_US_DEFAULT, tau_p_us=c.TAU_P_EMISOR_US_DEFAULT,
    Sf=c.S_FRONTAL_CM_S_DEFAULT, Sr=1.0e2,
    T_C=c.T_OPERACION_C_DEFAULT,
    modo_R="fresnel", reflector_trasero=True,
    lambda_perfil=550.0, lambda_iqe_mapa=550.0,
    Rs_extra=0.0, Rp=c.RP_BASE_OHM_CM2, n_ideal=1.0, irradiancia_soles=1.0,
    num_dedos=c.NUMERO_DEDOS_BASE, ancho_dedo_um=c.ANCHO_DEDO_BASE_UM,
    defecto_activo=False, defecto_filas=(2, 4), defecto_cols=(2, 4),
    defecto_tau_n_us=5.0, dedo_roto_col=None,
    anim_modo="arcoiris",
)
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)

S = st.session_state  # atajo


# ============================================================
# SIDEBAR — parámetros físicos (compartidos por todas las pestañas)
# ============================================================
with st.sidebar:
    st.markdown("## ⚙️ Parámetros físicos")
    st.caption(f"Semilla asignada **S = {c.SEMILLA_S}** (Tabla A.1, Anexo A) — "
               "estos son los valores por defecto y los usados en Validación.")
    st.info(
        f"**NA (base p)** = {c.NA_BASE_DEFAULT:.1e} cm⁻³  \n"
        f"**ND (emisor n)** = {c.ND_EMISOR_DEFAULT:.1e} cm⁻³  \n"
        f"**τ_SRH volumen** = {c.TAU_SRH_VOLUMEN_US_DEFAULT:.0f} µs  \n"
        f"**S_frontal** = {c.S_FRONTAL_CM_S_DEFAULT:.0e} cm/s  \n"
        f"**T operación** = {c.T_OPERACION_C_DEFAULT:.0f} °C"
    )

    st.markdown("### Geometría")
    S["dn_um"] = st.slider("Espesor emisor dₙ [µm]", 0.2, 10.0, S["dn_um"], 0.1)
    S["Wp_um"] = st.slider("Espesor base W_p [µm]", c.W_P_BASE_MIN_UM, c.W_P_BASE_MAX_UM, S["Wp_um"], 5.0)

    st.markdown("### Dopajes")
    S["NA"] = st.select_slider("N_A base p [cm⁻³]", options=[1e14,3e14,1e15,3e15,1e16,3e16,1e17],
                                value=min([1e14,3e14,1e15,3e15,1e16,3e16,1e17], key=lambda z: abs(z-S["NA"])),
                                format_func=lambda z: f"{z:.0e}")
    S["ND"] = st.select_slider("N_D emisor n [cm⁻³]", options=[1e18,3e18,1e19,3e19,1e20],
                                value=min([1e18,3e18,1e19,3e19,1e20], key=lambda z: abs(z-S["ND"])),
                                format_func=lambda z: f"{z:.0e}")

    st.markdown("### Óptica")
    S["modo_R"] = st.radio("Reflectancia frontal R(λ)", ["fresnel", "fijo"],
                            index=0 if S["modo_R"] == "fresnel" else 1, horizontal=True)
    S["reflector_trasero"] = st.checkbox("Reflector trasero de aluminio activo", S["reflector_trasero"])

    st.markdown("### Recombinación / colección")
    S["Sf"] = st.select_slider("S frontal [cm/s]", options=[10,1e2,1e3,1e4,1e5,1e6],
                                value=min([10,1e2,1e3,1e4,1e5,1e6], key=lambda z: abs(z-S["Sf"])),
                                format_func=lambda z: f"{z:.0e}")
    S["Sr"] = st.select_slider("S trasera [cm/s]", options=[10,1e2,1e3,1e4,1e5,1e6],
                                value=min([10,1e2,1e3,1e4,1e5,1e6], key=lambda z: abs(z-S["Sr"])),
                                format_func=lambda z: f"{z:.0e}")
    S["tau_n_us"] = st.slider("τₙ volumen (base) [µs]", 0.1, 1000.0, S["tau_n_us"])
    S["tau_p_us"] = st.slider("τₚ emisor [µs]", 0.1, 1000.0, S["tau_p_us"])

    st.markdown("### Diodo eléctrico")
    S["Rs_extra"] = st.slider("Rs adicional [Ω·cm²]", 0.0, 2.0, S["Rs_extra"], 0.05)
    S["Rp"] = st.select_slider("Rp [Ω·cm²]", options=[10,1e2,1e3,1e4,1e5,1e6],
                                value=min([10,1e2,1e3,1e4,1e5,1e6], key=lambda z: abs(z-S["Rp"])),
                                format_func=lambda z: f"{z:.0e}")
    S["n_ideal"] = st.slider("Factor de idealidad n", 1.0, 2.0, S["n_ideal"], 0.05)
    S["irradiancia_soles"] = st.slider("Irradiancia [soles]", 0.1, 1.5, S["irradiancia_soles"], 0.05)
    S["T_C"] = st.slider("Temperatura de operación [°C]", 15.0, 75.0, S["T_C"], 1.0)

    st.markdown("### Malla frontal de plata")
    S["num_dedos"] = st.slider("N° de dedos", 5, 100, S["num_dedos"])
    S["ancho_dedo_um"] = st.slider("Ancho de dedo [µm]", 20.0, 200.0, S["ancho_dedo_um"])

    st.caption("Estado compartido: lo que cambias acá se refleja en las 5 pestañas.")


# ============================================================
# FÍSICA COMÚN (recalculada en cada rerun a partir de session_state)
# ============================================================
T_K = S["T_C"] + 273.15
W_total_um = S["dn_um"] + S["Wp_um"]

Dp = f.coef_difusion(T_K, c.MU_P_EMISOR_N_300K)
Dn = f.coef_difusion(T_K, c.MU_N_BASE_P_300K)
Lp_cm = f.longitud_difusion(Dp, S["tau_p_us"]); Lp_um = Lp_cm * 1e4
Ln_cm = f.longitud_difusion(Dn, S["tau_n_us"]); Ln_um = Ln_cm * 1e4

Psi0 = f.potencial_juntura(S["NA"], S["ND"], c.NI_300K, T_K)
Wdep_cm = f.ancho_zona_deplecion(Psi0, S["NA"], S["ND"]); Wdep_um = Wdep_cm * 1e4
# Reparto ASIMÉTRICO de la deplección (neutralidad de carga NA·xp=ND·xn):
# como NA << ND, la deplección se hunde casi toda en la base (xp_lado_n es
# chico, xp_lado_p es grande). xn_um/xp_um son las posiciones absolutas
# (medidas desde x=0, la superficie) donde empieza/termina la deplección.
_xn_lado, _xp_lado = f.reparto_zona_deplecion(Wdep_um, S["NA"], S["ND"])
xn_um = max(S["dn_um"] - _xn_lado, 1e-4)
xp_um = min(S["dn_um"] + _xp_lado, W_total_um - 1e-4)
if xp_um <= xn_um:
    xp_um = xn_um + 1e-4

wl_grid = np.linspace(300.0, 1200.0, 500)
alpha_grid = f.alpha_silicio(wl_grid)
R_grid = f.reflectancia_frontal(wl_grid, modo=S["modo_R"])
P_lambda, phi0_grid = f.espectro_y_flujo_fotones(wl_grid)

EQE, IQE = f.calcular_EQE_IQE_preciso(
    wl_grid, alpha_grid, R_grid, phi0_grid,
    xn_um, xp_um, W_total_um, Lp_um, Ln_um, Dp, Dn, S["Sf"], S["Sr"]
)
JL_A_cm2 = c.Q * np.trapezoid(phi0_grid * EQE, wl_grid)
J0_A_cm2 = f.corriente_saturacion_J0(S["NA"], S["ND"], c.NI_300K, Dn, Ln_cm, Dp, Lp_cm)


def wavelength_to_hex(wl):
    """Aproximación visual del color asociado a una longitud de onda
    (algoritmo clásico de Dan Bruton). Solo para representación gráfica:
    por debajo de 380 nm y por sobre 750 nm no hay color perceptible
    real, se extrapola para que la animación siga siendo legible."""
    wl = float(np.clip(wl, 380, 750))
    if wl < 440: R, G, B = -(wl - 440) / (440 - 380), 0.0, 1.0
    elif wl < 490: R, G, B = 0.0, (wl - 440) / (490 - 440), 1.0
    elif wl < 510: R, G, B = 0.0, 1.0, -(wl - 510) / (510 - 490)
    elif wl < 580: R, G, B = (wl - 510) / (580 - 510), 1.0, 0.0
    elif wl < 645: R, G, B = 1.0, -(wl - 645) / (645 - 580), 0.0
    else: R, G, B = 1.0, 0.0, 0.0
    return "#%02x%02x%02x" % (int(255*R), int(255*G), int(255*B))


# ============================================================
# TABS
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🔆 1. Absorción y Generación",
    "🎯 2. Eficiencia Cuántica (EQE/IQE)",
    "⚡ 3. Curva I-V",
    "🧩 4. Mapa de Sectores y Defectos",
    "✅ 5. Validación",
    "🎬 6. Resumen animado",
])

st.markdown("""
<style>
div[data-testid="stMetricValue"] { font-size: 1.4rem; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# TAB 1 — ABSORCIÓN Y GENERACIÓN
# ------------------------------------------------------------------
with tab1:
    st.subheader("Fotones cayendo sobre el silicio: dónde se absorbe cada color")
    colA, colB = st.columns([1, 1])
    with colA:
        S["lambda_perfil"] = st.slider("λ para el perfil G(x) [nm]", 300.0, 1200.0, S["lambda_perfil"], 5.0, key="l1")
    with colB:
        S["anim_modo"] = st.radio("Animación", ["arcoiris (varios λ)", "un solo λ (el del slider)"],
                                   index=0 if S["anim_modo"] == "arcoiris" else 1, horizontal=True)
        S["anim_modo"] = "arcoiris" if S["anim_modo"].startswith("arcoiris") else "unico"

    # --- Animación de fotones (HTML/JS, movimiento real) ---
    alpha_um_lookup = (f.alpha_silicio(np.linspace(300, 1200, 46)) * 1e-4).tolist()  # cm^-1 -> um^-1
    wl_lookup = np.linspace(300, 1200, 46).tolist()
    R_lookup = f.reflectancia_frontal(np.linspace(300, 1200, 46), modo=S["modo_R"]).tolist()
    colores_lookup = [wavelength_to_hex(wl) for wl in wl_lookup]
    single_wl = S["lambda_perfil"]
    single_color = wavelength_to_hex(single_wl)
    single_alpha_um = float(f.alpha_silicio(np.array([single_wl]))[0] * 1e-4)

    html_photons = f"""
<div style="background:#0b0e14;border-radius:10px;padding:10px">
<canvas id="cv" width="900" height="360" style="width:100%;display:block;border-radius:8px;"></canvas>
</div>
<script>
const wlLookup = {json.dumps(wl_lookup)};
const alphaLookup = {json.dumps(alpha_um_lookup)};   // 1/um
const colorLookup = {json.dumps(colores_lookup)};
const modo = "{S['anim_modo']}";
const singleColor = "{single_color}";
const singleAlpha = {single_alpha_um};
const W_total_um = {W_total_um};
const dn_um = {S['dn_um']};

function interp(x, xs, ys){{
  if(x<=xs[0]) return ys[0];
  if(x>=xs[xs.length-1]) return ys[ys.length-1];
  for(let i=0;i<xs.length-1;i++){{
    if(x>=xs[i] && x<=xs[i+1]){{
      const t=(x-xs[i])/(xs[i+1]-xs[i]);
      return ys[i]+t*(ys[i+1]-ys[i]);
    }}
  }}
  return ys[ys.length-1];
}}

const cv = document.getElementById('cv');
const ctx = cv.getContext('2d');
const W = cv.width, H = cv.height;
const blockTop = 46, blockBottom = H - 46;
const blockH = blockBottom - blockTop;
const xnUmT1 = {xn_um}, xpUmT1 = {xp_um};

// --- ESCALA VERTICAL COMPRIMIDA POR ZONAS ---
// El emisor real mide ~{S['dn_um']:.1f} µm contra ~{S['Wp_um']:.0f} µm de la base:
// a escala real el emisor sería invisible (una línea). Por eso cada zona
// (emisor / deplección / base) recibe una banda de tamaño FIJO en pantalla,
// sin importar su espesor físico real. Esto se declara explícitamente: no es
// una distorsión oculta, es una lupa para que las 3 zonas se vean.
const fracEmisor = 0.24, fracDeplecion = 0.10; // el resto (0.66) es la base
const depthBreaks = [0, xnUmT1, xpUmT1, W_total_um];
const fracBreaks = [0, fracEmisor, fracEmisor+fracDeplecion, 1.0];

function fracOfDepth(x_um){{
  if(x_um <= depthBreaks[0]) return 0;
  if(x_um >= depthBreaks[3]) return 1;
  for(let i=0;i<3;i++){{
    if(x_um>=depthBreaks[i] && x_um<=depthBreaks[i+1]){{
      const t=(x_um-depthBreaks[i])/Math.max(depthBreaks[i+1]-depthBreaks[i],1e-9);
      return fracBreaks[i]+t*(fracBreaks[i+1]-fracBreaks[i]);
    }}
  }}
  return 1;
}}
function depthOfFrac(fr){{
  if(fr<=0) return 0;
  if(fr>=1) return depthBreaks[3];
  for(let i=0;i<3;i++){{
    if(fr>=fracBreaks[i] && fr<=fracBreaks[i+1]){{
      const t=(fr-fracBreaks[i])/Math.max(fracBreaks[i+1]-fracBreaks[i],1e-9);
      return depthBreaks[i]+t*(depthBreaks[i+1]-depthBreaks[i]);
    }}
  }}
  return depthBreaks[3];
}}
function yOfFrac(fr){{ return blockTop + fr*blockH; }}

let photons = [];
function spawnPhoton(){{
  let wl;
  if(modo === "arcoiris"){{
    wl = 380 + Math.random()*(720-380);
  }} else {{
    wl = {single_wl};
  }}
  let alpha_um = interp(wl, wlLookup, alphaLookup);
  let color = (modo==="arcoiris") ? colorFromWl(wl) : singleColor;
  let xAbs = -Math.log(Math.random())/Math.max(alpha_um,1e-6); // profundidad de absorcion [um]
  let transmitido = xAbs > W_total_um;
  photons.push({{
    x: 60 + Math.random()*(W-120),
    fracPos: -0.06,
    wl: wl, color: color,
    vfrac: 0.010 + Math.random()*0.004,
    fracAbs: transmitido ? 1.0 : fracOfDepth(xAbs),
    transmitido: transmitido,
    state: 'falling',
    burst: 0
  }});
}}
function colorFromWl(wl){{
  wl = Math.max(380, Math.min(750, wl));
  let R,G,B;
  if(wl<440){{R=-(wl-440)/(440-380);G=0;B=1;}}
  else if(wl<490){{R=0;G=(wl-440)/(490-440);B=1;}}
  else if(wl<510){{R=0;G=1;B=-(wl-510)/(510-490);}}
  else if(wl<580){{R=(wl-510)/(580-510);G=1;B=0;}}
  else if(wl<645){{R=1;G=-(wl-645)/(645-580);B=0;}}
  else {{R=1;G=0;B=0;}}
  return `rgb(${{Math.round(255*R)}},${{Math.round(255*G)}},${{Math.round(255*B)}})`;
}}

let sparks = [];
let nAbs=0, nTrans=0;
function step(){{
  ctx.clearRect(0,0,W,H);
  // silicio
  ctx.fillStyle = "#20242c";
  ctx.fillRect(30, blockTop, W-60, blockH);

  // --- bandas de zona (tamaño fijo en pantalla, ver nota de escala) ---
  const yE0=yOfFrac(0), yE1=yOfFrac(fracEmisor), yD1=yOfFrac(fracEmisor+fracDeplecion), yB1=yOfFrac(1);
  ctx.fillStyle="rgba(99,179,237,0.16)"; ctx.fillRect(30, yE0, W-60, yE1-yE0);
  ctx.fillStyle="rgba(246,173,85,0.30)"; ctx.fillRect(30, yE1, W-60, yD1-yE1);
  ctx.fillStyle="rgba(104,211,145,0.14)"; ctx.fillRect(30, yD1, W-60, yB1-yD1);
  ctx.strokeStyle = "#4a5568"; ctx.strokeRect(30, blockTop, W-60, blockH);
  ctx.strokeStyle="#f6ad55"; ctx.setLineDash([6,4]);
  ctx.beginPath(); ctx.moveTo(30,yE1); ctx.lineTo(W-30,yE1); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(30,yD1); ctx.lineTo(W-30,yD1); ctx.stroke();
  ctx.setLineDash([]);

  ctx.font="bold 13px sans-serif";
  ctx.fillStyle="#90cdf4"; ctx.fillText("EMISOR n  (dn=" + dn_um.toFixed(1) + " µm)", 36, (yE0+yE1)/2+5);
  ctx.fillStyle="#f6ad55"; ctx.fillText("DEPLECCIÓN", 36, (yE1+yD1)/2+5);
  ctx.fillStyle="#9ae6b4"; ctx.fillText("BASE p  (Wp=" + (W_total_um-dn_um).toFixed(0) + " µm)", 36, yD1+22);
  ctx.font="11px sans-serif"; ctx.fillStyle="#718096";
  ctx.fillText("(escala vertical comprimida por zona para que las 3 se vean — no es a escala real)", 36, blockTop-10);
  ctx.fillStyle="#a0aec0";
  ctx.fillText("superficie x=0", 36, blockTop+12);
  ctx.fillText("contacto trasero x=W=" + W_total_um.toFixed(0) + "µm", 36, blockBottom+16);

  if(Math.random() < 0.10) spawnPhoton();

  photons.forEach(p => {{
    if(p.state === 'falling'){{
      p.fracPos += p.vfrac;
      let yy = yOfFrac(Math.min(Math.max(p.fracPos,0),1.15));
      ctx.beginPath(); ctx.arc(p.x, yy, 3.2, 0, 7); ctx.fillStyle = p.color; ctx.fill();
      ctx.beginPath(); ctx.arc(p.x, yy, 6, 0, 7); ctx.strokeStyle = p.color; ctx.globalAlpha=0.35; ctx.stroke(); ctx.globalAlpha=1;
      if(!p.transmitido && p.fracPos >= p.fracAbs && p.fracPos > 0){{
        p.state = 'absorbed'; nAbs++;
        sparks.push({{x:p.x, y:yy, r:2, life:1.0, hole:{{y:yy, vy:1.2}}, elec:{{y:yy, vy:-1.4}}}});
      }}
      if(p.transmitido && p.fracPos >= 1.15){{ p.state='transmitted'; nTrans++; }}
    }}
  }});
  photons = photons.filter(p => p.state==='falling');

  sparks.forEach(s => {{
    s.r += 1.4; s.life -= 0.035;
    ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, 7);
    ctx.strokeStyle = `rgba(255,255,180,${{Math.max(s.life,0)}})`; ctx.lineWidth=2; ctx.stroke();
    // hueco (azul, sube) y electron (rojo, baja) separandose por el campo si estan cerca de la juntura
    s.hole.y += s.hole.vy; s.elec.y += s.elec.vy;
    ctx.beginPath(); ctx.arc(s.x-5, s.hole.y, 2.4, 0, 7); ctx.fillStyle=`rgba(99,179,237,${{Math.max(s.life,0)}})`; ctx.fill();
    ctx.beginPath(); ctx.arc(s.x+5, s.elec.y, 2.4, 0, 7); ctx.fillStyle=`rgba(252,129,129,${{Math.max(s.life,0)}})`; ctx.fill();
  }});
  sparks = sparks.filter(s => s.life > 0);

  ctx.font="12px sans-serif"; ctx.fillStyle="#e2e8f0";
  ctx.fillText(`Absorbidos: ${{nAbs}}   Transmitidos (atravesaron toda la celda): ${{nTrans}}`, 30, H-6);

  requestAnimationFrame(step);
}}
step();
</script>
"""
    components.html(html_photons, height=410, scrolling=False)
    st.caption("Puntos de color = fotones cayendo (color ≈ longitud de onda). Cada uno se absorbe a una "
               "profundidad muestreada de la ley de Beer-Lambert (P(absorción a x) ∝ α e^(−αx)): el azul se "
               "frena casi en el emisor, el rojo/IR suele llegar hasta la base o incluso atravesarla entera "
               "(fotón transmitido, sigue cayendo más allá del contacto trasero — se pierde, no genera par). "
               "Al absorberse, aparece el par electrón (rojo, hacia el contacto n) - hueco (azul, hacia el "
               "contacto p). Las bandas de emisor/deplección/base están dibujadas con **tamaño fijo en "
               "pantalla**, no a escala real, para que las tres se puedan ver a la vez.")

    c1, c2 = st.columns(2)
    with c1:
        x_perfil = np.linspace(0, W_total_um, 600)
        G_perfil = f.tasa_generacion(x_perfil, phi0_grid, R_grid, alpha_grid)
        i_wl = int(np.argmin(np.abs(wl_grid - S["lambda_perfil"])))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x_perfil, y=G_perfil[:, i_wl], mode="lines",
                                  line=dict(color=single_color, width=3), name="G(x)"))
        fig.add_vline(x=S["dn_um"], line_dash="dot", line_color="orange",
                      annotation_text="juntura (xj=dn)")
        fig.update_layout(title=f"Tasa de generación G(x) a λ={S['lambda_perfil']:.0f} nm",
                           xaxis_title="Profundidad x [µm]", yaxis_title="G [cm⁻³ s⁻¹ nm⁻¹]",
                           height=380, template="plotly_dark")
        st.plotly_chart(fig, width="stretch")
    with c2:
        prof_abs_um = np.clip(1.0 / np.maximum(alpha_grid, 1e-8) * 1e4, 0, 500)
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=wl_grid, y=prof_abs_um, mode="lines", line=dict(color="#68d391", width=3)))
        fig2.add_hline(y=W_total_um, line_dash="dash", line_color="white",
                       annotation_text=f"espesor celda W={W_total_um:.0f} µm")
        fig2.update_layout(title="Profundidad de absorción 1/α(λ) vs espesor de la celda",
                           xaxis_title="λ [nm]", yaxis_title="1/α [µm]", yaxis_type="log",
                           height=380, template="plotly_dark")
        st.plotly_chart(fig2, width="stretch")

    st.markdown("##### Mapa 2D de generación G(x,λ) — dónde se absorbe cada color")
    x_mapa = np.linspace(0, W_total_um, 220)
    G_mapa = f.tasa_generacion(x_mapa, phi0_grid, R_grid, alpha_grid)
    fig3 = go.Figure(data=go.Heatmap(z=np.log10(np.maximum(G_mapa, 1e-6)).T, x=x_mapa, y=wl_grid,
                                      colorscale="Inferno", colorbar_title="log₁₀G"))
    fig3.add_hline(y=S["lambda_perfil"], line_color="cyan", line_dash="dot")
    fig3.add_vline(x=S["dn_um"], line_color="orange", line_dash="dot")
    fig3.update_layout(xaxis_title="Profundidad x [µm]", yaxis_title="λ [nm]", height=420, template="plotly_dark")
    st.plotly_chart(fig3, width="stretch")

    st.markdown("##### Balance de fotones de Beer-Lambert (validación V1)")
    frac_r, frac_a, frac_t = f.balance_fotones(R_grid, alpha_grid, W_total_um)
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(x=wl_grid, y=frac_r, stackgroup="one", name="Reflejada", line_color="#f6ad55"))
    fig4.add_trace(go.Scatter(x=wl_grid, y=frac_a, stackgroup="one", name="Absorbida en Si", line_color="#68d391"))
    fig4.add_trace(go.Scatter(x=wl_grid, y=frac_t, stackgroup="one", name="Transmitida", line_color="#63b3ed"))
    fig4.update_layout(xaxis_title="λ [nm]", yaxis_title="Fracción de fotones", height=340, template="plotly_dark")
    st.plotly_chart(fig4, width="stretch")
    suma = frac_r + frac_a + frac_t
    st.caption(f"Suma reflejada+absorbida+transmitida: mín={suma.min():.4f}, máx={suma.max():.4f} "
               "(debe ser ≈1 para todo λ — ver pestaña Validación).")

# ------------------------------------------------------------------
# TAB 2 — EQE / IQE
# ------------------------------------------------------------------
with tab2:
    st.subheader("La vida de un portador: generación, difusión, ¿colección o recombinación?")
    st.caption("Cada punto nace como un par electrón-hueco a la profundidad donde se absorbió un fotón. "
               "Solo el portador minoritario importa para la colección (hueco si nace en el emisor, "
               "electrón si nace en la base): difunde al azar y, o llega a la juntura y se colecta "
               "(destello dorado, cuenta como corriente), o se recombina antes de llegar (se apaga, "
               "energía perdida como calor). La probabilidad de cada desenlace es exactamente fc(x).")

    # --- lookup tables para la animación ---
    x_life = np.linspace(0, W_total_um, 90)
    fc_life = f.prob_coleccion_total(x_life, xn_um, xp_um, W_total_um, Lp_um, Ln_um, Dp, Dn, S["Sf"], S["Sr"])
    G_x_full = f.tasa_generacion(x_life, phi0_grid, R_grid, alpha_grid)
    Gtot_life = np.trapezoid(G_x_full, wl_grid, axis=1)
    Gtot_life = np.maximum(Gtot_life, 0)
    cdf_life = np.cumsum(Gtot_life)
    cdf_life = cdf_life / cdf_life[-1] if cdf_life[-1] > 0 else np.linspace(0, 1, len(cdf_life))

    html_vida = f"""
<div style="background:#0b0e14;border-radius:10px;padding:10px">
<canvas id="cv2" width="900" height="380" style="width:100%;display:block;border-radius:8px;"></canvas>
</div>
<script>
const xLife = {json.dumps(x_life.tolist())};
const fcLife = {json.dumps(fc_life.tolist())};
const cdfLife = {json.dumps(cdf_life.tolist())};
const xnUm = {xn_um}, xpUm = {xp_um}, Wum = {W_total_um};

function interp2(x, xs, ys){{
  if(x<=xs[0]) return ys[0];
  if(x>=xs[xs.length-1]) return ys[ys.length-1];
  for(let i=0;i<xs.length-1;i++){{
    if(x>=xs[i] && x<=xs[i+1]){{
      const t=(x-xs[i])/(xs[i+1]-xs[i]);
      return ys[i]+t*(ys[i+1]-ys[i]);
    }}
  }}
  return ys[ys.length-1];
}}
function sampleX0(){{
  const r = Math.random();
  for(let i=0;i<cdfLife.length-1;i++){{
    if(r>=cdfLife[i] && r<=cdfLife[i+1]){{
      const t=(r-cdfLife[i])/Math.max(cdfLife[i+1]-cdfLife[i],1e-9);
      return xLife[i]+t*(xLife[i+1]-xLife[i]);
    }}
  }}
  return xLife[xLife.length-1];
}}

const cv=document.getElementById('cv2'); const ctx=cv.getContext('2d');
const W=cv.width,H=cv.height;
const topY=40,bottomY=H-50; const blockH=bottomY-topY;
// Escala comprimida por zona (igual criterio que la Pestaña 1): el emisor
// real es una franja delgadísima frente a la base, así que cada zona recibe
// una banda de tamaño FIJO en pantalla para que las 3 se vean a la vez.
const fracEmi2=0.22, fracDep2=0.10;
const depthBr2=[0,xnUm,xpUm,Wum], fracBr2=[0,fracEmi2,fracEmi2+fracDep2,1.0];
function yOf(x_um){{
  if(x_um<=depthBr2[0]) return topY;
  if(x_um>=depthBr2[3]) return topY+blockH;
  for(let i=0;i<3;i++){{
    if(x_um>=depthBr2[i] && x_um<=depthBr2[i+1]){{
      const t=(x_um-depthBr2[i])/Math.max(depthBr2[i+1]-depthBr2[i],1e-9);
      return topY+(fracBr2[i]+t*(fracBr2[i+1]-fracBr2[i]))*blockH;
    }}
  }}
  return topY+blockH;
}}

let nGen=0,nCol=0,nRec=0;
let carriers=[];
function spawn(){{
  const x0 = sampleX0();
  const fc0 = interp2(x0, xLife, fcLife);
  const willCollect = Math.random() < fc0;
  let target, tipo, colorViva, dirSigno;
  if(x0 < xnUm){{ target = xnUm; tipo='hueco'; colorViva='#63b3ed'; dirSigno=1; }}
  else if(x0 > xpUm){{ target = xpUm; tipo='electron'; colorViva='#fc8181'; dirSigno=-1; }}
  else {{ target = x0; tipo='par'; colorViva='#f6e05e'; dirSigno=0; }}
  const distTotal = Math.abs(target-x0) || 1;
  const fracFinal = willCollect ? 1.0 : (0.15+Math.random()*0.65);
  nGen++;
  carriers.push({{x0, target, x:60+Math.random()*(W-120), depth:x0, tipo, colorViva,
                  willCollect, fracFinal, prog:0, distTotal, alive:true, burst:0}});
}}

function step(){{
  ctx.clearRect(0,0,W,H);
  ctx.fillStyle="#20242c"; ctx.fillRect(30,topY,W-60,blockH);
  ctx.strokeStyle="#4a5568"; ctx.strokeRect(30,topY,W-60,blockH);
  // bandas emisor / deplecion / base (tamaño fijo en pantalla, ver nota Pestaña 1)
  ctx.fillStyle="rgba(99,179,237,0.14)"; ctx.fillRect(31, yOf(0), W-62, yOf(xnUm)-yOf(0));
  ctx.fillStyle="rgba(246,173,85,0.28)"; ctx.fillRect(31, yOf(xnUm), W-62, yOf(xpUm)-yOf(xnUm));
  ctx.fillStyle="rgba(104,211,145,0.12)"; ctx.fillRect(31, yOf(xpUm), W-62, yOf(Wum)-yOf(xpUm));
  ctx.fillStyle="#90cdf4"; ctx.font="bold 12px sans-serif";
  ctx.fillText("emisor (n)", 36, (yOf(0)+yOf(xnUm))/2+4);
  ctx.fillStyle="#f6ad55"; ctx.fillText("deplección / juntura", 36, (yOf(xnUm)+yOf(xpUm))/2+4);
  ctx.fillStyle="#9ae6b4"; ctx.fillText("base (p)", 36, yOf(xpUm)+18);

  if(Math.random()<0.16) spawn();

  carriers.forEach(p=>{{
    if(!p.alive) return;
    p.prog += 0.02 + Math.random()*0.01;
    const wiggle = Math.sin(p.prog*14 + p.x)*3;
    const fracNow = Math.min(p.prog, p.fracFinal);
    const depthNow = p.x0 + (p.target-p.x0)*Math.min(fracNow/p.fracFinal,1);
    const yy = yOf(depthNow);
    if(p.prog < p.fracFinal){{
      ctx.beginPath(); ctx.arc(p.x+wiggle, yy, 3.4, 0, 7); ctx.fillStyle=p.colorViva; ctx.fill();
    }} else if(p.burst < 1.0){{
      p.burst += 0.10;
      const col = p.willCollect ? `rgba(246,224,94,${{1-p.burst}})` : `rgba(160,174,192,${{1-p.burst}})`;
      ctx.beginPath(); ctx.arc(p.x+wiggle, yy, 3+p.burst*10, 0, 7); ctx.strokeStyle=col; ctx.lineWidth=2; ctx.stroke();
      if(p.burst < 0.11){{ if(p.willCollect) nCol++; else nRec++; }}
    }} else {{ p.alive=false; }}
  }});
  carriers = carriers.filter(p=>p.alive);

  ctx.fillStyle="#e2e8f0"; ctx.font="13px sans-serif";
  const pct = nGen>0 ? (100*nCol/nGen).toFixed(1) : "0.0";
  ctx.fillText(`Generados: ${{nGen}}   Colectados: ${{nCol}} (${{pct}}%)   Recombinados: ${{nRec}}`, 30, H-16);

  requestAnimationFrame(step);
}}
step();
</script>
"""
    components.html(html_vida, height=400, scrolling=False)

    st.subheader("Probabilidad de colección fc(x) y eficiencia cuántica")
    x_fc = np.linspace(0, W_total_um, 600)
    fc_x = f.prob_coleccion_total(x_fc, xn_um, xp_um, W_total_um, Lp_um, Ln_um, Dp, Dn, S["Sf"], S["Sr"])

    c1, c2 = st.columns([1, 1])
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x_fc, y=fc_x, mode="lines", line=dict(color="#f687b3", width=3)))
        fig.add_vrect(x0=0, x1=xn_um, fillcolor="#63b3ed", opacity=0.15, line_width=0, annotation_text="emisor")
        fig.add_vrect(x0=xn_um, x1=xp_um, fillcolor="#f6ad55", opacity=0.25, line_width=0, annotation_text="deplección")
        fig.add_vrect(x0=xp_um, x1=W_total_um, fillcolor="#68d391", opacity=0.15, line_width=0, annotation_text="base")
        fig.update_layout(title="Probabilidad de colección fc(x)", xaxis_title="x [µm]", yaxis_title="fc",
                           height=380, template="plotly_dark", yaxis_range=[0, 1.05])
        st.plotly_chart(fig, width="stretch")
    with c2:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=wl_grid, y=EQE, name="EQE(λ)", line=dict(color="#68d391", width=3)))
        fig2.add_trace(go.Scatter(x=wl_grid, y=IQE, name="IQE(λ)", line=dict(color="#f6ad55", width=3, dash="dot")))
        fig2.add_trace(go.Scatter(x=wl_grid, y=1 - R_grid, name="Cota física 1-R(λ)",
                                   line=dict(color="gray", dash="dash")))
        fig2.update_layout(title="EQE(λ) e IQE(λ)", xaxis_title="λ [nm]", yaxis_title="Eficiencia",
                            height=380, template="plotly_dark", yaxis_range=[0, 1.05])
        st.plotly_chart(fig2, width="stretch")

    st.markdown("##### Mapa de IQE local por sectores (grilla 8×8)")
    S["lambda_iqe_mapa"] = st.slider("λ del mapa de sectores [nm]", 300.0, 1200.0, S["lambda_iqe_mapa"], 5.0, key="l2")

    n_sec = 8
    tau_n_grid = np.full((n_sec, n_sec), S["tau_n_us"])
    Sf_grid = np.full((n_sec, n_sec), S["Sf"])
    if S["defecto_activo"]:
        r0, r1 = S["defecto_filas"]; c0, c1_ = S["defecto_cols"]
        tau_n_grid[r0:r1, c0:c1_] = S["defecto_tau_n_us"]
    if S["dedo_roto_col"] is not None:
        Sf_grid[:, S["dedo_roto_col"]] = S["Sf"] * 5  # dedo roto -> peor colección local (proxy)

    i_map = int(np.argmin(np.abs(wl_grid - S["lambda_iqe_mapa"])))
    alpha_1 = alpha_grid[i_map]; R_1 = R_grid[i_map]
    IQE_map = np.zeros((n_sec, n_sec))
    for i in range(n_sec):
        for j in range(n_sec):
            Lp_ij = f.longitud_difusion(Dp, S["tau_p_us"]) * 1e4
            Ln_ij = f.longitud_difusion(Dn, tau_n_grid[i, j]) * 1e4
            _EQE_ij, _IQE_ij = f.calcular_EQE_IQE_preciso(
                np.array([wl_grid[i_map]]), np.array([alpha_1]), np.array([R_1]), np.array([1.0]),
                xn_um, xp_um, W_total_um, Lp_ij, Ln_ij, Dp, Dn, Sf_grid[i, j], S["Sr"])
            IQE_map[i, j] = _IQE_ij[0]

    fig3 = go.Figure(data=go.Heatmap(z=IQE_map, colorscale="Viridis", zmin=0, zmax=1,
                                      colorbar_title="IQE local"))
    fig3.update_layout(title=f"IQE local a λ={S['lambda_iqe_mapa']:.0f} nm (8×8 sectores)",
                        height=420, template="plotly_dark")
    st.plotly_chart(fig3, width="stretch")
    if S["defecto_activo"] or S["dedo_roto_col"] is not None:
        st.caption("Este mapa ya refleja los defectos definidos en la pestaña 4 (contaminación / dedo roto).")

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**IQE en el rojo vs τₙ de volumen** (a λ fija en el infrarrojo cercano)")
        taus = np.geomspace(0.5, 1000, 25)
        wl_rojo = 950.0
        i_rojo = int(np.argmin(np.abs(wl_grid - wl_rojo)))
        iqe_vs_tau = []
        for t in taus:
            Ln_t = f.longitud_difusion(Dn, t) * 1e4
            _e, _i = f.calcular_EQE_IQE_preciso(np.array([wl_rojo]), np.array([alpha_grid[i_rojo]]),
                                                 np.array([R_grid[i_rojo]]), np.array([1.0]),
                                                 xn_um, xp_um, W_total_um, Lp_um, Ln_t, Dp, Dn, S["Sf"], S["Sr"])
            iqe_vs_tau.append(_i[0])
        figr = go.Figure(go.Scatter(x=taus, y=iqe_vs_tau, line=dict(color="#fc8181", width=3)))
        figr.update_layout(xaxis_title="τₙ volumen [µs]", yaxis_title=f"IQE a {wl_rojo:.0f} nm",
                            xaxis_type="log", height=320, template="plotly_dark")
        st.plotly_chart(figr, width="stretch")
    with c4:
        st.markdown("**IQE en el azul vs Sf** (a λ fija cerca de la superficie)")
        Sfs = np.geomspace(10, 1e6, 25)
        wl_azul = 420.0
        i_azul = int(np.argmin(np.abs(wl_grid - wl_azul)))
        iqe_vs_sf = []
        for sfv in Sfs:
            _e, _i = f.calcular_EQE_IQE_preciso(np.array([wl_azul]), np.array([alpha_grid[i_azul]]),
                                                 np.array([R_grid[i_azul]]), np.array([1.0]),
                                                 xn_um, xp_um, W_total_um, Lp_um, Ln_um, Dp, Dn, sfv, S["Sr"])
            iqe_vs_sf.append(_i[0])
        figb = go.Figure(go.Scatter(x=Sfs, y=iqe_vs_sf, line=dict(color="#63b3ed", width=3)))
        figb.update_layout(xaxis_title="S frontal [cm/s]", yaxis_title=f"IQE a {wl_azul:.0f} nm",
                            xaxis_type="log", height=320, template="plotly_dark")
        st.plotly_chart(figb, width="stretch")
    st.caption("Reproduce cualitativamente la lámina 30 de la Unidad 3: el rojo mejora con τ de volumen "
               "(colecta desde más profundo en la base); el azul depende solo del emisor y de la superficie frontal.")

# ------------------------------------------------------------------
# TAB 3 — CURVA I-V (animada)
# ------------------------------------------------------------------
with tab3:
    st.subheader("Cómo se forma la juntura p-n")
    st.caption("Bloque p (base, poco dopada, NA={:.0e} cm⁻³) y bloque n (emisor, muy dopado, "
               "ND={:.0e} cm⁻³) se ponen en contacto. Los portadores móviles difunden y se recombinan "
               "cerca del contacto, dejando expuestos los iones fijos: eso es la zona de deplección. "
               "Como el emisor está mucho más dopado, necesita mucho menos ancho para exponer la misma "
               "carga — por eso la deplección se hunde casi toda hacia la base (asimetría real, no "
               "decorativa: viene de NA·xₚ=ND·xₙ).".format(S["NA"], S["ND"]))

    n_ion_p = int(np.clip(np.interp(np.log10(S["NA"]), [14, 17], [6, 46]), 6, 46))
    n_ion_n = int(np.clip(np.interp(np.log10(S["ND"]), [17, 20], [10, 60]), 10, 60))
    frac_xn_visual = min(max(_xn_lado / Wdep_um, 0.03), 0.5) if Wdep_um > 0 else 0.1

    html_juntura = f"""
<div style="background:#0b0e14;border-radius:10px;padding:10px">
<canvas id="cvj" width="900" height="330" style="width:100%;display:block;border-radius:8px;"></canvas>
</div>
<script>
const nIonP = {n_ion_p}, nIonN = {n_ion_n};
const fracXn = {frac_xn_visual};
const psi0 = {Psi0:.4f};
const cv=document.getElementById('cvj'); const ctx=cv.getContext('2d');
const W=cv.width,H=cv.height, midY=H/2+10;
const left=40,right=W-40; const midX=(left+right)/2;

function rnd(a,b){{return a+Math.random()*(b-a);}}
let ionsP=[], ionsN=[], mobiles=[];
for(let i=0;i<nIonP;i++) ionsP.push({{x:rnd(left+10,midX-6), y:rnd(60,H-50)}});
for(let i=0;i<nIonN;i++) ionsN.push({{x:rnd(midX+6,right-10), y:rnd(60,H-50)}});
ionsP.forEach(ion=>mobiles.push({{x:ion.x,y:ion.y,tipo:'hueco',home:ion}}));
ionsN.forEach(ion=>mobiles.push({{x:ion.x,y:ion.y,tipo:'electron',home:ion}}));

const cicloMs = 7000;
const t0 = performance.now();

function draw(){{
  const t = ((performance.now()-t0) % cicloMs) / cicloMs; // 0..1
  ctx.clearRect(0,0,W,H);
  ctx.fillStyle="#a0aec0"; ctx.font="13px sans-serif";
  ctx.fillText("base p (NA={S['NA']:.0e} cm⁻³)", left, 30);
  ctx.fillText("emisor n (ND={S['ND']:.0e} cm⁻³)", midX+20, 30);

  let gap = 0, depW = 0, showField = false;
  if(t < 0.22){{
    gap = 40*(1-t/0.22);
  }} else if(t < 0.55){{
    gap = 0;
    const tt=(t-0.22)/0.33; depW = tt*(right-left)*0.28;
  }} else if(t < 0.9){{
    depW = (right-left)*0.28; showField = true;
  }} else {{
    const tt=(t-0.9)/0.10; depW = (1-tt)*(right-left)*0.28;
  }}

  const shift = gap/2;
  // bloques
  ctx.strokeStyle="#4a5568";
  ctx.strokeRect(left-shift, 50, midX-left-shift+ (gap>0?-4:0), H-100);
  ctx.strokeRect(midX+shift, 50, right-midX-shift, H-100);

  // zona de deplecion (asimetrica: fracXn hacia el lado n, resto hacia el p)
  if(depW>0.5){{
    const wN = depW*fracXn, wP = depW*(1-fracXn);
    ctx.fillStyle="rgba(246,173,85,0.25)";
    ctx.fillRect(midX-wP, 50, wP+wN, H-100);
    if(showField){{
      ctx.strokeStyle="#f6ad55"; ctx.lineWidth=2;
      ctx.beginPath(); ctx.moveTo(midX-wP+4, midY); ctx.lineTo(midX+wN-4, midY);
      ctx.lineTo(midX+wN-10, midY-5); ctx.moveTo(midX+wN-4,midY); ctx.lineTo(midX+wN-10,midY+5);
      ctx.stroke();
      ctx.fillStyle="#f6ad55"; ctx.font="12px sans-serif";
      ctx.fillText("Campo E   Ψ₀ ≈ " + psi0.toFixed(3) + " V", midX-wP, 45);
    }}
  }}

  // iones fijos (solo tras difusion, quedan al descubierto dentro de la zona)
  ionsP.forEach(ion=>{{
    const inDep = depW>0.5 && ion.x > midX - depW*(1-fracXn);
    ctx.beginPath(); ctx.arc(ion.x-shift, ion.y, 5, 0, 7);
    ctx.strokeStyle = inDep ? "#fc8181" : "#718096"; ctx.lineWidth=1.5; ctx.stroke();
    if(inDep){{ ctx.fillStyle="rgba(252,129,129,0.5)"; ctx.font="10px sans-serif"; ctx.fillText("-",ion.x-shift-3,ion.y+3); }}
  }});
  ionsN.forEach(ion=>{{
    const inDep = depW>0.5 && ion.x < midX + depW*fracXn;
    ctx.beginPath(); ctx.arc(ion.x+shift, ion.y, 5, 0, 7);
    ctx.strokeStyle = inDep ? "#63b3ed" : "#718096"; ctx.lineWidth=1.5; ctx.stroke();
    if(inDep){{ ctx.fillStyle="rgba(99,179,237,0.5)"; ctx.font="10px sans-serif"; ctx.fillText("+",ion.x+shift-3,ion.y+3); }}
  }});

  // portadores moviles: difunden hacia el centro y se recombinan si t esta en fase de difusion
  mobiles.forEach(m=>{{
    let targetX = m.home.x + (m.tipo==='hueco' ? shift*0 : shift*0);
    if(t<0.22){{ m.x = m.home.x + (m.tipo==='hueco'? -shift: shift); m.y=m.home.y; m.visible=true; }}
    else if(t<0.55){{
      const tt=(t-0.22)/0.33;
      const destX = m.tipo==='hueco' ? Math.min(m.home.x+tt*90, midX-6) : Math.max(m.home.x-tt*90, midX+6);
      m.x = m.home.x + (destX-m.home.x); m.y = m.home.y;
      const distToCenter = Math.abs(midX-m.x);
      m.visible = distToCenter > 8 + Math.random()*4;
    }} else {{ m.visible = false; }}
  }});
  mobiles.forEach(m=>{{
    if(!m.visible) return;
    ctx.beginPath(); ctx.arc(m.x, m.y, 3, 0, 7);
    ctx.fillStyle = m.tipo==='hueco' ? "#63b3ed" : "#fc8181";
    ctx.fill();
  }});

  requestAnimationFrame(draw);
}}
draw();
</script>
"""
    components.html(html_juntura, height=350, scrolling=False)

    st.subheader("Ensayo eléctrico: barrido de voltaje animado")
    malla = f.modelo_malla_frontal_plata(S["num_dedos"], S["ancho_dedo_um"])
    JL_con_sombra = malla["fraccion_iluminada"] * JL_A_cm2
    Rs_total = c.RS_BASE_OHM_CM2 + malla["Rs_malla_ohm_cm2"] + S["Rs_extra"]

    resultado = f.simular_celda_JV(JL_con_sombra, J0_A_cm2, T_K, S["irradiancia_soles"],
                                    S["n_ideal"], Rs_total, S["Rp"], n_puntos=250)
    V_arr, J_arr, P_arr = resultado["V_array_V"], resultado["J_array_A_cm2"] * 1e3, resultado["P_array_W_cm2"] * 1e3

    frames = []
    n_frames = 60
    idxs = np.linspace(0, len(V_arr) - 1, n_frames).astype(int)
    for k in idxs:
        frames.append(go.Frame(
            data=[go.Scatter(x=V_arr, y=J_arr, mode="lines", line=dict(color="#68d391", width=3)),
                  go.Scatter(x=[V_arr[k]], y=[J_arr[k]], mode="markers", marker=dict(color="#f6ad55", size=14)),
                  go.Scatter(x=V_arr, y=P_arr, mode="lines", line=dict(color="#63b3ed", width=3), xaxis="x2", yaxis="y2"),
                  go.Scatter(x=[V_arr[k]], y=[P_arr[k]], mode="markers", marker=dict(color="#f6ad55", size=14),
                             xaxis="x2", yaxis="y2")],
            name=str(k)))

    fig = go.Figure(
        data=[go.Scatter(x=V_arr, y=J_arr, mode="lines", line=dict(color="#68d391", width=3), name="J-V"),
              go.Scatter(x=[V_arr[0]], y=[J_arr[0]], mode="markers", marker=dict(color="#f6ad55", size=14), name="punto"),
              go.Scatter(x=V_arr, y=P_arr, mode="lines", line=dict(color="#63b3ed", width=3), name="P-V", xaxis="x2", yaxis="y2"),
              go.Scatter(x=[V_arr[0]], y=[P_arr[0]], mode="markers", marker=dict(color="#f6ad55", size=14), xaxis="x2", yaxis="y2")],
        frames=frames)
    fig.update_layout(
        template="plotly_dark", height=460,
        xaxis=dict(domain=[0, 0.46], title="V [V]"), yaxis=dict(title="J [mA/cm²]"),
        xaxis2=dict(domain=[0.54, 1.0], title="V [V]"), yaxis2=dict(title="P [mW/cm²]"),
        updatemenus=[dict(type="buttons", showactive=False, y=1.12, x=0.0,
                          buttons=[dict(label="▶ Reproducir barrido de V",
                                        method="animate",
                                        args=[None, dict(frame=dict(duration=40, redraw=True), fromcurrent=True)])])],
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")

    FF0 = f.FF0_empirico(resultado["Voc_V"], T_K)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Jsc", f"{resultado['Jsc_A_cm2']*1e3:.2f} mA/cm²")
    m2.metric("Voc", f"{resultado['Voc_V']*1e3:.1f} mV")
    m3.metric("FF", f"{resultado['FF']*100:.1f} %", f"FF₀ ideal={FF0*100:.1f}%")
    m4.metric("Pmax", f"{resultado['Pmax_W_cm2']*1e3:.2f} mW/cm²")
    m5.metric("Eficiencia η", f"{resultado['eta']*100:.2f} %")

    st.subheader("¿Qué pasa físicamente a cada voltaje?")
    st.caption("La corriente que sale de la celda es una carrera entre dos flujos que van en sentidos "
               "opuestos: la corriente fotogenerada (el campo de la juntura arrastra los pares hacia "
               "afuera) y la corriente de inyección directa del diodo (a mayor V, más portadores "
               "mayoritarios se inyectan de vuelta por difusión). En V=0 domina la primera; en V=Voc "
               "se cancelan exactamente.")

    V_max_exp = float(resultado["Voc_V"]) * 1.15
    V_op = st.slider("Voltaje de operación V [V]", 0.0, max(V_max_exp, 0.05), min(resultado["Voc_V"] * 0.6, V_max_exp), 0.005)

    Vt_local = c.K_B_EVK * T_K
    J_foto_mA = JL_con_sombra * 1e3
    J_osc_mA = J0_A_cm2 * (np.exp(V_op / (S["n_ideal"] * Vt_local)) - 1.0) * 1e3
    J_neto_mA = J_foto_mA - J_osc_mA

    n_flechas_foto = int(np.clip(round(np.sqrt(J_foto_mA) * 2.2), 1, 22))
    n_flechas_osc = int(np.clip(round(np.sqrt(max(J_osc_mA, 0)) * 2.2), 0, 22))

    def _flechas_svg(n, color, y0, dy, sentido):
        partes = []
        for i in range(n):
            x = 40 + (i % 11) * 34
            y = y0 + (i // 11) * dy
            if sentido > 0:
                partes.append(f'<path d="M{x},{y+10} L{x},{y} L{x-4},{y+4} M{x},{y} L{x+4},{y+4}" '
                               f'stroke="{color}" stroke-width="2.4" fill="none"/>')
            else:
                partes.append(f'<path d="M{x},{y} L{x},{y+10} L{x-4},{y+6} M{x},{y+10} L{x+4},{y+6}" '
                               f'stroke="{color}" stroke-width="2.4" fill="none"/>')
        return "".join(partes)

    svg_flujo = f"""
<div style="background:#0b0e14;border-radius:10px;padding:10px">
<svg viewBox="0 0 900 190" style="width:100%;display:block">
  <rect x="20" y="10" width="860" height="170" rx="8" fill="#161b22" stroke="#4a5568"/>
  <line x1="450" y1="10" x2="450" y2="180" stroke="#f6ad55" stroke-dasharray="6,4" stroke-width="2"/>
  <text x="30" y="28" fill="#a0aec0" font-size="13">base p / juntura</text>
  <text x="460" y="28" fill="#a0aec0" font-size="13">emisor n</text>
  <text x="30" y="180" fill="#68d391" font-size="12">↑ Corriente fotogenerada (arrastre por campo, J_foto={J_foto_mA:.2f} mA/cm²)</text>
  {_flechas_svg(n_flechas_foto, "#68d391", 130, 0, +1)}
  <text x="30" y="100" fill="#fc8181" font-size="12">↓ Inyección directa del diodo (difusión, J_osc={J_osc_mA:.4f} mA/cm²)</text>
  {_flechas_svg(n_flechas_osc, "#fc8181", 62, 0, -1)}
</svg>
</div>
"""
    st.components.v1.html(svg_flujo, height=210, scrolling=False)

    mv1, mv2, mv3 = st.columns(3)
    mv1.metric("J fotogenerada", f"{J_foto_mA:.3f} mA/cm²")
    mv2.metric("J inyección directa (diodo)", f"{J_osc_mA:.4f} mA/cm²")
    mv3.metric("J neta (la que sale de la celda)", f"{J_neto_mA:.3f} mA/cm²",
               "≈0 → estás en Voc" if abs(J_neto_mA) < 0.02 * J_foto_mA else None)
    st.caption("(Esta vista ignora la caída Rs·J dentro del exponente del diodo, solo para que las "
               "flechas sean legibles; la curva J-V de arriba sí la incluye completa.)")

    st.markdown("##### Malla frontal de dedos de plata: sombra vs resistencia serie")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Fracción de sombra fs", f"{malla['fraccion_sombra']*100:.2f} %")
        st.metric("Rs de la malla", f"{malla['Rs_malla_ohm_cm2']:.4f} Ω·cm²")
    with c2:
        Ns = np.linspace(5, 100, 40)
        fss = Ns * S["ancho_dedo_um"] * 1e-4 / c.ANCHO_CELDA_CM
        Rss = c.RS_REF_DEDOS_OHM_CM2 * c.NUMERO_DEDOS_REFERENCIA / Ns
        figN = go.Figure()
        figN.add_trace(go.Scatter(x=Ns, y=fss*100, name="Sombra [%]", line=dict(color="#f6ad55")))
        figN.add_trace(go.Scatter(x=Ns, y=Rss, name="Rs malla [Ω·cm²]", yaxis="y2", line=dict(color="#63b3ed")))
        figN.add_vline(x=S["num_dedos"], line_dash="dot", line_color="white")
        figN.update_layout(xaxis_title="N° de dedos", yaxis_title="Sombra [%]",
                           yaxis2=dict(title="Rs [Ω·cm²]", overlaying="y", side="right"),
                           height=320, template="plotly_dark")
        st.plotly_chart(figN, width="stretch")
    st.caption("Más dedos → menos resistencia serie pero más sombra: hay un compromiso óptimo.")

# ------------------------------------------------------------------
# TAB 4 — MAPA DE SECTORES Y DEFECTOS
# ------------------------------------------------------------------
with tab4:
    st.subheader("Introduce defectos localizados y observa su efecto global")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Contaminación metálica (región de bajo τₙ)**")
        S["defecto_activo"] = st.checkbox("Activar contaminación", S["defecto_activo"])
        r0, r1 = st.slider("Filas afectadas", 0, 8, S["defecto_filas"])
        c0, c1_ = st.slider("Columnas afectadas", 0, 8, S["defecto_cols"])
        S["defecto_filas"], S["defecto_cols"] = (r0, r1), (c0, c1_)
        S["defecto_tau_n_us"] = st.slider("τₙ en la zona contaminada [µs]", 0.1, 50.0, S["defecto_tau_n_us"])
    with c2:
        st.markdown("**Dedo de plata interrumpido**")
        activar_dedo = st.checkbox("Activar dedo roto", S["dedo_roto_col"] is not None)
        if activar_dedo:
            S["dedo_roto_col"] = st.slider("Columna del dedo roto", 0, 7, S["dedo_roto_col"] or 3)
        else:
            S["dedo_roto_col"] = None

    n_sec = 8
    tau_n_sano = np.full((n_sec, n_sec), S["tau_n_us"])
    tau_n_defecto = tau_n_sano.copy()
    r0, r1 = S["defecto_filas"]; c0, c1_ = S["defecto_cols"]
    if S["defecto_activo"]:
        tau_n_defecto[r0:r1, c0:c1_] = S["defecto_tau_n_us"]

    def mapa_iqe(tau_n_grid, wl_sel):
        i_w = int(np.argmin(np.abs(wl_grid - wl_sel)))
        out = np.zeros((n_sec, n_sec))
        for i in range(n_sec):
            for j in range(n_sec):
                Ln_ij = f.longitud_difusion(Dn, tau_n_grid[i, j]) * 1e4
                _e, _i = f.calcular_EQE_IQE_preciso(
                    np.array([wl_grid[i_w]]), np.array([alpha_grid[i_w]]), np.array([R_grid[i_w]]), np.array([1.0]),
                    xn_um, xp_um, W_total_um, Lp_um, Ln_ij, Dp, Dn, S["Sf"], S["Sr"])
                out[i, j] = _i[0]
        return out

    wl_defecto = st.slider("λ para visualizar el defecto [nm]", 300.0, 1200.0, 900.0, 10.0)
    mapa_sano = mapa_iqe(tau_n_sano, wl_defecto)
    mapa_con_defecto = mapa_iqe(tau_n_defecto, wl_defecto) if S["defecto_activo"] else mapa_sano.copy()

    c3, c4 = st.columns(2)
    with c3:
        figS = go.Figure(go.Heatmap(z=mapa_sano, colorscale="Viridis", zmin=0, zmax=1))
        figS.update_layout(title="IQE local — celda sana", height=360, template="plotly_dark")
        st.plotly_chart(figS, width="stretch")
    with c4:
        figD = go.Figure(go.Heatmap(z=mapa_con_defecto, colorscale="Viridis", zmin=0, zmax=1))
        figD.update_layout(title="IQE local — con defecto", height=360, template="plotly_dark")
        st.plotly_chart(figD, width="stretch")

    # Propagación a la curva I-V global
    def JL_global(tau_n_grid, Sf_extra_col=None):
        JL_sum = 0.0
        for i in range(n_sec):
            for j in range(n_sec):
                Ln_ij = f.longitud_difusion(Dn, tau_n_grid[i, j]) * 1e4
                Sf_ij = S["Sf"] if (Sf_extra_col is None or j != Sf_extra_col) else S["Sf"]
                _e, _i = f.calcular_EQE_IQE_preciso(wl_grid, alpha_grid, R_grid, phi0_grid,
                                                     xn_um, xp_um, W_total_um, Lp_um, Ln_ij, Dp, Dn, Sf_ij, S["Sr"])
                JL_sum += c.Q * np.trapezoid(phi0_grid * _e, wl_grid)
        return JL_sum / (n_sec * n_sec)

    JL_sano = JL_global(tau_n_sano)
    JL_defecto = JL_global(tau_n_defecto) if S["defecto_activo"] else JL_sano

    malla_sana = f.modelo_malla_frontal_plata(S["num_dedos"], S["ancho_dedo_um"])
    Rs_sano = c.RS_BASE_OHM_CM2 + malla_sana["Rs_malla_ohm_cm2"]
    Rs_con_dedo_roto = Rs_sano + (0.30 if S["dedo_roto_col"] is not None else 0.0)  # penalización proxy

    res_sano = f.simular_celda_JV(malla_sana["fraccion_iluminada"] * JL_sano, J0_A_cm2, T_K,
                                   S["irradiancia_soles"], S["n_ideal"], Rs_sano, S["Rp"], n_puntos=250)
    res_defecto = f.simular_celda_JV(malla_sana["fraccion_iluminada"] * JL_defecto, J0_A_cm2, T_K,
                                      S["irradiancia_soles"], S["n_ideal"], Rs_con_dedo_roto, S["Rp"], n_puntos=250)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=res_sano["V_array_V"], y=res_sano["J_array_A_cm2"]*1e3,
                              name="Celda sana", line=dict(color="#68d391", width=3)))
    fig.add_trace(go.Scatter(x=res_defecto["V_array_V"], y=res_defecto["J_array_A_cm2"]*1e3,
                              name="Con defecto(s)", line=dict(color="#fc8181", width=3, dash="dash")))
    fig.update_layout(xaxis_title="V [V]", yaxis_title="J [mA/cm²]", height=400, template="plotly_dark")
    st.plotly_chart(fig, width="stretch")

    m1, m2, m3 = st.columns(3)
    m1.metric("Jsc sana", f"{res_sano['Jsc_A_cm2']*1e3:.2f} mA/cm²")
    m2.metric("Jsc con defecto", f"{res_defecto['Jsc_A_cm2']*1e3:.2f} mA/cm²",
              f"{(res_defecto['Jsc_A_cm2']-res_sano['Jsc_A_cm2'])*1e3:+.2f} mA/cm²")
    m3.metric("Δ FF", f"{(res_defecto['FF']-res_sano['FF'])*100:+.2f} pp")
    st.caption("Explicación física: la **contaminación** (τₙ bajo) reduce la colección → cae Jsc de forma "
               "proporcional al área afectada. El **dedo roto** sube Rs → cae el FF y la Pmax, pero casi no "
               "cambia Jsc, porque en V≈0 la resistencia serie no limita la corriente de cortocircuito.")

# ------------------------------------------------------------------
# TAB 5 — VALIDACIÓN
# ------------------------------------------------------------------
with tab5:
    st.subheader("Verificaciones automáticas (con los parámetros de la semilla S=3 por defecto)")
    st.caption("Esta pestaña se ejecuta automáticamente. Compara cada resultado de la simulación con un "
               "valor de referencia y una tolerancia (Anexo B / criterios de aceptación del enunciado 2.2).")

    # Recalcular todo con valores por defecto de semilla, sin importar los sliders actuales.
    NA0, ND0 = c.NA_BASE_DEFAULT, c.ND_EMISOR_DEFAULT
    dn0, Wp0 = c.D_N_EMISOR_UM, c.W_P_BASE_UM_DEFAULT
    W0 = dn0 + Wp0
    T0_K = c.T_OPERACION_C_DEFAULT + 273.15
    Sf0, Sr0 = c.S_FRONTAL_CM_S_DEFAULT, 1.0e2
    tau_n0, tau_p0 = c.TAU_SRH_VOLUMEN_US_DEFAULT, c.TAU_P_EMISOR_US_DEFAULT

    Dp0 = f.coef_difusion(T0_K, c.MU_P_EMISOR_N_300K)
    Dn0 = f.coef_difusion(T0_K, c.MU_N_BASE_P_300K)
    Lp0_um = f.longitud_difusion(Dp0, tau_p0) * 1e4
    Ln0_um = f.longitud_difusion(Dn0, tau_n0) * 1e4
    Psi0_0 = f.potencial_juntura(NA0, ND0, c.NI_300K, T0_K)
    Wdep0_um = f.ancho_zona_deplecion(Psi0_0, NA0, ND0) * 1e4
    _xn0_lado, _xp0_lado = f.reparto_zona_deplecion(Wdep0_um, NA0, ND0)
    xn0_um = dn0 - _xn0_lado
    xp0_um = dn0 + _xp0_lado

    wl0 = np.linspace(300.0, 1200.0, 900)
    alpha0 = f.alpha_silicio(wl0)
    R0 = f.reflectancia_frontal(wl0, modo="fresnel")
    P0, phi00 = f.espectro_y_flujo_fotones(wl0)
    EQE0, IQE0 = f.calcular_EQE_IQE_preciso(wl0, alpha0, R0, phi00, xn0_um, xp0_um, W0,
                                             Lp0_um, Ln0_um, Dp0, Dn0, Sf0, Sr0)

    filas = []

    # V1: balance de fotones suma 1
    fr, fa, ft = f.balance_fotones(R0, alpha0, W0)
    suma = fr + fa + ft
    err_v1 = np.max(np.abs(suma - 1.0)) * 100
    filas.append(("V1", "Balance de fotones Beer-Lambert (suma=1 ∀λ)", f"{suma.min():.5f}–{suma.max():.5f}",
                  "1.00000", f"{err_v1:.4f}%", err_v1 < 1.0))

    # V2: profundidad de absorción a 450nm y 1000nm
    i450 = int(np.argmin(np.abs(wl0 - 450))); i1000 = int(np.argmin(np.abs(wl0 - 1000)))
    prof450 = 1.0 / alpha0[i450] * 1e4
    prof1000 = 1.0 / alpha0[i1000] * 1e4
    ok_v2 = (0.3 <= prof450 <= 3.0) and (prof1000 >= 70)
    filas.append(("V2", "Profundidad de absorción 1/α a 450 y 1000 nm",
                  f"{prof450:.2f} µm ; {prof1000:.1f} µm", "~1 µm ; >100 µm (±30%)",
                  "—", ok_v2))

    # V3: consistencia cruzada Jsc (EQE integrado) vs Jsc leída de curva J-V
    JL0 = c.Q * np.trapezoid(phi00 * EQE0, wl0)
    J00 = f.corriente_saturacion_J0(NA0, ND0, c.NI_300K, Dn0, Ln0_um * 1e-4, Dp0, Lp0_um * 1e-4)
    malla0 = f.modelo_malla_frontal_plata(c.NUMERO_DEDOS_BASE, c.ANCHO_DEDO_BASE_UM)
    res0 = f.simular_celda_JV(malla0["fraccion_iluminada"] * JL0, J00, T0_K, 1.0, 1.0,
                               c.RS_BASE_OHM_CM2 + malla0["Rs_malla_ohm_cm2"], c.RP_BASE_OHM_CM2, n_puntos=400)
    Jsc_EQE = JL0 * malla0["fraccion_iluminada"] * 1e3
    Jsc_JV = res0["Jsc_A_cm2"] * 1e3
    err_v3 = abs(Jsc_EQE - Jsc_JV) / Jsc_JV * 100 if Jsc_JV > 0 else np.nan
    filas.append(("V3", "Consistencia cruzada Jsc: ∫q·φ0·EQE dλ vs Jsc de curva J-V",
                  f"{Jsc_EQE:.3f} vs {Jsc_JV:.3f} mA/cm²", "coincidencia <5%", f"{err_v3:.3f}%", err_v3 < 5.0))

    # V4: FF0 con Rs->0, Rp->inf, n=1
    res_ideal = f.simular_celda_JV(malla0["fraccion_iluminada"] * JL0, J00, T0_K, 1.0, 1.0, 0.0, 1e12, n_puntos=400)
    FF0_calc = res_ideal["FF"]
    FF0_emp = f.FF0_empirico(res_ideal["Voc_V"], T0_K)
    err_v4 = abs(FF0_calc - FF0_emp) / FF0_emp * 100
    filas.append(("V4", "FF con Rs→0,Rp→∞,n=1 vs FF₀ empírico", f"{FF0_calc:.4f} vs {FF0_emp:.4f}",
                  "coincidencia <1%", f"{err_v4:.3f}%", err_v4 < 1.0))

    # V5: cota física EQE(λ) <= 1-R(λ)
    margen = (1 - R0) - EQE0
    ok_v5 = np.all(margen >= -1e-6)
    filas.append(("V5", "Cota física EQE(λ) ≤ 1−R(λ) para todo λ", f"mín margen={margen.min():.2e}",
                  "≥ 0 siempre", "—", ok_v5))

    # V6: dVoc/dT entre 15-75C
    temps_C = np.linspace(15, 75, 13)
    Vocs = []
    for TC in temps_C:
        TK = TC + 273.15
        p = f.J0_con_temperatura(TK, NA0, ND0, tau_n0, tau_p0)
        r = f.simular_celda_JV(malla0["fraccion_iluminada"] * JL0, p["J0_A_cm2"], TK, 1.0, 1.0,
                                0.0, 1e12, n_puntos=250)
        Vocs.append(r["Voc_V"])
    pendiente_mV_C = np.polyfit(temps_C, Vocs, 1)[0] * 1e3
    ok_v6 = -2.6 <= pendiente_mV_C <= -1.8
    filas.append(("V6", "Coeficiente dVoc/dT (barrido 15–75°C)", f"{pendiente_mV_C:.3f} mV/°C",
                  "entre −1.8 y −2.6 mV/°C", "—", ok_v6))

    # V7: efecto de la malla frontal — Jsc cae proporcional a fs añadida
    malla_x1 = f.modelo_malla_frontal_plata(c.NUMERO_DEDOS_BASE, c.ANCHO_DEDO_BASE_UM)
    malla_x2 = f.modelo_malla_frontal_plata(c.NUMERO_DEDOS_BASE, c.ANCHO_DEDO_BASE_UM * 2)
    res_x1 = f.simular_celda_JV(malla_x1["fraccion_iluminada"] * JL0, J00, T0_K, 1.0, 1.0,
                                 c.RS_BASE_OHM_CM2 + malla_x1["Rs_malla_ohm_cm2"], c.RP_BASE_OHM_CM2, n_puntos=250)
    res_x2 = f.simular_celda_JV(malla_x2["fraccion_iluminada"] * JL0, J00, T0_K, 1.0, 1.0,
                                 c.RS_BASE_OHM_CM2 + malla_x2["Rs_malla_ohm_cm2"], c.RP_BASE_OHM_CM2, n_puntos=250)
    caida_Jsc_pct = (1 - res_x2["Jsc_A_cm2"] / res_x1["Jsc_A_cm2"]) * 100
    caida_area_pct = (malla_x2["fraccion_sombra"] - malla_x1["fraccion_sombra"]) / (1 - malla_x1["fraccion_sombra"]) * 100
    err_v7 = abs(caida_Jsc_pct - caida_area_pct)
    filas.append(("V7", "Duplicar ancho de dedos: caída de Jsc vs área sombreada añadida",
                  f"{caida_Jsc_pct:.3f}% vs {caida_area_pct:.3f}%", "coincidencia <2 puntos", f"{err_v7:.3f} pp",
                  err_v7 < 2.0))

    import pandas as pd
    df = pd.DataFrame(filas, columns=["#", "Verificación", "Valor calculado", "Referencia/tolerancia",
                                       "Error", "Veredicto"])
    df["Veredicto"] = df["Veredicto"].map(lambda ok: "✅ APROBADO" if ok else "❌ REVISAR")
    st.dataframe(df, width="stretch", hide_index=True)

    n_ok = sum(1 for r in filas if r[-1])
    if n_ok == len(filas):
        st.success(f"Todas las verificaciones ({n_ok}/{len(filas)}) están dentro de tolerancia.")
    else:
        st.warning(f"{n_ok}/{len(filas)} verificaciones aprobadas. Revisa las marcadas ❌ — recuerda que el "
                   "enunciado acepta fallas siempre que se explique físicamente el supuesto que las causa "
                   "(p.ej. el modelo óptico de este simulador es una aproximación analítica, no datos "
                   "medidos de Green/Schinke, ver notas en fisica.py).")

    with st.expander("📎 Nota metodológica sobre aproximaciones (léela antes de presentar)"):
        st.markdown("""
- **α(λ) del silicio** y el **espectro AM1.5G** se generan aquí con modelos analíticos suaves
  (mismo estilo que `U2_Simulacion_optica.py` del curso), porque este entorno no tiene acceso a
  internet para descargar `astmg173.xls` ni las tablas medidas de Green (2008)/Schinke. La
  *forma* de las curvas (absorción fuerte en azul/UV, cola larga en rojo/IR; espectro tipo
  cuerpo negro solar con bandas de agua/O₂) es físicamente correcta y el espectro se normaliza
  a 1000 W/m² (300–2000 nm), pero los valores puntuales no son idénticos a los datos medidos.
  **Para la entrega real, reemplacen `_nk_silicio_aprox` y `_espectro_am15g_aprox` en
  `fisica.py` por `cargar_datos_nk_reales(...)` / `cargar_espectro_am15g_real("astmg173.xls")`**
  (ya están escritas y listas, solo falta el archivo de datos).
- El **EQE/IQE** se integra **analíticamente por tramos** (no con la regla del trapecio sobre
  una malla uniforme): para λ azul la longitud de absorción puede ser de pocos nanómetros, y una
  malla en x demasiado gruesa frente a eso sobreestima brutalmente la integral con trapecios
  (llegaba a dar EQE>1). La integral de α·e^(−αx) tiene primitiva cerrada en cada tramo
  (emisor/deplección/base), así que el resultado no depende de ninguna malla.
- `τₚ emisor` no viene dado por la semilla (la Tabla A.1 solo asigna `τ_SRH` de volumen);
  se declaró 1 µs como valor típico de un emisor n⁺ muy dopado — factor a discutir en la
  presentación si el grupo prefiere otro valor.
        """)

# ------------------------------------------------------------------
# TAB 6 — RESUMEN ANIMADO (secuencia completa, autoplay, sin controles)
# ------------------------------------------------------------------
with tab6:
    st.subheader("La celda p-n completa, de principio a fin — se reproduce sola")
    st.caption("Un ciclo de ~22 s que recorre las 4 etapas y luego se repite. Pensada para explicarse en "
               "vivo durante la presentación: no requiere que muevas nada.")

    V_arr_full = resultado["V_array_V"]
    J_arr_full = resultado["J_array_A_cm2"] * 1e3  # mA/cm², convención J<0 = generando
    # Truncar justo después de Voc: más allá el diodo entra en conducción directa
    # fuerte (J llega a decenas de mA/cm² positivos) y aplastaría la escala del
    # tramo fotovoltaico, que es el que importa mostrar aquí.
    i_voc = int(np.searchsorted(J_arr_full, 0.0)) if np.any(J_arr_full >= 0) else len(J_arr_full) - 1
    i_corte = min(i_voc + max(len(J_arr_full) // 40, 3), len(J_arr_full) - 1)
    V_arr6 = V_arr_full[:i_corte + 1].tolist()
    J_arr6 = (-J_arr_full[:i_corte + 1]).tolist()  # signo positivo = corriente generada
    Jsc6, Voc6, FF6, eta6, Pmax6 = (resultado["Jsc_A_cm2"] * 1e3, resultado["Voc_V"],
                                     resultado["FF"] * 100, resultado["eta"] * 100,
                                     resultado["Pmax_W_cm2"] * 1e3)

    html_resumen = f"""
<div style="background:#0b0e14;border-radius:10px;padding:10px">
<div id="fase-titulo" style="color:#f6ad55;font:bold 18px sans-serif;margin-bottom:2px">Cargando…</div>
<div id="fase-sub" style="color:#a0aec0;font:13px sans-serif;margin-bottom:8px;min-height:18px"></div>
<div style="background:#1a202c;border-radius:4px;height:6px;margin-bottom:8px;overflow:hidden">
  <div id="barra" style="background:#68d391;height:100%;width:0%"></div>
</div>
<canvas id="cv6" width="900" height="440" style="width:100%;display:block;border-radius:8px;"></canvas>
</div>
<script>
const wlLookup6 = {json.dumps(wl_lookup)};
const alphaLookup6 = {json.dumps(alpha_um_lookup)};
const xnUm6 = {xn_um}, xpUm6 = {xp_um}, Wum6 = {W_total_um}, dnUm6 = {S['dn_um']};
const NA6 = {S['NA']}, ND6 = {S['ND']}, Psi06 = {Psi0};
const nIonP6 = {n_ion_p}, nIonN6 = {n_ion_n}, fracXn6 = {frac_xn_visual};
const Varr6 = {json.dumps(V_arr6)};
const Jarr6 = {json.dumps(J_arr6)};
const Jsc6={Jsc6:.4f}, Voc6={Voc6:.5f}, FF6={FF6:.2f}, eta6={eta6:.3f}, Pmax6={Pmax6:.4f};

function interp6(x, xs, ys){{
  if(x<=xs[0]) return ys[0];
  if(x>=xs[xs.length-1]) return ys[ys.length-1];
  for(let i=0;i<xs.length-1;i++){{
    if(x>=xs[i] && x<=xs[i+1]){{
      const t=(x-xs[i])/(xs[i+1]-xs[i]);
      return ys[i]+t*(ys[i+1]-ys[i]);
    }}
  }}
  return ys[ys.length-1];
}}
function colorFromWl6(wl){{
  wl = Math.max(380, Math.min(750, wl));
  let R,G,B;
  if(wl<440){{R=-(wl-440)/(440-380);G=0;B=1;}}
  else if(wl<490){{R=0;G=(wl-440)/(490-440);B=1;}}
  else if(wl<510){{R=0;G=1;B=-(wl-510)/(510-490);}}
  else if(wl<580){{R=(wl-510)/(580-510);G=1;B=0;}}
  else if(wl<645){{R=1;G=-(wl-645)/(645-580);B=0;}}
  else {{R=1;G=0;B=0;}}
  return `rgb(${{Math.round(255*R)}},${{Math.round(255*G)}},${{Math.round(255*B)}})`;
}}

const cv6=document.getElementById('cv6'); const ctx6=cv6.getContext('2d');
const W6=cv6.width, H6=cv6.height;
const tituloEl=document.getElementById('fase-titulo'), subEl=document.getElementById('fase-sub'), barraEl=document.getElementById('barra');

// --- cross-section reutilizable (fases 1-3): escala comprimida por zona ---
const csTop=30, csBottom=H6-30, csLeft=40, csRight=W6-40, csH=csBottom-csTop;
const fracEmi6=0.24, fracDep6=0.10;
const depthBr6=[0,xnUm6,xpUm6,Wum6], fracBr6=[0,fracEmi6,fracEmi6+fracDep6,1.0];
function yOf6(x_um){{
  if(x_um<=depthBr6[0]) return csTop;
  if(x_um>=depthBr6[3]) return csTop+csH;
  for(let i=0;i<3;i++){{
    if(x_um>=depthBr6[i] && x_um<=depthBr6[i+1]){{
      const t=(x_um-depthBr6[i])/Math.max(depthBr6[i+1]-depthBr6[i],1e-9);
      return csTop+(fracBr6[i]+t*(fracBr6[i+1]-fracBr6[i]))*csH;
    }}
  }}
  return csTop+csH;
}}
function drawCrossSection(){{
  ctx6.fillStyle="#20242c"; ctx6.fillRect(csLeft,csTop,csRight-csLeft,csH);
  ctx6.fillStyle="rgba(99,179,237,0.14)"; ctx6.fillRect(csLeft+1, yOf6(0), csRight-csLeft-2, yOf6(xnUm6)-yOf6(0));
  ctx6.fillStyle="rgba(246,173,85,0.28)"; ctx6.fillRect(csLeft+1, yOf6(xnUm6), csRight-csLeft-2, yOf6(xpUm6)-yOf6(xnUm6));
  ctx6.fillStyle="rgba(104,211,145,0.12)"; ctx6.fillRect(csLeft+1, yOf6(xpUm6), csRight-csLeft-2, yOf6(Wum6)-yOf6(xpUm6));
  ctx6.strokeStyle="#4a5568"; ctx6.strokeRect(csLeft,csTop,csRight-csLeft,csH);
  ctx6.font="bold 12px sans-serif";
  ctx6.fillStyle="#90cdf4"; ctx6.fillText("EMISOR n", csLeft+8, (yOf6(0)+yOf6(xnUm6))/2+4);
  ctx6.fillStyle="#f6ad55"; ctx6.fillText("DEPLECCIÓN", csLeft+8, (yOf6(xnUm6)+yOf6(xpUm6))/2+4);
  ctx6.fillStyle="#9ae6b4"; ctx6.fillText("BASE p", csLeft+8, yOf6(xpUm6)+20);
}}

// --- estado de fases ---
const FASES = [
  {{ nombre:"1. Absorción y generación", sub:"Cada fotón se absorbe a una profundidad que depende de su color (Beer-Lambert).", dur:5000 }},
  {{ nombre:"2. Difusión: ¿colección o recombinación?", sub:"El portador minoritario difunde al azar; solo una fracción fc(x) llega a la juntura.", dur:5000 }},
  {{ nombre:"3. Así se formó la juntura p-n", sub:"Los portadores móviles se recombinan en el contacto, dejando expuestos los iones fijos.", dur:6000 }},
  {{ nombre:"4. Curva J-V bajo iluminación", sub:"Se barre el voltaje y se traza la curva; el punto naranja es el ensayo en curso.", dur:6000 }},
  {{ nombre:"Resumen", sub:"Parámetros de la celda con los parámetros actuales.", dur:3000 }},
];
const CICLO_TOTAL = FASES.reduce((a,f)=>a+f.dur,0);
const t0_6 = performance.now();

// fotones deterministicos para la fase 1 (reproducible en cada vuelta)
const fotonesDemo = [
  {{wl:420, t0:0.05}}, {{wl:480, t0:0.22}}, {{wl:560, t0:0.40}},
  {{wl:650, t0:0.58}}, {{wl:900, t0:0.74}}, {{wl:420, t0:0.90}}
];
function faseFotones(tf){{
  drawCrossSection();
  fotonesDemo.forEach(fd=>{{
    if(tf < fd.t0) return;
    const prog = Math.min((tf-fd.t0)/0.30, 1.0);
    const alpha_um = interp6(fd.wl, wlLookup6, alphaLookup6);
    const xAbs = Math.min(1.6/Math.max(alpha_um,1e-6), Wum6*1.05);
    const color = colorFromWl6(fd.wl);
    const x0 = 90 + (fd.wl % 300) * 2.3;
    if(prog < 1.0){{
      const yy = csTop + prog*(yOf6(Math.min(xAbs,Wum6))-csTop);
      ctx6.beginPath(); ctx6.arc(x0, yy, 4, 0, 7); ctx6.fillStyle=color; ctx6.fill();
    }} else {{
      const burst = Math.min((tf-fd.t0-0.30)/0.15, 1.0);
      if(burst<1.0){{
        const yy = yOf6(Math.min(xAbs,Wum6));
        ctx6.beginPath(); ctx6.arc(x0, yy, 3+burst*9, 0, 7);
        ctx6.strokeStyle=`rgba(255,255,180,${{1-burst}})`; ctx6.lineWidth=2; ctx6.stroke();
      }}
    }}
  }});
  ctx6.fillStyle="#e2e8f0"; ctx6.font="12px sans-serif";
  ctx6.fillText("azul/violeta → se frena en el emisor   |   rojo/IR → llega a la base o la atraviesa", csLeft, csBottom+22);
}}

const portadoresDemo = [
  {{x0:2.0, willCollect:true,  t0:0.05, x:260}},
  {{x0:80.0, willCollect:false, t0:0.15, x:520}},
  {{x0:3.5, willCollect:true,  t0:0.55, x:700}},
];
function faseVida(tf){{
  drawCrossSection();
  portadoresDemo.forEach(p=>{{
    if(tf<p.t0) return;
    const target = p.x0 < xnUm6 ? xnUm6 : xpUm6;
    const fracFinal = p.willCollect ? 1.0 : 0.5;
    const prog = Math.min((tf-p.t0)/0.35, 1.0);
    const fracNow = prog*fracFinal;
    const depthNow = p.x0 + (target-p.x0)*Math.min(fracNow/fracFinal,1);
    const yy = yOf6(depthNow);
    const wiggle = Math.sin(prog*30+p.x)*3;
    const color = p.x0 < xnUm6 ? "#63b3ed" : "#fc8181";
    if(prog<1.0){{
      ctx6.beginPath(); ctx6.arc(p.x+wiggle, yy, 4, 0, 7); ctx6.fillStyle=color; ctx6.fill();
    }} else {{
      const burst=Math.min((tf-p.t0-0.35)/0.20,1.0);
      const col = p.willCollect ? `rgba(246,224,94,${{1-burst}})` : `rgba(160,174,192,${{1-burst}})`;
      ctx6.beginPath(); ctx6.arc(p.x+wiggle, yy, 3+burst*11, 0, 7);
      ctx6.strokeStyle=col; ctx6.lineWidth=2.2; ctx6.stroke();
      if(burst>=1.0){{
        ctx6.fillStyle= p.willCollect ? "#f6e05e" : "#a0aec0"; ctx6.font="11px sans-serif";
        ctx6.fillText(p.willCollect?"colectado":"recombinado", p.x-20, yy-14);
      }}
    }}
  }});
}}

function faseJuntura(tf){{
  const left=csLeft, right=csRight, midX=(left+right)/2, midY=(csTop+csBottom)/2;
  let gap=0, depW=0, showField=false;
  if(tf<0.20){{ gap=40*(1-tf/0.20); }}
  else if(tf<0.55){{ gap=0; const tt=(tf-0.20)/0.35; depW=tt*(right-left)*0.30; }}
  else {{ depW=(right-left)*0.30; showField = tf<0.92; }}
  const shift=gap/2;
  ctx6.strokeStyle="#4a5568";
  ctx6.strokeRect(left-shift,csTop,midX-left-shift,csH);
  ctx6.strokeRect(midX+shift,csTop,right-midX-shift,csH);
  ctx6.fillStyle="#a0aec0"; ctx6.font="12px sans-serif";
  ctx6.fillText("base p (NA="+NA6.toExponential(0)+")", left, csTop-8);
  ctx6.fillText("emisor n (ND="+ND6.toExponential(0)+")", midX+shift+10, csTop-8);
  if(depW>0.5){{
    const wN=depW*fracXn6, wP=depW*(1-fracXn6);
    ctx6.fillStyle="rgba(246,173,85,0.28)"; ctx6.fillRect(midX-wP, csTop, wP+wN, csH);
    if(showField){{
      ctx6.strokeStyle="#f6ad55"; ctx6.lineWidth=2;
      ctx6.beginPath(); ctx6.moveTo(midX-wP+4,midY); ctx6.lineTo(midX+wN-4,midY);
      ctx6.lineTo(midX+wN-10,midY-5); ctx6.moveTo(midX+wN-4,midY); ctx6.lineTo(midX+wN-10,midY+5);
      ctx6.stroke();
      ctx6.fillStyle="#f6ad55"; ctx6.fillText("Campo E — Ψ₀≈"+Psi06.toFixed(3)+" V", midX-wP, csTop+16);
    }}
  }}
  // iones (posiciones fijas por indice, deterministicas)
  for(let i=0;i<nIonP6;i++){{
    const ix = left+10+((i*53)%Math.max(midX-left-24,1));
    const iy = csTop+20+((i*37)%Math.max(csH-40,1));
    const inDep = depW>0.5 && ix > midX-depW*(1-fracXn6);
    ctx6.beginPath(); ctx6.arc(ix-shift, iy, 4.5, 0, 7);
    ctx6.strokeStyle = inDep ? "#fc8181" : "#718096"; ctx6.stroke();
    if(tf<0.55){{ ctx6.beginPath(); ctx6.arc(ix-shift-(tf<0.20?shift:0), iy, 2.4, 0, 7); ctx6.fillStyle="#63b3ed"; ctx6.fill(); }}
  }}
  for(let i=0;i<nIonN6;i++){{
    const ix = midX+10+((i*47)%Math.max(right-midX-24,1));
    const iy = csTop+16+((i*41)%Math.max(csH-36,1));
    const inDep = depW>0.5 && ix < midX+depW*fracXn6;
    ctx6.beginPath(); ctx6.arc(ix+shift, iy, 4.5, 0, 7);
    ctx6.strokeStyle = inDep ? "#63b3ed" : "#718096"; ctx6.stroke();
    if(tf<0.55){{ ctx6.beginPath(); ctx6.arc(ix+shift+(tf<0.20?shift:0), iy, 2.4, 0, 7); ctx6.fillStyle="#fc8181"; ctx6.fill(); }}
  }}
}}

function faseIV(tf){{
  const left=70, right=W6-40, top=30, bottom=H6-60;
  ctx6.strokeStyle="#4a5568"; ctx6.beginPath();
  ctx6.moveTo(left,top); ctx6.lineTo(left,bottom); ctx6.lineTo(right,bottom); ctx6.stroke();
  ctx6.fillStyle="#a0aec0"; ctx6.font="12px sans-serif";
  ctx6.fillText("V [V]", right-30, bottom+18); ctx6.fillText("J [mA/cm²]", left-55, top+4);
  const Vmax=Varr6[Varr6.length-1], Jmax=Jsc6*1.08;
  const xOf=v=>left+(v/Vmax)*(right-left);
  const yOf7=j=>bottom-(j/Jmax)*(bottom-top-10);
  const nShow = Math.max(2, Math.floor(Math.min(tf/0.85,1.0)*Varr6.length));
  ctx6.strokeStyle="#68d391"; ctx6.lineWidth=2.5; ctx6.beginPath();
  for(let i=0;i<nShow;i++){{ const x=xOf(Varr6[i]), y=yOf7(Jarr6[i]); if(i===0) ctx6.moveTo(x,y); else ctx6.lineTo(x,y); }}
  ctx6.stroke();
  const iPunto = Math.min(nShow-1, Varr6.length-1);
  if(iPunto>=0){{
    ctx6.beginPath(); ctx6.arc(xOf(Varr6[iPunto]), yOf7(Jarr6[iPunto]), 6, 0, 7);
    ctx6.fillStyle="#f6ad55"; ctx6.fill();
    ctx6.font="12px sans-serif"; ctx6.fillStyle="#e2e8f0";
    ctx6.fillText(`V=${{Varr6[iPunto].toFixed(3)}} V   J=${{Jarr6[iPunto].toFixed(2)}} mA/cm²`, left+10, top+16);
  }}
  if(tf>0.90){{
    ctx6.fillStyle="#f6ad55"; ctx6.font="bold 13px sans-serif";
    ctx6.fillText(`Jsc=${{Jsc6.toFixed(2)}}  Voc=${{(Voc6*1000).toFixed(0)}}mV  FF=${{FF6.toFixed(1)}}%  η=${{eta6.toFixed(2)}}%`, left+10, bottom-10);
  }}
}}

function faseResumen(tf){{
  ctx6.fillStyle="#e2e8f0"; ctx6.textAlign="center";
  ctx6.font="bold 22px sans-serif";
  ctx6.fillText("Resumen de la celda simulada", W6/2, H6/2-90);
  const items = [
    [`Jsc = ${{Jsc6.toFixed(2)}} mA/cm²`, "#68d391"],
    [`Voc = ${{(Voc6*1000).toFixed(0)}} mV`, "#63b3ed"],
    [`FF = ${{FF6.toFixed(1)}} %`, "#f6ad55"],
    [`η = ${{eta6.toFixed(2)}} %`, "#f687b3"],
  ];
  ctx6.font="bold 30px sans-serif";
  items.forEach((it,i)=>{{
    ctx6.fillStyle=it[1];
    ctx6.fillText(it[0], W6/2, H6/2-20+i*46);
  }});
  ctx6.textAlign="left";
}}

function draw6(){{
  const tGlobal = ((performance.now()-t0_6) % CICLO_TOTAL);
  let acc=0, faseIdx=0, tf=0;
  for(let i=0;i<FASES.length;i++){{
    if(tGlobal < acc+FASES[i].dur){{ faseIdx=i; tf=(tGlobal-acc)/FASES[i].dur; break; }}
    acc += FASES[i].dur;
  }}
  ctx6.clearRect(0,0,W6,H6);
  tituloEl.textContent = FASES[faseIdx].nombre;
  subEl.textContent = FASES[faseIdx].sub;
  barraEl.style.width = (100*(tGlobal/CICLO_TOTAL)).toFixed(1)+"%";

  if(faseIdx===0) faseFotones(tf);
  else if(faseIdx===1) faseVida(tf);
  else if(faseIdx===2) faseJuntura(tf);
  else if(faseIdx===3) faseIV(tf);
  else faseResumen(tf);

  requestAnimationFrame(draw6);
}}
draw6();
</script>
"""
    components.html(html_resumen, height=560, scrolling=False)
    st.caption("Los números que ves al final corresponden a los parámetros actuales de la barra lateral "
               "(no a la semilla fija) — si cambias algo ahí, esta pestaña se regenera con los nuevos valores.")
