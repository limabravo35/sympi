import streamlit as st
import pandas as pd
import datetime
import altair as alt
import os
import seaborn as sns
import matplotlib.pyplot as plt

st.set_page_config(page_title="Tägliche Bewertung", layout="centered")

st.title("📊 Tägliche Bewertung (1–10)")
st.write("Trage deine Daten ein und analysiere deinen Verlauf.")

DATEI_PFAD = "daten.csv"

# --- CSV laden oder leeren DataFrame erstellen ---
def lade_daten():
    if os.path.exists(DATEI_PFAD):
        df = pd.read_csv(DATEI_PFAD, parse_dates=["Datum"])
        df["Datum"] = pd.to_datetime(df["Datum"])
        return df.sort_values("Datum")
    else:
        return pd.DataFrame(columns=["Datum", "Stimmung", "Schlaf", "Stress"])

# --- Daten synchronisieren ---
st.session_state["daten"] = lade_daten()

# --- 1. Dateneingabe ---
with st.expander("📝 Neue tägliche Bewertung"):
    with st.form("eingabe_formular"):
        datum = st.date_input("Datum", value=datetime.date.today())
        stimmung = st.slider("Stimmung / Energie", 1, 10, 5)
        schlaf = st.slider("Schlafqualität", 1, 10, 5)
        stress = st.slider("Stresslevel", 1, 10, 5)
        submit = st.form_submit_button("Eintrag speichern")

    if submit:
        neue_zeile = {
            "Datum": pd.to_datetime(datum),
            "Stimmung": stimmung,
            "Schlaf": schlaf,
            "Stress": stress
        }

        df_neu = pd.DataFrame([neue_zeile])
        df_aktuell = st.session_state["daten"]

        df_kombiniert = pd.concat([df_aktuell, df_neu])
        df_kombiniert = df_kombiniert.drop_duplicates(subset="Datum", keep="last").sort_values("Datum")

        df_kombiniert.to_csv(DATEI_PFAD, index=False)
        st.session_state["daten"] = df_kombiniert
        st.success("Eintrag gespeichert!")

# --- Tabs für verschiedene Funktionen ---
if not st.session_state["daten"].empty:
    tab1, tab2, tab3 = st.tabs(["📈 Verlauf", "📊 Analysen", "📋 Tabelle & Export"])

    with tab1:
        st.header("📈 Verlauf deiner Bewertungen")

        # Filter: Zeitraum
        filter_typ = st.radio("Zeitraum anzeigen als:", ["Täglich", "Wöchentlich", "Monatlich"], horizontal=True)
        df = st.session_state["daten"].copy()

        if filter_typ == "Wöchentlich":
            df["Woche"] = df["Datum"].dt.isocalendar().week
            df["Jahr"] = df["Datum"].dt.isocalendar().year
            df = df.groupby(["Jahr", "Woche"]).mean(numeric_only=True).reset_index()
            df["Datum"] = pd.to_datetime(df["Jahr"].astype(str) + df["Woche"].astype(str) + '1', format='%G%V%u')
            df = df.drop(columns=["Jahr", "Woche"])

        elif filter_typ == "Monatlich":
            df["Jahr"] = df["Datum"].dt.year
            df["Monat"] = df["Datum"].dt.month
            df = df.groupby(["Jahr", "Monat"]).mean(numeric_only=True).reset_index()
            df["Datum"] = pd.to_datetime(df["Jahr"].astype(str) + "-" + df["Monat"].astype(str) + "-01")
            df = df.drop(columns=["Jahr", "Monat"])

        # Filter: Kategorie
        kategorien = ["Stimmung", "Schlaf", "Stress"]
        gewählte_kategorien = st.multiselect("Welche Kategorien sollen angezeigt werden?", kategorien, default=kategorien)

        df_plot = df[["Datum"] + gewählte_kategorien].melt(id_vars="Datum", var_name="Kategorie", value_name="Wert")

        chart = alt.Chart(df_plot).mark_line(point=True).encode(
            x=alt.X("Datum:T", axis=alt.Axis(format="%d.%m", title="Datum")),
            y=alt.Y("Wert:Q", scale=alt.Scale(domain=[1, 10]), title="Wert (1–10)"),
            color=alt.Color("Kategorie:N", scale=alt.Scale(domain=kategorien,
                                                           range=["#4CAF50", "#2196F3", "#F44336"]))
        ).properties(
            width=700,
            height=400
        )

        st.altair_chart(chart, use_container_width=True)

    with tab2:
        st.header("📊 Analyse deiner Entwicklung")

        df = st.session_state["daten"].copy()
        df["Woche"] = df["Datum"].dt.isocalendar().week
        df["Jahr"] = df["Datum"].dt.isocalendar().year
        df["Monat"] = df["Datum"].dt.to_period("M")

        letzte_woche = df["Woche"].max()
        vorletzte_woche = letzte_woche - 1

        analyse = []

        for k in ["Stimmung", "Schlaf", "Stress"]:
            aktuell = df[df["Woche"] == letzte_woche][k].mean()
            vorher = df[df["Woche"] == vorletzte_woche][k].mean()

            if pd.isna(vorher):
                trend = "🟡 Keine Vergleichsdaten"
            elif aktuell > vorher:
                trend = "🟢 Steigend"
            elif aktuell < vorher:
                trend = "🔴 Fallend"
            else:
                trend = "🟠 Stabil"

            analyse.append({
                "Kategorie": k,
                "Letzte Woche": round(aktuell, 2) if not pd.isna(aktuell) else "–",
                "Vorherige Woche": round(vorher, 2) if not pd.isna(vorher) else "–",
                "Trend": trend
            })

        st.table(pd.DataFrame(analyse))

        # Monatsdurchschnitte
        st.subheader("📆 Durchschnitt pro Monat")
        df_monat = df.groupby("Monat")[["Stimmung", "Schlaf", "Stress"]].mean().round(2)
        df_monat.index = df_monat.index.astype(str)
        st.dataframe(df_monat)

        # Korrelationen
        st.subheader("📉 Korrelationen zwischen Kategorien")

        df_corr = df[["Stimmung", "Schlaf", "Stress"]].corr()

        fig, ax = plt.subplots()
        sns.heatmap(df_corr, annot=True, cmap="coolwarm", vmin=-1, vmax=1, ax=ax, linewidths=.5)
        ax.set_title("Korrelationsmatrix")
        st.pyplot(fig)

    with tab3:
        st.header("📋 Eingetragene Rohdaten")
        df_anzeige = st.session_state["daten"].copy()
        df_anzeige = df_anzeige.sort_values("Datum", ascending=False) 
        df_anzeige["Datum"] = df_anzeige["Datum"].dt.strftime("%d.%m.%Y")
        st.dataframe(df_anzeige.set_index("Datum"))


        st.download_button(
            label="📥 Daten als CSV herunterladen",
            data=st.session_state["daten"].to_csv(index=False).encode("utf-8"),
            file_name="bewertung_export.csv",
            mime="text/csv"
        )

else:
    st.info("Noch keine Daten vorhanden. Bitte zuerst einen Eintrag speichern.")
