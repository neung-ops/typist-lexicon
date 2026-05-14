import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import random
import plotly.express as px

# --- 1. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('vocab_vault.db')
    c = conn.cursor()
    # Table for vocabulary and SRS stats
    c.execute('''CREATE TABLE IF NOT EXISTS vocabulary
                 (id INTEGER PRIMARY KEY, 
                  word TEXT UNIQUE, 
                  translation TEXT, 
                  level TEXT,
                  interval INTEGER DEFAULT 0, 
                  easiness REAL DEFAULT 2.5,
                  next_review DATE,
                  status TEXT DEFAULT 'New')''')
    
    # Table for activity logs (for analytics)
    c.execute('''CREATE TABLE IF NOT EXISTS activity_log
                 (id INTEGER PRIMARY KEY, 
                  word_id INTEGER, 
                  timestamp DATETIME, 
                  is_correct INTEGER,
                  speed_wpm REAL)''')
    
    # Pre-seed with some Oxford 3000 words if empty
    c.execute("SELECT count(*) FROM vocabulary")
    if c.fetchone()[0] == 0:
        initial_words = [
            ("Analyze", "วิเคราะห์", "B1"),
            ("Comprehensive", "ครอบคลุม", "C1"),
            ("Implement", "นำไปปฏิบัติ", "B2"),
            ("Efficient", "ที่มีประสิทธิภาพ", "B1"),
            ("Perspective", "มุมมอง", "B2"),
            ("Consistent", "สม่ำเสมอ", "B2")
        ]
        for w, t, l in initial_words:
            c.execute("INSERT INTO vocabulary (word, translation, level, next_review) VALUES (?, ?, ?, ?)",
                      (w, t, l, datetime.now().date()))
    conn.commit()
    return conn

# --- 2. SRS LOGIC (SM-2 Simplified) ---
def update_srs(word_id, is_correct):
    # แปลง word_id เป็น int มาตรฐานของ python เพื่อป้องกัน error กับ sqlite
    word_id = int(word_id)
    conn = sqlite3.connect('vocab_vault.db')
    c = conn.cursor()
    c.execute("SELECT interval, easiness FROM vocabulary WHERE id = ?", (word_id,))
    row = c.fetchone()
    
    if row is None:
        conn.close()
        return

    interval, easiness = row

    if is_correct:
        if interval == 0:
            new_interval = 1
        elif interval == 1:
            new_interval = 3
        else:
            new_interval = int(interval * easiness)
        new_easiness = easiness + 0.1
        status = 'Mastering' if new_interval > 14 else 'Learning'
    else:
        new_interval = 0  # Start over
        new_easiness = max(1.3, easiness - 0.2)
        status = 'Relearning'

    next_review = datetime.now().date() + timedelta(days=new_interval)
    c.execute("UPDATE vocabulary SET interval=?, easiness=?, next_review=?, status=? WHERE id=?",
              (new_interval, new_easiness, next_review, status, word_id))
    conn.commit()
    conn.close()

# --- 3. UI STYLING ---
st.set_page_config(page_title="Typist Lexicon", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #E0E0E0; }
    .stTextInput > div > div > input {
        font-size: 24px; text-align: center; border-radius: 15px;
        border: 2px solid #4F46E5; background-color: #1F2937; color: white;
    }
    .vocab-card {
        background: rgba(255, 255, 255, 0.05); padding: 30px;
        border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center; margin-bottom: 20px;
    }
    .thai-translation { color: #A855F7; font-size: 1.5rem; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. MAIN APP LOGIC ---
def main():
    conn = init_db()
    
    st.title("⌨️ Typist Lexicon")
    st.markdown("Master Vocabulary through Muscle Memory & SRS")

    tab1, tab2, tab3 = st.tabs(["🚀 Practice", "📊 Analytics", "📚 Word Vault"])

    with tab1:
        # Fetch words due for review
        today = datetime.now().date()
        df_due = pd.read_sql_query(f"SELECT * FROM vocabulary WHERE next_review <= '{today}'", conn)
        
        if not df_due.empty:
            target_word_row = df_due.iloc[0]
            target_word = target_word_row['word']
            
            st.markdown(f"""
                <div class="vocab-card">
                    <p style='color: #94A3B8; margin:0;'>Level: {target_word_row['level']}</p>
                    <h1 style='font-size: 4rem; margin: 10px 0;'>{target_word}</h1>
                    <p class="thai-translation">{target_word_row['translation']}</p>
                </div>
            """, unsafe_allow_html=True)

            # Input area with auto-clear logic
            user_input = st.text_input("Type the word exactly to continue...", key="typing_area")

            if user_input:
                if user_input.strip().lower() == target_word.lower():
                    update_srs(target_word_row['id'], True)
                    
                    # Log activity
                    c = conn.cursor()
                    c.execute("INSERT INTO activity_log (word_id, timestamp, is_correct) VALUES (?, ?, ?)",
                              (int(target_word_row['id']), datetime.now(), 1))
                    conn.commit()
                    
                    st.toast("Correct! Muscle memory engaged. 🎯")
                    time.sleep(0.5) # ให้เวลาคนดูความสำเร็จแป๊บนึง
                    st.rerun() # รีเฟรชเพื่อไปคำถัดไปทันที
                else:
                    # ถ้าพิมพ์จนครบความยาวแล้วยังผิด
                    if len(user_input) >= len(target_word):
                        st.error("Incorrect. Try again!")
                        update_srs(target_word_row['id'], False)
        else:
            st.info("🎉 All caught up! No words due for review right now. Add more in 'Word Vault'.")

    with tab2:
        st.header("Your Progress Insights")
        df_all = pd.read_sql_query("SELECT status, count(*) as count FROM vocabulary GROUP BY status", conn)
        
        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(df_all, values='count', names='status', title='Learning Mastery Distribution',
                         color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            st.metric("Total Words in Database", len(pd.read_sql_query("SELECT * FROM vocabulary", conn)))
            st.write("Keep typing every day to move words to 'Mastered' status.")

    with tab3:
        st.header("Vocabulary Management")
        with st.expander("➕ Add New Word"):
            new_word = st.text_input("English Word")
            new_trans = st.text_input("Thai Translation")
            new_level = st.selectbox("Level", ["A1", "A2", "B1", "B2", "C1", "C2"])
            if st.button("Add to Vault"):
                if new_word and new_trans:
                    try:
                        c = conn.cursor()
                        c.execute("INSERT INTO vocabulary (word, translation, level, next_review) VALUES (?, ?, ?, ?)",
                                  (new_word, new_trans, new_level, datetime.now().date()))
                        conn.commit()
                        st.success(f"Added '{new_word}'!")
                    except:
                        st.warning("Word already exists in vault.")
        
        df_vault = pd.read_sql_query("SELECT word, translation, level, status, next_review FROM vocabulary", conn)
        st.dataframe(df_vault, use_container_width=True)

if __name__ == "__main__":
    main()
