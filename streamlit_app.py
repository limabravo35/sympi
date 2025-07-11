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
MEDI_PFAD = "medikamente.csv"

# --- CSV laden ---
def lade_daten():
    if os.path.exists(DATEI_PFAD):
        df = pd.read_csv(DATEI_PFAD, parse_dates=["Datum"])
        df["Datum"] = pd.to_datetime(df["Datum"])
        return df.sort_values("Datum")
    else:
        return pd.DataFrame(columns=["Datum", "Stimmung", "Schlaf", "Stress"])

def lade_medikamente():
    if os.path.exists(MEDI_PFAD):
        df = pd.read_csv(MEDI_PFAD, parse_dates=["Datum"])
        df["Datum"] = pd.to_datetime(df["Datum"])
        return df.sort_values("Datum")
    else:
        return pd.DataFrame(columns=["Datum", "Kommentar"])

st.session_state["daten"] = lade_daten()
st.session_state["medikamente"] = lade_medikamente()

# --- Neue tägliche Bewertung ---
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

# --- Medikamentenänderung eintragen ---
with st.expander("💊 Medikamentenänderung eintragen"):
    with st.form("med_form"):
        med_datum = st.date_input("Datum der Änderung", value=datetime.date.today(), key="med_datum")
        kommentar = st.text_input("Kommentar (z. B. Sertralin auf 100 mg)", key="med_kommentar")
        submit_med = st.form_submit_button("Änderung speichern")

    if submit_med:
        if kommentar.strip() == "":
            st.warning("Bitte gib einen Kommentar ein.")
        else:
            med_df = pd.DataFrame([{"Datum": pd.to_datetime(med_datum), "Kommentar": kommentar}])
            alt_df = st.session_state["medikamente"]
            gesamt = pd.concat([alt_df, med_df]).drop_duplicates().sort_values("Datum")
            gesamt.to_csv(MEDI_PFAD, index=False)
            st.session_state["medikamente"] = gesamt
            st.success("Medikamentenänderung gespeichert!")

