import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic as haversine
import googlemaps
from datetime import datetime, timedelta
from fpdf import FPDF
import base64
import os
from dotenv import load_dotenv

# API anahtarını yükle
load_dotenv()
GOOGLE_API_KEY = os.getenv("AIzaSyDwQVuPcON3rGSibcBrwhxQvz4HLTpF9Ws")
gmaps = googlemaps.Client(key=GOOGLE_API_KEY)

st.set_page_config(layout="wide")
SAATLIK_ISCILIK = 500
km_basi_tuketim = 0.07
benzin_fiyati = 43

st.title("🛠️ Montaj Ekip Rota ve Maliyet Planlama")

# Session state ilk yükleme
if "ekipler" not in st.session_state:
    st.session_state.ekipler = {}

# Ekip Yönetimi
st.sidebar.subheader("👷 Ekip Yönetimi")
ekip_adi = st.sidebar.text_input("Yeni Ekip Adı Girin")
if st.sidebar.button("➕ Ekip Oluştur") and ekip_adi:
    if ekip_adi not in st.session_state.ekipler:
        st.session_state.ekipler[ekip_adi] = {"members": [], "sehirler": []}
    else:
        st.warning("⚠️ Bu ekip zaten mevcut.")

if st.session_state.ekipler:
    aktif_ekip = st.sidebar.selectbox("📌 Aktif Ekip Seç", list(st.session_state.ekipler.keys()))
    st.session_state.aktif_ekip = aktif_ekip

    yeni_uye = st.sidebar.text_input("Yeni Üye Ekle", key="yeni_uye")
    if st.sidebar.button("➕ Üye Ekle") and yeni_uye:
        if yeni_uye not in st.session_state.ekipler[aktif_ekip]["members"]:
            st.session_state.ekipler[aktif_ekip]["members"].append(yeni_uye)
        else:
            st.warning("⚠️ Bu üye zaten var.")

# Başlangıç Konumu
st.sidebar.markdown("---")
st.sidebar.subheader("📍 Başlangıç Konumu")

if "baslangic_konum" not in st.session_state:
    st.session_state.baslangic_konum = None

baslangic_input = st.sidebar.text_input("Başlangıç Şehri", key="baslangic_input")
if st.sidebar.button("🌍 Konumu Belirle") and baslangic_input:
    sonuc = gmaps.geocode(baslangic_input)
    if sonuc:
        st.session_state.baslangic_konum = sonuc[0]["geometry"]["location"]
        st.success("✅ Başlangıç konumu belirlendi.")
    else:
        st.error("❌ Konum bulunamadı.")

# Sıralama tipi
st.sidebar.markdown("---")
siralama_tipi = st.sidebar.radio("🔀 Sıralama Tipi", ["Önem Derecesi", "En Kısa Mesafe"])

# Şehir Ekleme
st.subheader("📌 Şehir Ekle (Aktif Ekibe)")
if "aktif_ekip" in st.session_state and st.session_state.aktif_ekip:
    with st.form("sehir_form"):
        sehir_adi = st.text_input("Şehir / Bayi Adı")
        onem = st.slider("Önem Derecesi", 1, 5, 3)
        is_suresi = st.number_input("Montaj Süresi (saat)", 1, 24, 2)
        ekle_btn = st.form_submit_button("➕ Şehir Ekle")

        if ekle_btn:
            sonuc = gmaps.geocode(sehir_adi)
            if sonuc:
                konum = sonuc[0]["geometry"]["location"]
                st.session_state.ekipler[st.session_state.aktif_ekip]["sehirler"].append({
                    "sehir": sehir_adi,
                    "konum": konum,
                    "onem": onem,
                    "is_suresi": is_suresi
                })
                st.success(f"{sehir_adi} aktif ekibe eklendi.")
            else:
                st.error("Konum bulunamadı.")
else:
    st.warning("Lütfen önce bir ekip oluşturup seçin.")

