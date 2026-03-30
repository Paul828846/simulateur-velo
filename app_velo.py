import streamlit as st
import gpxpy
import pandas as pd
import math
import plotly.graph_objects as go
import plotly.express as px

# --- CSS PERSONNALISÉ POUR SMARTPHONE ---
st.markdown("""
    <style>
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
    }
    </style>
    """, unsafe_content_code=True)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

def analyze_gpx(file, vf_k, vc_k, vd_k, wr, wb, v_wind_k):
    g = gpxpy.parse(file)
    crr, rho, cda, grav, eta = 0.004, 1.225, 0.35, 9.81, 0.97
    m = wr + wb
    vf, vc, vd = vf_k/3.6, vc_k/3.6, vd_k/3.6
    v_wind = v_wind_k / 3.6
    
    pts_plot, dist_t, dp, dm, a_max = [], 0, 0, 0, -999
    st_t = {"Plat":{"t":0,"d":0,"w":0}, "Montée":{"t":0,"d":0,"w":0}, "Descente":{"t":0,"d":0,"w":0}}
    res = {"Aéro":0, "Gravité":0, "Roulement":0}
    all_p = []
    for tr in g.tracks:
        for sg in tr.segments:
            for p in sg.points: all_p.append((p.latitude, p.longitude, p.elevation))
    if not all_p: return None

    for i in range(1, len(all_p)):
        p1, p2 = all_p[i-1], all_p[i]
        e1, e2 = p1[2] or 0, p2[2] or 0
        d = haversine(p1[0], p1[1], p2[0], p2[1])
        if d < 1: continue
        dist_t += d
        diff = e2 - e1
        if diff > 0: dp += diff
        else: dm += abs(diff)
        if e2 > a_max: a_max = e2
        slope = (diff / d) * 100
        v = vc if slope > 2 else (vd if slope < -2 else vf)
        dt = d / v
        v_air = v + v_wind 
        pr = crr * m * grav * v
        pa = 0.5 * rho * cda * (v_air**2) * v
        pg = m * grav * (slope / 100) * v
        pt = max(0, (pr + pa + pg) / eta)
        k = "Montée" if slope > 2 else ("Descente" if slope < -2 else "Plat")
        st_t[k]["t"] += dt
        st_t[k]["d"] += d
        st_t[k]["w"] += pt * dt
        res["Roulement"] += pr * dt
        res["Aéro"] += max(0, pa * dt)
        res["Gravité"] += max(0, pg * dt)
        pts_plot.append({"D": dist_t/1000, "A": e2})
    return pts_plot, st_t, res, dist_t, dp, dm, a_max

# --- INTERFACE ---
st.set_page_config(page_title="Vélo Analyse Expert", layout="wide")
st.title("🚴‍♂️ Analyse de Performance Cycliste")

# TEXTE D'EXPLICATION
with st.expander("📖 Guide d'utilisation et aide"):
    st.info("**📱 Note aux utilisateurs mobile :** Cliquez sur la petite flèche en haut à gauche (onglet latéral) pour modifier vos paramètres de poids, vent et vitesse.")
    st.write("""
    Cette application simule l'effort physique nécessaire pour réaliser un parcours GPX selon vos paramètres :
    * **Poids :** Influence principalement l'effort en montée (gravité).
    * **Vent :** Un vent positif (+) simule un vent de face, un vent négatif (-) un vent de dos.
    * **Vitesses cibles :** Définissez votre allure habituelle sur chaque terrain pour estimer votre puissance et votre temps.
    * **Résistances :** Le graphique final montre si votre énergie a été consommée par l'air (Aéro), la pente (Gravité) ou les pneus (Roulement).
    """)

st.sidebar.header("Paramètres Physiques")
wr = st.sidebar.number_input("Poids Cycliste (kg)", 40, 150, 75)
wb = st.sidebar.number_input("Poids Vélo (kg)", 5, 30, 9)
v_wind_k = st.sidebar.slider("Vent (km/h) : [+] Face / [-] Dos", -50, 50, 0)
st.sidebar.header("Vitesses cibles")
vf = st.sidebar.slider("Vitesse Plat (km/h)", 10, 50, 28)
vc = st.sidebar.slider("Vitesse Montée (km/h)", 5, 30, 12)
vd = st.sidebar.slider("Vitesse Descente (km/h)", 15, 80, 40)

f = st.file_uploader("Importer votre fichier .GPX", type="gpx")

if f:
    r = analyze_gpx(f, vf, vc, vd, wr, wb, v_wind_k)
    if r:
        pts, st_t, res, d_t, d_p, d_m, a_m = r
        tw = sum(v["w"] for v in st_t.values())
        tt = sum(v["t"] for v in st_t.values())
        h, m = int(tt // 3600), int((tt % 3600) // 60)

        st.header("🏁 Indicateurs")
        c1, c2, c3 = st.columns(3)
        c1.metric("Temps Total", f"{h}h {m}min")
        c2.metric("P. Moy. Totale", f"{tw/tt:.0f} W")
        c3.metric("Distance", f"{d_t/1000:.1f} km")
        c1.metric("P. Moy. Montée", f"{st_t['Montée']['w']/st_t['Montée']['t']:.0f} W" if st_t['Montée']['t']>0 else "0 W")
        c2.metric("P. Moy. Plat", f"{st_t['Plat']['w']/st_t['Plat']['t']:.0f} W" if st_t['Plat']['t']>0 else "0 W")
        c3.metric("Dénivelé D+", f"{d_p:.0f} m")
        c1.metric("Dénivelé D-", f"{d_m:.0f} m")
        c2.metric("Énergie (kJ)", f"{tw/1000:.0f} kJ")
        c3.metric("Alt. Max", f"{a_m:.0f} m")
        
        st.divider()
        st.subheader("⛰️ Profil Altimétrique")
        fig_p = go.Figure(go.Scatter(x=[p['D'] for p in pts], y=[p['A'] for p in pts], fill='tozeroy', line=dict(color='grey')))
        fig_p.update_layout(xaxis_title="Distance (km)", yaxis_title="Altitude (m)", height=300, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_p, use_container_width=True)

        ca, cb = st.columns(2)
        with ca:
            st.subheader("📊 Terrain")
            df_t = pd.DataFrame([{"Type":k, "Km":v["d"]/1000, "%":(v["t"]/tt)*100 if tt>0 else 0} for k,v in st_t.items()])
            st.table(df_t.style.format({"Km":"{:.1f}", "%":"{:.1f}%"}))
            st.plotly_chart(px.pie(df_t, names="Type", values="Km", hole=0.4, height=300), use_container_width=True)
        with cb:
            st.subheader("🌬️ Résistances")
            tr_v = sum(res.values())
            df_r = pd.DataFrame([{"Source":k, "kJ":v/1000, "%":(v/tr_v)*100 if tr_v>0 else 0} for k,v in res.items()])
            st.table(df_r.style.format({"kJ":"{:.0f}", "%":"{:.1f}%"}))
            st.plotly_chart(px.pie(df_r, names="Source", values="kJ", hole=0.4, height=300), use_container_width=True)