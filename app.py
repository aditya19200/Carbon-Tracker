

import os
import io
import datetime as dt
from typing import Optional, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from backend import Database


load_dotenv()
st.set_page_config(page_title="Carbon Tracker", page_icon="🌿", layout="wide")

CUSTOM_CSS = """
<style>
/* Tighter top padding */
.block-container { padding-top: 1.2rem; }

/* Metric cards */
.metric-wrap { display:flex; gap:16px; flex-wrap:wrap; }
div[data-testid="stMetricValue"] { font-size: 26px; }

/* Section headers */
h3, h4 { margin-top: 0.6rem; }

/* Table tweaks */
thead tr th { white-space: nowrap; }

/* Subtle card look */
.st-card { padding: 0.75rem 1rem; border: 1px solid rgba(128,128,128,0.15);
           border-radius: 12px; background: rgba(127,127,127,0.03); }

/* Sidebar compaction */
section[data-testid="stSidebar"] .block-container { padding-top: 0.6rem; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_db() -> Database:
    return Database()

def _safe_df(rows, columns=None) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=columns or [])
    return pd.DataFrame(rows)

def _paginate_df(df: pd.DataFrame, page: int, page_size: int) -> Tuple[pd.DataFrame, int]:
    if df.empty:
        return df, 0
    total_pages = (len(df) + page_size - 1) // page_size
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size
    return df.iloc[start:end], total_pages

def _download_csv(df: pd.DataFrame, filename: str, label: str):
    if df.empty:
        st.download_button(label, data=b"", file_name=filename, disabled=True, help="No data")
        return
    buff = io.StringIO()
    df.to_csv(buff, index=False)
    st.download_button(label, data=buff.getvalue(), file_name=filename, mime="text/csv")

def _query_params_set(user_id: Optional[int], dfrom: dt.date, dto: dt.date):
    st.query_params.clear()
    if user_id:
        st.query_params["user"] = str(user_id)
    if dfrom:
        st.query_params["from"] = str(dfrom)
    if dto:
        st.query_params["to"] = str(dto)


@st.cache_data(ttl=30, show_spinner=False)
def load_users():
    return get_db().list_users()

@st.cache_data(ttl=30, show_spinner=False)
def load_activities():
    return get_db().list_activities()

@st.cache_data(ttl=30, show_spinner=False)
def load_locations():
    return get_db().list_locations()

@st.cache_data(ttl=30, show_spinner=False)
def load_logs(user_id: Optional[int], dfrom: Optional[str], dto: Optional[str]):
    return get_db().list_logs(user_id=user_id, date_from=dfrom, date_to=dto)

@st.cache_data(ttl=30, show_spinner=False)
def proc_monthly_emissions(user_id: int, year: int, month: int):
    return get_db().monthly_emissions_by_category(user_id, year, month)

@st.cache_data(ttl=30, show_spinner=False)
def proc_ranking(user_id: int, start_date: str, end_date: str):
    return get_db().activity_ranking(user_id, start_date, end_date)

@st.cache_data(ttl=30, show_spinner=False)
def func_goal(user_id: int, year: int, month: int):
    return get_db().user_met_goal(user_id, year, month)


try:
    db = get_db()
    st.toast("Connected to MySQL", icon="✅")
except Exception as e:
    st.error(f"DB connection failed: {e}")
    st.stop()


users = load_users()
activities = load_activities()
locations = load_locations()

user_label_map = {f"{u['UserID']} — {u['Name']}": u["UserID"] for u in users}
user_id_to_name = {u["UserID"]: u["Name"] for u in users}


qp = st.query_params
today = dt.date.today()
first_of_month = today.replace(day=1)

def _parse_date(val: str, fallback: dt.date) -> dt.date:
    try:
        return dt.date.fromisoformat(val)
    except Exception:
        return fallback

default_user_from_qp: Optional[int] = None
if "user" in qp:
    try:
        cand = int(qp["user"])
        if any(u["UserID"] == cand for u in users):
            default_user_from_qp = cand
    except Exception:
        pass
default_from = _parse_date(qp.get("from", ""), first_of_month)
default_to = _parse_date(qp.get("to", ""), today)


st.title("🌿 Carbon Tracker")
st.caption("Elegant Streamlit UI with a thin Python backend over MySQL. Add logs, visualize emissions, and check monthly goals.")

fb1, fb2, fb3, fb4 = st.columns([3, 2, 2, 1.2])

user_display_choices = ["All"] + list(user_label_map.keys())
default_user_label = "All"
if default_user_from_qp:
    
    for lbl, uid in user_label_map.items():
        if uid == default_user_from_qp:
            default_user_label = lbl
            break

user_choice = fb1.selectbox("User", user_display_choices, index=user_display_choices.index(default_user_label))
picked_user_id = None if user_choice == "All" else user_label_map[user_choice]

dfrom = fb2.date_input("From", value=default_from, format="YYYY-MM-DD")
dto = fb3.date_input("To", value=default_to, format="YYYY-MM-DD")
apply_btn = fb4.button("Apply")

if apply_btn:
    _query_params_set(picked_user_id, dfrom, dto)

# tabs
tab_dash, tab_logs, tab_add, tab_master = st.tabs(["📊 Dashboard", "🧾 Logs", "➕ Add / Import Logs", "🛠 Master Data"])

# LOGS (shared for multiple tabs) 
raw_logs = load_logs(picked_user_id, str(dfrom), str(dto))
df_logs = _safe_df(
    raw_logs,
    columns=["LogID", "UserName", "ActivityName", "Date", "Quantity", "CalculatedEmission", "City", "Country"],
)

#  Dashboard 
with tab_dash:
    st.subheader("Overview")

    # Quick KPIs
    total_emission = float(df_logs["CalculatedEmission"].sum()) if not df_logs.empty else 0.0
    total_entries = int(df_logs.shape[0]) if not df_logs.empty else 0
    unique_acts = int(df_logs["ActivityName"].nunique()) if not df_logs.empty else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("Total Emission (kgCO₂)", f"{total_emission:.3f}")
    k2.metric("Entries", f"{total_entries}")
    k3.metric("Unique Activities", f"{unique_acts}")

    # Time-series view
    st.markdown("#### Emission over Time")
    if not df_logs.empty:
        ts = df_logs.copy()
        ts["Date"] = pd.to_datetime(ts["Date"]).dt.date
        daily = ts.groupby("Date", as_index=False)["CalculatedEmission"].sum()
        fig_ts = px.line(daily, x="Date", y="CalculatedEmission", markers=True, title="Daily Emission")
        st.plotly_chart(fig_ts, use_container_width=True)
    else:
        st.info("No logs found for the selected range.")

    # Monthly by Category (procedure)
    st.markdown("#### Monthly Emissions by Category")
    if picked_user_id:
        ycol, mcol, tcol = st.columns([1, 1, 1])
        sel_year = ycol.number_input("Year", min_value=2000, max_value=2100, value=today.year, step=1)
        sel_month = mcol.number_input("Month", min_value=1, max_value=12, value=today.month, step=1)
        if tcol.button("Refresh Category Chart"):
            st.cache_data.clear()  
        try:
            cat_rows = proc_monthly_emissions(picked_user_id, int(sel_year), int(sel_month))
            df_cat = _safe_df(cat_rows)
            if not df_cat.empty:
                # Expect columns: CategoryName, TotalEmission_kgCO2
                fig_cat = px.bar(
                    df_cat.sort_values("TotalEmission_kgCO2", ascending=False),
                    x="CategoryName", y="TotalEmission_kgCO2",
                    title=f"Emissions by Category — {sel_year}-{sel_month:02d}"
                )
                st.plotly_chart(fig_cat, use_container_width=True)
                st.dataframe(df_cat, use_container_width=True, height=260)
                _download_csv(df_cat, "monthly_by_category.csv", "⬇️ Download table (CSV)")
            else:
                st.info("No data for the selected month.")
        except Exception as e:
            st.error(f"Procedure failed: {e}")

    else:
        st.info("Pick a specific user to view Monthly Category breakdown and Goal check.")

    # Ranking (procedure)
    st.markdown("#### Highest Emitting Activities")
    if picked_user_id:
        c1, c2, c3 = st.columns([1, 1, 1])
        rs = c1.date_input("Start date", value=dfrom)
        re = c2.date_input("End date", value=dto)
        if c3.button("Refresh Ranking"):
            st.cache_data.clear()
        try:
            rank_rows = proc_ranking(picked_user_id, str(rs), str(re))
            df_rank = _safe_df(rank_rows)
            if not df_rank.empty:
                fig_rank = px.bar(
                    df_rank.sort_values("TotalEmission_kgCO2", ascending=False),
                    x="ActivityName", y="TotalEmission_kgCO2", color="CategoryName",
                    title="Activity Ranking by Emission", barmode="relative"
                )
                st.plotly_chart(fig_rank, use_container_width=True)
                st.dataframe(df_rank, use_container_width=True, height=260)
                _download_csv(df_rank, "activity_ranking.csv", "⬇️ Download ranking (CSV)")
            else:
                st.info("No activity data in the selected range.")
        except Exception as e:
            st.error(f"Procedure failed: {e}")

    # Goal check
    st.markdown("#### Goal Check (this month)")
    if picked_user_id:
        try:
            met = func_goal(picked_user_id, today.year, today.month)
            if met is True:
                st.success("✅ Goal Met (monthly emission is below CarbonGoal)")
            elif met is False:
                st.warning("⚠️ Goal Not Met")
            else:
                st.info("No result from function.")
        except Exception as e:
            st.error(f"Goal check failed: {e}")

# Logs Tab 
with tab_logs:
    st.subheader("Activity Logs")
    if df_logs.empty:
        st.info("No logs to show. Try expanding your date range or add new logs in the **Add / Import Logs** tab.")
    else:
        # Controls
        lc1, lc2, lc3, lc4 = st.columns([1, 1, 1, 1])
        page_size = lc1.select_slider("Rows / page", [10, 20, 30, 50, 100], value=20)
        page = lc2.number_input("Page", min_value=1, step=1, value=1)
        sort_col = lc3.selectbox("Sort by", options=df_logs.columns.tolist(), index=df_logs.columns.get_loc("Date"))
        ascending = lc4.toggle("Ascending", value=False)

        sdf = df_logs.sort_values(sort_col, ascending=ascending, kind="mergesort")
        view, total_pages = _paginate_df(sdf, page, page_size)
        if total_pages and page > total_pages:
            st.warning(f"Page reset to 1 (only {total_pages} pages).")
            view, total_pages = _paginate_df(sdf, 1, page_size)

        st.dataframe(view, use_container_width=True, height=420)
        cdl, _, _ = st.columns([1.2, 1, 1])
        _download_csv(sdf, "logs_filtered.csv", "⬇️ Download logs (CSV)")

        # Delete section
        st.markdown("##### Delete a Log")
        dd1, dd2 = st.columns([1, 3])
        del_id = dd1.number_input("LogID", min_value=0, step=1, value=0)
        if dd2.button("🗑️ Delete"):
            if del_id <= 0:
                st.warning("Enter a valid LogID.")
            else:
                try:
                    deleted = db.delete_log(int(del_id))
                    if deleted:
                        st.toast(f"Deleted LogID {del_id}", icon="🗑️")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.info("No row deleted; check the LogID.")
                except Exception as e:
                    st.error(f"Delete failed: {e}")

# ---------- Add / Import Logs ----------
with tab_add:
    st.subheader("Add Activity Log")
    if not users:
        st.warning("Please create a user first in **Master Data**.")
    else:
        # User must be specific when inserting (not All)
        ins_user_id = picked_user_id
        if ins_user_id is None:
            st.info("Select a specific user in the top bar to add logs.")
        else:
            # Build activity / location pickers
            # activities: expect keys: ActivityID, Name, UnitOfMeasure, CategoryName
            act_labels = []
            act_id_map = {}
            for a in activities:
                nm = a.get("Name") or a.get("ActivityName") or f"Activity {a.get('ActivityID')}"
                u = a.get("UnitOfMeasure") or ""
                lab = f"{a['ActivityID']} — {nm}{f' ({u})' if u else ''}"
                act_labels.append(lab)
                act_id_map[lab] = a["ActivityID"]

            loc_labels = ["(None)"]
            loc_id_map = {"(None)": None}
            for l in locations:
                lab = f"{l['LocationID']} — {l['City']}, {l['Country']}"
                loc_labels.append(lab)
                loc_id_map[lab] = l["LocationID"]

            c1, c2 = st.columns([2, 1])
            act_choice = c1.selectbox("Activity", act_labels)
            qty = c2.number_input("Quantity", min_value=0.0, value=1.0, step=0.25)
            d1, d2 = st.columns([1, 1])
            log_date = d1.date_input("Date", value=dt.date.today())
            loc_choice = d2.selectbox("Location (optional)", loc_labels)

            if st.button("➕ Add Log"):
                try:
                    new_id = db.add_log(
                        user_id=ins_user_id,
                        activity_id=act_id_map[act_choice],
                        date=str(log_date),
                        qty=float(qty),
                        location_id=loc_id_map[loc_choice],
                    )
                    st.toast(f"Inserted LogID {new_id}", icon="✅")
                    
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Insert failed: {e}")

    st.markdown("---")
    st.subheader("Bulk Import (CSV)")
    with st.expander("Template & Uploader", expanded=False):
        st.caption("Upload CSV with columns: `ActivityID,Date,Quantity,LocationID` (LocationID optional). The selected User in the top filter will be used.")
        sample = pd.DataFrame({
            "ActivityID": [1, 2],
            "Date": [str(today), str(today)],
            "Quantity": [2.5, 1.0],
            "LocationID": [None, None],
        })
        _download_csv(sample, "import_template.csv", "⬇️ Download CSV template")

        file = st.file_uploader("Upload CSV", type=["csv"])
        if file is not None:
            try:
                df_imp = pd.read_csv(file)
                st.dataframe(df_imp, use_container_width=True, height=240)
                valid_cols = {"ActivityID", "Date", "Quantity"}
                if not valid_cols.issubset(df_imp.columns):
                    st.error("CSV must include columns: ActivityID, Date, Quantity. (LocationID optional)")
                elif picked_user_id is None:
                    st.error("Select a specific User in the top bar before importing.")
                else:
                    if st.button("📥 Import Rows"):
                        inserted = 0
                        for _, r in df_imp.iterrows():
                            try:
                                db.add_log(
                                    user_id=picked_user_id,
                                    activity_id=int(r["ActivityID"]),
                                    date=str(r["Date"]),
                                    qty=float(r["Quantity"]),
                                    location_id=(int(r["LocationID"]) if "LocationID" in df_imp.columns and pd.notna(r["LocationID"]) else None),
                                )
                                inserted += 1
                            except Exception as ie:
                                st.warning(f"Row failed: {ie}")
                        st.toast(f"Imported {inserted} rows", icon="📥")
                        st.cache_data.clear()
            except Exception as e:
                st.error(f"Import error: {e}")

#  Master Data 
with tab_master:
    st.subheader("Users")
    df_users = _safe_df(load_users())
    if df_users.empty:
        st.info("No users found. Create one below.")
    else:
        st.dataframe(df_users, use_container_width=True, height=260)

    st.markdown("##### Create User")
    m1, m2 = st.columns([1.5, 1.5])
    with m1:
        u_name = st.text_input("Name")
        u_email = st.text_input("Email")
        u_pass = st.text_input("Password", type="password")
    with m2:
        u_goal = st.number_input("Carbon Goal (monthly, kgCO₂)", min_value=0.0, step=10.0, value=300.0)
        u_reg = st.date_input("Registration Date", value=dt.date.today())

    if st.button("👤 Add User"):
        if not u_name or not u_email or not u_pass:
            st.warning("Name, Email, and Password are required.")
        else:
            try:
                uid = db.add_user(u_name, u_email, u_pass, u_goal, str(u_reg))
                st.toast(f"User created (UserID {uid})", icon="✅")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Create user failed: {e}")

    st.markdown("---")
    st.subheader("Activities")
    df_acts = _safe_df(load_activities())
    if df_acts.empty:
        st.info("No activities found.")
    else:
        
        show_cols = [c for c in df_acts.columns if c in ["ActivityID", "Name", "UnitOfMeasure", "CategoryName", "EmissionValue"]]
        st.dataframe(df_acts[show_cols] if show_cols else df_acts, use_container_width=True, height=300)

#  Footer 
st.caption("Built with Streamlit • MySQL • Plotly — minimal backend, clean frontend.")