# PDF çıktısı oluşturma
def create_pdf(km, sure, yakit, iscilik, toplam):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Montaj Rota ve Maliyet Özeti", ln=True, align="C")
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(200, 10, f"Toplam Mesafe: {km:.2f} km", ln=True)
    pdf.cell(200, 10, f"Toplam Süre: {sure}", ln=True)
    pdf.cell(200, 10, f"Toplam Yakıt Maliyeti: {yakit:.2f} TL", ln=True)
    pdf.cell(200, 10, f"Toplam İşçilik Maliyeti: {iscilik:.2f} TL", ln=True)
    pdf.cell(200, 10, f"Toplam Maliyet: {toplam:.2f} TL", ln=True)

    filename = "rota_ozeti.pdf"
    pdf.output(filename)
    with open(filename, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode("utf-8")
        href = f'<a href="data:application/pdf;base64,{base64_pdf}" download="{filename}">📄 PDF çıktısını indir</a>'
    return href

# Rota ve Harita
st.subheader("🗺️ Rota ve Harita")

if st.session_state.baslangic_konum and st.session_state.aktif_ekip:
    sehirler = st.session_state.ekipler[st.session_state.aktif_ekip]["sehirler"]
    if sehirler:
        baslangic = st.session_state.baslangic_konum
        sehirler = sehirler.copy()

        if siralama_tipi == "Önem Derecesi":
            sehirler.sort(key=lambda x: x["onem"], reverse=True)
        else:
            rota = []
            current = baslangic
            while sehirler:
                en_yakin = min(sehirler, key=lambda x: haversine(
                    (current["lat"], current["lng"]),
                    (x["konum"]["lat"], x["konum"]["lng"])
                ))
                rota.append(en_yakin)
                current = en_yakin["konum"]
                sehirler.remove(en_yakin)
            sehirler = rota

        harita = folium.Map(location=[baslangic["lat"], baslangic["lng"]], zoom_start=6)
        toplam_km = toplam_sure = toplam_iscilik = toplam_yakit = toplam_maliyet = 0
        konumlar = [baslangic] + [s["konum"] for s in sehirler]

        for i in range(len(konumlar) - 1):
            yol = gmaps.directions(
                (konumlar[i]["lat"], konumlar[i]["lng"]),
                (konumlar[i + 1]["lat"], konumlar[i + 1]["lng"]),
                mode="driving"
            )
            if yol:
                km = yol[0]["legs"][0]["distance"]["value"] / 1000
                sure_dk = yol[0]["legs"][0]["duration"]["value"] / 60
                toplam_km += km
                toplam_sure += sure_dk / 60
                yakit_maliyeti = km * km_basi_tuketim * benzin_fiyati
                iscilik_maliyeti = sure_dk * SAATLIK_ISCILIK
                toplam_yakit += yakit_maliyeti
                toplam_iscilik += iscilik_maliyeti
                toplam_maliyet += yakit_maliyeti + iscilik_maliyeti

                folium.Marker(
                    [konumlar[i]["lat"], konumlar[i]["lng"]],
                    tooltip=f"{i}. Nokta"
                ).add_to(harita)
                folium.Marker(
                    [konumlar[i + 1]["lat"], konumlar[i + 1]["lng"]],
                    tooltip=f"{i+1}. Nokta"
                ).add_to(harita)
                folium.PolyLine([
                    (konumlar[i]["lat"], konumlar[i]["lng"]),
                    (konumlar[i + 1]["lat"], konumlar[i + 1]["lng"])
                ], color="blue").add_to(harita)

        toplam_sure_td = str(timedelta(hours=toplam_sure))
        pdf_link = create_pdf(toplam_km, toplam_sure_td, toplam_yakit, toplam_iscilik, toplam_maliyet)
        st.markdown(pdf_link, unsafe_allow_html=True)
        st_folium(harita, width=700)
    else:
        st.info("📍 Rota için şehir ekleyin.")
else:
    st.warning("❗ Başlangıç konumunu ve şehirleri belirlemelisiniz.")
