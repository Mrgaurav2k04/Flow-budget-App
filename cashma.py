import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import os

# --- LOAD ASSETS ---
try:
    # Try to load the local App logo if available
    app_icon = Image.open("App logo.png")
except FileNotFoundError:
    app_icon = "🏦" # Fallback

# --- UI SETTINGS ---
st.set_page_config(page_title="FLOW | Cashma", layout="centered", page_icon=app_icon)

# Add logo to the sidebar to make it feel like a real app
if app_icon != "🏦":
    st.sidebar.image(app_icon, use_container_width=True)

# Custom Gen Z Dark Mode CSS
st.markdown("""
    <style>
    .main { background-color: #050505; color: white; }
    div[data-testid="stMetricValue"] { color: #00FFA3; font-weight: bold; }
    .stButton>button { 
        width: 100%; 
        border-radius: 15px; 
        height: 3em; 
        background-color: #00FFA3; 
        color: black; 
        font-weight: bold; 
        border: none; 
        transition: 0.3s;
    }
    .stButton>button:hover { 
        background-color: #00cc82; 
        color: white; 
        border: 1px solid #00FFA3;
    }
    /* Style headers */
    h1, h2, h3 { color: #E0E0E0; font-family: 'sans-serif'; }
    /* Enhance the sidebar */
    [data-testid="stSidebar"] { background-color: #111111; }
    </style>
    """, unsafe_allow_html=True)

DATA_FILE = "cashma_transactions.csv"

# --- DATA MANAGEMENT ---
def load_transactions():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        # Ensure 'time' column is string
        if not df.empty and 'time' in df.columns:
            df['time'] = df['time'].astype(str)
        return df
    else:
        return pd.DataFrame(columns=["time", "type", "amount", "category", "note"])

def save_transaction(trans_dict):
    df = load_transactions()
    new_row = pd.DataFrame([trans_dict])
    # Use pd.concat instead of append (deprecated)
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    return df

def clear_data():
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)

# Initialize session state for reactivity
if 'transactions' not in st.session_state:
    st.session_state.transactions = load_transactions()

df_trans = st.session_state.transactions

# Ensure time column exists and is string before processing
if not df_trans.empty and 'time' in df_trans.columns:
    df_trans['time'] = df_trans['time'].astype(str)

# Calculate Balances
if not df_trans.empty:
    total_credits = df_trans[df_trans['type'] == 'Credit']['amount'].sum()
    total_debits = df_trans[df_trans['type'] == 'Debit']['amount'].sum()
else:
    total_credits = 0.0
    total_debits = 0.0

current_balance = total_credits - total_debits

# --- SIDEBAR CONFIG ---
st.sidebar.title("⚙️ Setup Your Flow")
st.sidebar.markdown(f"### Overall Balance: **₹{current_balance:,.2f}**")
savings_target = st.sidebar.number_input("Savings Goal (₹)", value=1000.0, step=100.0)
days_in_month = st.sidebar.number_input("Days remaining in month", min_value=1, max_value=31, value=30, step=1)

# Calculate Safe Balance
if current_balance < savings_target:
    st.sidebar.error("Warning: Savings target is higher than your balance!")
    safe_balance = 0
else:
    safe_balance = current_balance - savings_target

daily_limit = safe_balance / days_in_month if days_in_month > 0 else 0

# Calculate totals for today
today_str = datetime.now().strftime("%Y-%m-%d")
today_debits = 0.0
if not df_trans.empty and 'time' in df_trans.columns:
    df_trans['date_only'] = df_trans['time'].apply(lambda x: x.split(" ")[0] if isinstance(x, str) else "")
    today_records = df_trans[df_trans['date_only'] == today_str]
    today_debits = today_records[today_records['type'] == 'Debit']['amount'].sum()

# Remaining today is exactly the daily limit minus what we spent today
# (Credits are already factored into the Total Balance -> Safe Balance -> Daily Limit)
remaining_today = daily_limit - today_debits

