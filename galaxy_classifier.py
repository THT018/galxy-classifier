"""
Clasificador de Galaxias - Herramienta de votación morfológica
Uso: streamlit run galaxy_classifier.py

Requiere: pip install streamlit pandas requests pillow
"""

import streamlit as st
import pandas as pd
import requests
from PIL import Image
from io import BytesIO
from datetime import datetime
import os

# ─── CONFIGURACIÓN ──────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Clasificador de Galaxias",
    page_icon="🌌",
    layout="wide",
)

st.markdown("""
<style>
    .main { background-color: #0a0a1a; color: #e0e0ff; }
    .stApp { background-color: #0a0a1a; }
    h1, h2, h3 { color: #a0c4ff; font-family: 'Courier New', monospace; }
    .galaxy-info { background: #12122a; border: 1px solid #2a2a5a;
                   border-radius: 8px; padding: 12px; margin-bottom: 10px; }
    .stButton>button { background-color: #1e3a5f; color: #a0c4ff;
                        border: 1px solid #2a5a8f; border-radius: 6px; }
    .stButton>button:hover { background-color: #2a5a8f; }
</style>
""", unsafe_allow_html=True)

# ─── FUNCIONES ───────────────────────────────────────────────────────────────

def get_sdss_image(ra: float, dec: float, scale: float = 0.2, size: int = 512) -> Image.Image | None:
    """Obtiene imagen de galaxia desde SDSS usando RA y DEC."""
    url = (
        f"https://skyserver.sdss.org/dr18/SkyServerWS/ImgCutout/getjpeg"
        f"?ra={ra}&dec={dec}&scale={scale}&width={size}&height={size}"
    )
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200 and "image" in resp.headers.get("Content-Type", ""):
            return Image.open(BytesIO(resp.content))
    except Exception as e:
        st.warning(f"No se pudo cargar imagen SDSS: {e}")
    return None


def save_vote(row_data: dict, votes: dict, voter_name: str, output_dir: str = ".") -> str:
    """Guarda el voto en un CSV con el nombre del votante."""
    filename = os.path.join(output_dir, f"votos_{voter_name}.csv")
    record = {
        "dr7objid":     row_data.get("dr7objid", ""),
        "PGC_name":     row_data.get("PGC_name", ""),
        "ra":           row_data.get("ra", ""),
        "dec":          row_data.get("dec", ""),
        "ObjID":        row_data.get("ObjID", ""),
        "votante":      voter_name,
        "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **votes,
    }
    df_new = pd.DataFrame([record])
    if os.path.exists(filename):
        df_existing = pd.read_csv(filename)
        df_out = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_out = df_new
    df_out.to_csv(filename, index=False)
    return filename


# ─── SIDEBAR ─────────────────────────────────────────────────────────────────

st.sidebar.title("🌌 Clasificador de Galaxias")
st.sidebar.markdown("---")

voter_name = st.sidebar.text_input("👤 Nombre del votante", placeholder="Escribe tu nombre...")

