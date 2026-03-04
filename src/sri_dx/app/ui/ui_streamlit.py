import streamlit as st

def main():
    st.set_page_config(page_title="SRI-DX: Diagnosis Retrieval System", layout="wide")
    
    st.title("🩺 SRI-DX")
    st.subheader("Sistema de Recuperación de Información para Diagnóstico Médico")

    # Sidebar
    st.sidebar.header("Configuración")
    mode = st.sidebar.selectbox("Modo de búsqueda", ["Híbrido (ANN + BM25)", "Sólo Vectorial", "Búsqueda Web Fallback"])
    
    # Main search
    query = st.text_input("Ingrese síntomas o descripción del caso:", placeholder="Ej: Dolor abdominal agudo, fiebre y náuseas...")

    if st.button("Buscar"):
        if query:
            with st.spinner("Buscando en el corpus clínico y generando evidencia..."):
                # TODO: Implement search flow call
                st.info(f"Resultados para: {query}")
                st.warning("Nota: Este sistema es una herramienta de apoyo y no sustituye el criterio médico.")
        else:
            st.error("Por favor, ingrese una consulta.")

if __name__ == "__main__":
    main()