# --- MAIN APP ---
st.title("🏦 FLOW (Cashma)")
st.write("### Your Personal Bank & Tracker")

# Metrics Display
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Total Balance", value=f"₹{current_balance:,.0f}")
with col2:
    st.metric(label="Daily Budget", value=f"₹{daily_limit:,.0f}")
with col3:
    st.metric(label="Remaining Today", value=f"₹{remaining_today:,.0f}", 
              delta=f"-₹{today_debits:,.0f}" if today_debits > 0 else None, 
              delta_color="inverse")

# Progress bar for today's budget
if daily_limit > 0:
    progression = min(today_debits / daily_limit, 1.0)
    st.progress(progression, text=f"Used {progression*100:.1f}% of today's budget")
    if progression >= 0.9:
        st.warning("⚠️ You're dangerously close to your daily limit! Hold up!")

st.write("---")

# --- TRANSACTION LOGGER ---    
st.write("### � Log a Transaction")

trans_type = st.radio("Type", ["Debit", "Credit"], horizontal=True)

with st.form("transaction_form", clear_on_submit=False):
    col1, col2 = st.columns([1, 1])
    
    with col1:
        amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0, format="%.2f")
    
    with col2:
        if trans_type == "Debit":
            category = st.selectbox("Category", ["Food 🍔", "Transport 🚕", "Chill 🎮", "Study 📚", "Shopping 🛍️", "Other 📦"])
            note = st.text_input("Note (e.g., Lunch, Movie)")
        else:
            category = st.text_input("From (e.g., Dad, Freelance Project)")
            note = st.text_input("Note (Optional, e.g., Monthly Allowance)")
            
    submitted = st.form_submit_button("Log Transaction 🚀")
    
    if submitted:
        if amount > 0:
            if trans_type == "Credit" and not category.strip():
                st.error("Please enter who this credit is 'From'.")
            else:
                new_trans = {
                    "time": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
                    "type": trans_type,
                    "amount": amount,
                    "category": category,
                    "note": note if note else "No note"
                }
                # Save to CSV and update session state
                st.session_state.transactions = save_transaction(new_trans)
                
                if trans_type == "Credit":
                    st.balloons()
                    st.success(f"Money IN! 🤑 Credited ₹{amount} from {category}.")
                else:
                    st.success(f"Logged ₹{amount} for {note or category}. Budget updated!")
                st.rerun()
        else:
            st.error("Please enter an amount greater than 0.")

# --- HISTORY & ANALYTICS ---
if not df_trans.empty:
    st.write("---")
    st.write("### 📜 Transaction History")
    
    # Pre-process for display
    display_df = df_trans.drop(columns=['date_only'], errors='ignore').copy()
    display_df = display_df.sort_index(ascending=False) # Most recent first
    
    # Format amount with sign
    display_df['amount_display'] = display_df.apply(
        lambda row: f"+₹{row['amount']:.2f}" if row['type'] == 'Credit' else f"-₹{row['amount']:.2f}",
        axis=1
    )
    
    display_cols = display_df[['time', 'type', 'category', 'note', 'amount_display']]
    st.dataframe(
        display_cols,
        use_container_width=True,
        hide_index=True
    )
    
    # Breakdown by category (Debits only)
    st.write("#### Spending by Category")
    debits_df = df_trans[df_trans['type'] == 'Debit']
    if not debits_df.empty:
        category_totals = debits_df.groupby('category')['amount'].sum().reset_index()
        st.bar_chart(category_totals.set_index('category'))
    else:
        st.info("No spending data yet to show category breakdown.")
    
    # Option to clear history
    _, col = st.columns([3, 1])
    with col:
        if st.button("Clear History 🗑️"):
            clear_data()
            st.session_state.transactions = load_transactions()
            st.rerun()

st.write("---")
st.caption("Flow (Cashma) v3.0 | Your Personal Bank & Budgeting App")