uploaded_file = st.sidebar.file_uploader("📂 Cargar CSV de galaxias", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.sidebar.success(f"✅ {len(df)} galaxias cargadas")
else:
    st.sidebar.info("Carga un CSV para comenzar")
    df = None

# ─── PROGRESO ────────────────────────────────────────────────────────────────

if df is not None:
    if "galaxy_index" not in st.session_state:
        st.session_state.galaxy_index = 0
    if "votes_count" not in st.session_state:
        st.session_state.votes_count = 0

    total = len(df)
    idx   = st.session_state.galaxy_index

    st.sidebar.markdown("---")
    st.sidebar.metric("Progreso", f"{idx}/{total}")
    st.sidebar.progress(idx / total if total > 0 else 0)
    st.sidebar.metric("Votos guardados", st.session_state.votes_count)

    if idx >= total:
        st.balloons()
        st.success("🎉 ¡Has clasificado todas las galaxias!")
        st.stop()

    # ─── GALAXIA ACTUAL ──────────────────────────────────────────────────────

    galaxy = df.iloc[idx]

    st.title(f"🔭 Galaxia {idx + 1} de {total}")

    col_img, col_form = st.columns([1, 1], gap="large")

    # Columna izquierda: imagen + info
    with col_img:
        st.markdown(f"""
        <div class="galaxy-info">
            <b>PGC:</b> {galaxy.get('PGC_name', 'N/A')}<br>
            <b>RA:</b>  {galaxy.get('ra', 'N/A'):.6f} °<br>
            <b>DEC:</b> {galaxy.get('dec', 'N/A'):.6f} °<br>
            <b>ObjID:</b> {galaxy.get('ObjID', 'N/A')}<br>
            <b>dr7objid:</b> {galaxy.get('dr7objid', 'N/A')}
        </div>
        """, unsafe_allow_html=True)

        with st.spinner("Cargando imagen desde SDSS..."):
            img = get_sdss_image(galaxy["ra"], galaxy["dec"])

        if img:
            st.image(img, caption=f"SDSS — RA={galaxy['ra']:.4f}, DEC={galaxy['dec']:.4f}",
                     use_container_width=True)
        else:
            st.error("No se pudo cargar la imagen de SDSS")

        # Enlace al NS Atlas si existe
        if pd.notna(galaxy.get("nsatlas_link")):
            st.markdown(f"[🔗 Ver en NS Atlas]({galaxy['nsatlas_link']})", unsafe_allow_html=False)

        # Notas del CSV original
        if pd.notna(galaxy.get("Notas")):
            st.info(f"📝 Nota original: {galaxy['Notas']}")

    # Columna derecha: formulario de votación
    with col_form:
        st.subheader("📋 Clasificación morfológica")

        # Evitar re-submit al recargar
        vote_key = f"voted_{idx}"

        with st.form(key=f"vote_form_{idx}"):

            gtype = st.selectbox(
                "Tipo morfológico (Type)",
                options=["", "E", "S0", "SB0", "Sa", "SBa", "Sb", "SBb",
                         "Sc", "SBc", "Sd", "SBd", "Irr", "Merger"],
                index=0,
                help="Clasificación de Hubble de la galaxia"
            )

            bar = st.radio(
                "¿Tiene barra? (Bar)",
                options=[0.0, 1.0],
                format_func=lambda x: "No" if x == 0.0 else "Sí",
                horizontal=True
            )

            st.markdown("#### Anillos")
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                o_ring = st.number_input("O_ring (externo)",
                    min_value=0.0, max_value=1.0, value=0.0, step=1.0)
            with col_r2:
                i_ring = st.number_input("I_ring (interno)",
                    min_value=0.0, max_value=1.0, value=0.0, step=1.0)
            with col_r3:
                n_ring = st.number_input("N_ring (nuclear)",
                    min_value=0.0, max_value=1.0, value=0.0, step=1.0)

            type_ring = st.selectbox(
                "Tipo de anillo (Type_ring)",
                options=["", "r", "R", "rR", "rs", "s"],
                index=0,
                help="r=inner ring, R=outer ring"
            )

            st.markdown("#### Ansae")
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                ansae_round = st.number_input("Ansae_round",
                    min_value=0.0, max_value=1.0, value=0.0, step=1.0)
            with col_a2:
                ansae_arc = st.number_input("Ansae_arc",
                    min_value=0.0, max_value=1.0, value=0.0, step=1.0)

            notas_voto = st.text_area("📝 Notas del votante", placeholder="Observaciones opcionales...")

            # Botones
            col_b1, col_b2 = st.columns(2)
            submitted   = col_b1.form_submit_button("✅ Guardar y siguiente", use_container_width=True)
            skip_button = col_b2.form_submit_button("⏭️ Omitir galaxia",      use_container_width=True)

        if submitted:
            if not voter_name:
                st.error("⚠️ Escribe tu nombre en la barra lateral antes de votar.")
            elif not gtype:
                st.error("⚠️ Selecciona un tipo morfológico antes de continuar.")
            else:
                votes = {
                    "Type":        gtype,
                    "Bar":         bar,
                    "Type_ring":   type_ring if type_ring else None,
                    "O_ring":      o_ring,
                    "I_ring":      i_ring,
                    "N_ring":      n_ring,
                    "Ansae_round": ansae_round,
                    "Ansae_arc":   ansae_arc,
                    "Notas_voto":  notas_voto,
                }
                outfile = save_vote(galaxy.to_dict(), votes, voter_name)
                st.success(f"✅ Guardado en `{outfile}`")
                st.session_state.votes_count += 1
                st.session_state.galaxy_index += 1
                st.rerun()

        if skip_button:
            st.session_state.galaxy_index += 1
            st.rerun()

else:
    # Pantalla de bienvenida
    st.title("🌌 Clasificador de Galaxias")
    st.markdown("""
    ### Bienvenido

    Esta herramienta permite clasificar galaxias morfológicamente usando imágenes del **SDSS (Sloan Digital Sky Survey)**.

    #### Pasos:
    1. **Escribe tu nombre** en la barra lateral (izquierda)
    2. **Carga tu CSV** con las galaxias a clasificar
    3. **Clasifica** cada galaxia usando el formulario
    4. Los resultados se guardan en un **CSV con tu nombre**

    #### Columnas necesarias en el CSV:
    | Columna | Descripción |
    |---------|-------------|
    | `ra`    | Ascensión recta (grados) |
    | `dec`   | Declinación (grados) |
    | `ObjID` | Identificador del objeto |
    | `PGC_name` | Nombre PGC (opcional) |
    | `dr7objid` | ID DR7 (opcional) |
    | `nsatlas_link` | Link NS Atlas (opcional) |
    """)