# --- Tabs ---
if not st.session_state["daten"].empty:
    tab1, tab2, tab3 = st.tabs(["📈 Verlauf", "📊 Analysen", "📋 Tabelle & Export"])

    # --- Verlauf ---
    with tab1:
        st.header("📈 Verlauf deiner Bewertungen")
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

        min_datum = df["Datum"].min().date()
        max_datum = df["Datum"].max().date()
        bereich = st.slider("Zeitraum eingrenzen", min_value=min_datum, max_value=max_datum,
                            value=(min_datum, max_datum), format="DD.MM.YYYY")
        df = df[(df["Datum"] >= pd.to_datetime(bereich[0])) & (df["Datum"] <= pd.to_datetime(bereich[1]))]

        kategorien = ["Stimmung", "Schlaf", "Stress"]
        gewählte_kategorien = st.multiselect("Welche Kategorien sollen angezeigt werden?", kategorien, default=kategorien)

        df_plot = df[["Datum"] + gewählte_kategorien].melt(id_vars="Datum", var_name="Kategorie", value_name="Wert")

        chart = alt.Chart(df_plot).mark_line(point=True).encode(
            x=alt.X("Datum:T", axis=alt.Axis(format="%d.%m", title="Datum")),
            y=alt.Y("Wert:Q", scale=alt.Scale(domain=[1, 10]), title="Wert (1–10)"),
            color=alt.Color("Kategorie:N", scale=alt.Scale(scheme="category10")),
            tooltip=["Datum:T", "Kategorie:N", "Wert:Q"]
        ).properties(
            width="container",
            height=400
        )

        if not st.session_state["medikamente"].empty:
            med_df = st.session_state["medikamente"]
            med_df["Datum"] = pd.to_datetime(med_df["Datum"])
            med_markierungen = alt.Chart(med_df).mark_rule(color="red").encode(
                x="Datum:T",
                tooltip=["Datum:T", "Kommentar:N"]
            )

            med_labels = alt.Chart(med_df).mark_text(
                align='left', baseline='bottom', dx=5, dy=-5, color="red"
            ).encode(
                x="Datum:T",
                y=alt.value(10),
                text="Kommentar:N"
            )

            chart = chart + med_markierungen + med_labels

        st.altair_chart(chart, use_container_width=True)

    # --- Analysen ---
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

        st.subheader("📆 Durchschnitt pro Monat")
        df_monat = df.groupby("Monat")[["Stimmung", "Schlaf", "Stress"]].mean().round(2)
        df_monat.index = df_monat.index.astype(str)
        st.dataframe(df_monat)

        st.subheader("📉 Korrelationen zwischen Kategorien")
        df_corr = df[["Stimmung", "Schlaf", "Stress"]].corr()
        fig, ax = plt.subplots()
        sns.heatmap(df_corr, annot=True, cmap="coolwarm", vmin=-1, vmax=1, ax=ax, linewidths=.5)
        ax.set_title("Korrelationsmatrix")
        st.pyplot(fig)

        st.subheader("💊 Durchschnitt vor/nach Medikamentenänderungen")
        medi_df = st.session_state["medikamente"]
        df_daten = st.session_state["daten"]
        zeilen = []
        for _, row in medi_df.iterrows():
            tag = pd.to_datetime(row["Datum"])
            kommentar = row["Kommentar"]
            vor = df_daten[(df_daten["Datum"] >= tag - pd.Timedelta(days=7)) & (df_daten["Datum"] < tag)]
            nach = df_daten[(df_daten["Datum"] > tag) & (df_daten["Datum"] <= tag + pd.Timedelta(days=7))]

            zeilen.append({
                "Änderung": kommentar,
                "Datum": tag.date(),
                "Stimmung vorher": round(vor["Stimmung"].mean(), 2) if not vor.empty else "–",
                "Stimmung nachher": round(nach["Stimmung"].mean(), 2) if not nach.empty else "–",
                "Schlaf vorher": round(vor["Schlaf"].mean(), 2) if not vor.empty else "–",
                "Schlaf nachher": round(nach["Schlaf"].mean(), 2) if not nach.empty else "–",
                "Stress vorher": round(vor["Stress"].mean(), 2) if not vor.empty else "–",
                "Stress nachher": round(nach["Stress"].mean(), 2) if not nach.empty else "–"
            })
        df_änderungen = pd.DataFrame(zeilen)
        st.dataframe(df_änderungen)

    # --- Tabelle & Export ---
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

        st.subheader("❌ Eintrag löschen")
        eintrag_liste = st.session_state["daten"].sort_values("Datum", ascending=False)
        löschen_datum = st.selectbox("Eintrag wählen", eintrag_liste["Datum"].dt.strftime("%d.%m.%Y"))
        if st.button("Eintrag löschen"):
            datum_dt = pd.to_datetime(löschen_datum, format="%d.%m.%Y")
            st.session_state["daten"] = eintrag_liste[eintrag_liste["Datum"] != datum_dt]
            st.session_state["daten"].to_csv(DATEI_PFAD, index=False)
            st.success("Eintrag gelöscht.")
            st.experimental_rerun()

        st.subheader("❌ Medikamentenänderung löschen")
        med_liste = st.session_state["medikamente"].sort_values("Datum", ascending=False)
        med_löschen_datum = st.selectbox("Änderung wählen", med_liste["Datum"].dt.strftime("%d.%m.%Y"), key="med_select")
        if st.button("Medikamentenänderung löschen"):
            datum_dt = pd.to_datetime(med_löschen_datum, format="%d.%m.%Y")
            st.session_state["medikamente"] = med_liste[med_liste["Datum"] != datum_dt]
            st.session_state["medikamente"].to_csv(MEDI_PFAD, index=False)
            st.success("Medikamentenänderung gelöscht.")
            st.experimental_rerun()

else:
    st.info("Noch keine Daten vorhanden. Bitte zuerst einen Eintrag speichern.")


