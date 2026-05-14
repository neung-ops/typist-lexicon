import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import time

# --- CONFIG & DATABASE ---
DB_NAME = "vocab_vault.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # สร้างตารางพร้อมรองรับ Part of Speech และ Example
    c.execute('''CREATE TABLE IF NOT EXISTS vocab 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  word TEXT UNIQUE, 
                  pos TEXT,
                  translation TEXT, 
                  example TEXT,
                  level TEXT, 
                  interval INTEGER, 
                  easiness REAL, 
                  next_review TEXT,
                  mastery_score INTEGER DEFAULT 0)''')
    
    # เช็คว่ามีคอลัมน์ใหม่หรือยัง (สำหรับ Migration)
    c.execute("PRAGMA table_info(vocab)")
    columns = [column[1] for column in c.fetchall()]
    if 'pos' not in columns:
        c.execute("ALTER TABLE vocab ADD COLUMN pos TEXT")
    if 'example' not in columns:
        c.execute("ALTER TABLE vocab ADD COLUMN example TEXT")
        
    # เพิ่มคำศัพท์เริ่มต้น (ถ้ายังไม่มี)
    c.execute("SELECT COUNT(*) FROM vocab")
    if c.fetchone()[0] == 0:
        initial_words = [
            ('Analyze', 'v.', 'วิเคราะห์', 'We need to analyze the results of the experiment.', 'B1', 1, 2.5, datetime.now().strftime('%Y-%m-%d')),
            ('Implement', 'v.', 'ทำให้เกิดผล, นำมาใช้', 'The company decided to implement a new policy.', 'B2', 1, 2.5, datetime.now().strftime('%Y-%m-%d')),
            ('Comprehensive', 'adj.', 'ครอบคลุม', 'This is a comprehensive study of the market.', 'C1', 1, 2.5, datetime.now().strftime('%Y-%m-%d'))
        ]
        c.executemany("INSERT INTO vocab (word, pos, translation, example, level, interval, easiness, next_review) VALUES (?,?,?,?,?,?,?,?)", initial_words)
    
    conn.commit()
    conn.close()

def update_srs(word_id, success):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT interval, easiness, mastery_score FROM vocab WHERE id = ?", (int(word_id),))
    row = c.fetchone()
    if not row: return
    
    interval, easiness, mastery = row
    
    if success:
        # ระบบ SM-2 อย่างง่าย
        if interval == 0: interval = 1
        elif interval == 1: interval = 3
        else: interval = int(interval * easiness)
        mastery = min(100, mastery + 20)
    else:
        interval = 1 # พิมพ์ผิดให้กลับมาเริ่มใหม่พรุ่งนี้
        easiness = max(1.3, easiness - 0.2)
        mastery = max(0, mastery - 10)
        
    next_review = (datetime.now() + timedelta(days=interval)).strftime('%Y-%m-%d')
    c.execute("UPDATE vocab SET interval = ?, easiness = ?, next_review = ?, mastery_score = ? WHERE id = ?", 
              (interval, easiness, next_review, mastery, int(word_id)))
    conn.commit()
    conn.close()

# --- MAIN APP ---
st.set_page_config(page_title="Typist Lexicon v2", layout="wide")
init_db()

# Custom CSS สำหรับ UI ทันสมัย
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stTextInput input { font-size: 2rem !important; text-align: center; border-radius: 15px; border: 2px solid #3e4452; }
    .vocab-card { background: #1f2937; padding: 40px; border-radius: 20px; text-align: center; border: 1px solid #374151; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5); }
    .word-main { font-size: 5rem; font-weight: 800; color: #60a5fa; margin-bottom: 0px; }
    .pos-tag { color: #9ca3af; font-style: italic; font-size: 1.2rem; }
    .trans-main { font-size: 2rem; color: #f3f4f6; margin-top: 10px; }
    .example-box { background: #111827; padding: 20px; border-radius: 10px; margin-top: 25px; color: #d1d5db; border-left: 5px solid #60a5fa; text-align: left; }
    </style>
""", unsafe_allow_image_ Wood=True)

tab1, tab2, tab3 = st.tabs(["🎯 Practice", "📊 Stats", "➕ Add Word"])

with tab1:
    conn = sqlite3.connect(DB_NAME)
    today = datetime.now().strftime('%Y-%m-%d')
    # ดึงคำที่ต้องทบทวน
    df_due = pd.read_sql_query("SELECT * FROM vocab WHERE next_review <= ?", conn, params=(today,))
    conn.close()

    if not df_due.empty:
        target = df_due.iloc[0]
        
        # Display Card
        st.markdown(f"""
            <div class="vocab-card">
                <div class="pos-tag">Level: {target['level']} | {target['pos']}</div>
                <div class="word-main">{target['word']}</div>
                <div class="trans-main">{target['translation']}</div>
                <div class="example-box">
                    <strong>Example:</strong><br>
                    {target['example'] if target['example'] else 'No example provided.'}
                </div>
            </div>
        """, unsafe_allow_image_ Wood=True)
        
        st.write("") # Spacer
        
        # Input Section
        input_key = f"input_{target['id']}"
        user_input = st.text_input("Type exactly to master this word:", key=input_key, placeholder="Type here...")

        if user_input:
            if user_input.strip().lower() == target['word'].lower():
                update_srs(target['id'], True)
                st.toast(f"✅ Amazing! '{target['word']}' updated.", icon='🚀')
                time.sleep(0.6)
                st.rerun()
            else:
                if len(user_input) >= len(target['word']):
                    st.error("Oops! Try again.")
                    update_srs(target['id'], False)
    else:
        st.balloons()
        st.success("All caught up! You've mastered all words for today.")

with tab2:
    st.header("Your Progress Dashboard")
    conn = sqlite3.connect(DB_NAME)
    df_all = pd.read_sql_query("SELECT * FROM vocab", conn)
    conn.close()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Words", len(df_all))
    col2.metric("Avg. Mastery", f"{int(df_all['mastery_score'].mean())}%")
    col3.metric("Due Today", len(df_due))
    
    st.subheader("Vocabulary List")
    st.dataframe(df_all[['word', 'pos', 'level', 'translation', 'mastery_score', 'next_review']], use_container_width=True)

with tab3:
    st.header("Add New Vocabulary")
    with st.form("add_form", clear_on_submit=True):
        new_word = st.text_input("Word")
        new_pos = st.selectbox("Type", ["n.", "v.", "adj.", "adv.", "phr."])
        new_trans = st.text_input("Thai Translation")
        new_example = st.text_area("Example Sentence")
        new_level = st.select_slider("Level", options=["A1", "A2", "B1", "B2", "C1", "C2"], value="B1")
        
        if st.form_submit_button("Save to Vault"):
            if new_word and new_trans:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO vocab (word, pos, translation, example, level, interval, easiness, next_review) VALUES (?,?,?,?,?,?,?,?)",
                              (new_word, new_pos, new_trans, new_example, new_level, 1, 2.5, datetime.now().strftime('%Y-%m-%d')))
                    conn.commit()
                    st.success(f"Added {new_word}!")
                except:
                    st.error("This word already exists.")
                conn.close()
