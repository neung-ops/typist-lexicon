import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import time
import random

# --- STREAMING_CHUNK:Configuring Database and Global State... ---
DB_NAME = "vocab_pro.db"

# Initialize Session States
if 'session_queue' not in st.session_state:
    st.session_state.session_queue = [] # เก็บคำที่พิมพ์ผ่านแล้วในรอบนี้
if 'quiz_phase' not in st.session_state:
    st.session_state.quiz_phase = False
if 'quiz_index' not in st.session_state:
    st.session_state.quiz_index = 0
if 'current_options' not in st.session_state:
    st.session_state.current_options = []

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vocab 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  word TEXT UNIQUE, pos TEXT, translation TEXT, 
                  example TEXT, level TEXT, interval INTEGER DEFAULT 0, 
                  easiness REAL DEFAULT 2.5, next_review TEXT, mastery_score INTEGER DEFAULT 0)''')
    
    # Check for existing data or add starter pack
    c.execute("SELECT COUNT(*) FROM vocab")
    if c.fetchone()[0] == 0:
        now = datetime.now().strftime('%Y-%m-%d')
        starters = [
            ('Analyze', 'v.', 'วิเคราะห์', 'We need to analyze the results.', 'B1', 0, 2.5, now),
            ('Comprehensive', 'adj.', 'ครอบคลุม', 'A comprehensive guide to coding.', 'C1', 0, 2.5, now),
            ('Implement', 'v.', 'นำมาใช้', 'Let\'s implement the new feature.', 'B2', 0, 2.5, now),
            ('Ambiguous', 'adj.', 'กวม, ไม่ชัดเจน', 'His answer was very ambiguous.', 'C1', 0, 2.5, now),
            ('Facilitate', 'v.', 'อำนวยความสะดวก', 'The app facilitates learning.', 'B2', 0, 2.5, now)
        ]
        c.executemany("INSERT INTO vocab (word, pos, translation, example, level, interval, easiness, next_review) VALUES (?,?,?,?,?,?,?,?)", starters)
    conn.commit()
    conn.close()

# --- STREAMING_CHUNK:Defining Helper Functions for SRS and Quiz... ---
def get_distractors(correct_answer):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT translation FROM vocab WHERE translation != ? ORDER BY RANDOM() LIMIT 3", (correct_answer,))
    others = [row[0] for row in c.fetchall()]
    conn.close()
    while len(others) < 3: others.append("ตัวเลือกสุ่ม " + str(len(others)))
    return others

def update_srs(word_id, success):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT interval, easiness, mastery_score FROM vocab WHERE id = ?", (int(word_id),))
    row = c.fetchone()
    if not row: return
    interval, easiness, mastery = row
    
    if success:
        new_interval = 1 if interval == 0 else (3 if interval == 1 else int(interval * easiness))
        new_mastery = min(100, mastery + 15)
        new_easiness = easiness + 0.1
    else:
        new_interval = 0 
        new_mastery = max(0, mastery - 20)
        new_easiness = max(1.3, easiness - 0.2)
        
    next_day = (datetime.now() + timedelta(days=new_interval)).strftime('%Y-%m-%d')
    c.execute("UPDATE vocab SET interval=?, easiness=?, next_review=?, mastery_score=? WHERE id=?", 
              (new_interval, new_easiness, next_day, new_mastery, int(word_id)))
    conn.commit()
    conn.close()

# --- STREAMING_CHUNK:Styling the Modern Dark UI... ---
st.set_page_config(page_title="Typist Lexicon Pro", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0B0E14; color: white; }
    .vocab-card {
        background: linear-gradient(145deg, #1A1F2B, #12161F);
        padding: 40px; border-radius: 25px; text-align: center;
        border: 1px solid rgba(255,255,255,0.05); margin-bottom: 20px;
    }
    .word-main { font-size: 5rem; font-weight: 800; background: linear-gradient(to right, #60A5FA, #A855F7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .example-box { background: rgba(0,0,0,0.3); padding: 20px; border-radius: 15px; color: #94A3B8; font-style: italic; text-align: left; border-left: 4px solid #A855F7; }
    .stTextInput input { background-color: #1A1F2B !important; color: white !important; font-size: 2rem !important; text-align: center !important; height: 70px !important; border-radius: 15px !important; border: 2px solid #2D3748 !important; }
    </style>
    <script>
    setInterval(function() {
        var inputs = window.parent.document.querySelectorAll('input');
        for (var i = 0; i < inputs.length; i++) {
            inputs[i].setAttribute('autocomplete', 'off');
        }
    }, 1000);
    </script>
""", unsafe_allow_html=True)

# --- STREAMING_CHUNK:Main Application Logic... ---
def main():
    init_db()
    st.title("⌨️ Typist Lexicon Pro")

    if st.session_state.quiz_phase:
        # --- QUIZ PHASE UI ---
        current_word_data = st.session_state.session_queue[st.session_state.quiz_index]
        
        st.markdown(f"""
            <div style="text-align:center; padding:20px; background:rgba(96, 165, 250, 0.1); border-radius:20px; border:1px dashed #60A5FA;">
                <h2 style="color:#60A5FA;">Final Challenge: Meaning</h2>
                <p>Select the correct translation for:</p>
                <h1 style="font-size:4rem;">{current_word_data['word']}</h1>
            </div>
        """, unsafe_allow_html=True)
        
        if not st.session_state.current_options:
            opts = get_distractors(current_word_data['translation'])
            opts.append(current_word_data['translation'])
            random.shuffle(opts)
            st.session_state.current_options = opts
            
        st.write("")
        cols = st.columns(2)
        for i, opt in enumerate(st.session_state.current_options):
            with cols[i % 2]:
                if st.button(opt, key=f"opt_{i}", use_container_width=True):
                    if opt == current_word_data['translation']:
                        st.session_state.quiz_index += 1
                        st.session_state.current_options = [] # Reset options for next word
                        if st.session_state.quiz_index >= len(st.session_state.session_queue):
                            # FINISHED SESSION
                            st.balloons()
                            for w in st.session_state.session_queue: update_srs(w['id'], True)
                            st.success("🎉 Session Mastered! Muscle memory and cognition synced.")
                            st.session_state.quiz_phase = False
                            st.session_state.session_queue = []
                            st.session_state.quiz_index = 0
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.rerun()
                    else:
                        st.error("Wrong! Back to training for this word.")
                        update_srs(current_word_data['id'], False)
                        st.session_state.quiz_phase = False
                        st.session_state.session_queue = []
                        st.session_state.quiz_index = 0
                        time.sleep(1)
                        st.rerun()
    else:
        # --- PRACTICE TABS ---
        tabs = st.tabs(["🚀 Practice", "📊 Stats", "📂 Vault"])
        
        with tabs[0]:
            conn = sqlite3.connect(DB_NAME)
            today = datetime.now().strftime('%Y-%m-%d')
            # ดึงคำที่ถึงกำหนด (Due) และไม่อยู่ในคิวที่พิมพ์ไปแล้ว
            finished_ids = [str(w['id']) for w in st.session_state.session_queue]
            query = f"SELECT * FROM vocab WHERE next_review <= ?"
            if finished_ids:
                query += f" AND id NOT IN ({','.join(finished_ids)})"
            query += " ORDER BY mastery_score ASC LIMIT 1"
            
            df_target = pd.read_sql_query(query, conn, params=(today,))
            conn.close()

            if not df_target.empty:
                target = df_target.iloc[0]
                st.markdown(f"""
                    <div class="vocab-card">
                        <div style="color:#94A3B8;">{target['level']} | {target['pos']}</div>
                        <div class="word-main">{target['word']}</div>
                        <div style="font-size:1.5rem; color:#E2E8F0; margin-bottom:20px;">{target['translation']}</div>
                        <div class="example-box"><strong>Example:</strong> {target['example']}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Dynamic Key เพื่อ Clear ช่องพิมพ์
                input_key = f"input_{target['id']}_{len(st.session_state.session_queue)}"
                typed_word = st.text_input("Type correctly to advance:", key=input_key).strip()

                if typed_word:
                    if typed_word.lower() == target['word'].lower():
                        st.session_state.session_queue.append(target.to_dict())
                        st.toast(f"Matched: {target['word']} ✅")
                        # ถ้าพิมพ์ครบ 3 คำ หรือคำศัพท์หมดคิว -> ไป Quiz
                        if len(st.session_state.session_queue) >= 3:
                            st.session_state.quiz_phase = True
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        if len(typed_word) >= len(target['word']):
                            st.error("Typos detected! Muscle memory failed.")
            else:
                if st.session_state.session_queue:
                    # ถ้ามีคำค้างในคิวแต่ไม่มีคำใหม่แล้ว ให้ไปควิซเลย
                    st.session_state.quiz_phase = True
                    st.rerun()
                else:
                    st.info("No words due for today. Add more in 'Vault' or enjoy your day!")

        with tabs[1]:
            st.header("Learning Insights")
            conn = sqlite3.connect(DB_NAME)
            df_all = pd.read_sql_query("SELECT * FROM vocab", conn)
            conn.close()
            st.dataframe(df_all[['word', 'pos', 'level', 'translation', 'mastery_score', 'next_review']], use_container_width=True)

        with tabs[2]:
            st.header("Word Vault")
            with st.form("add_word"):
                c1, c2 = st.columns(2)
                w = c1.text_input("New Word")
                p = c2.selectbox("POS", ["n.", "v.", "adj.", "adv."])
                t = st.text_input("Thai Translation")
                e = st.text_area("Example Sentence")
                l = st.select_slider("CEFR Level", ["A1", "A2", "B1", "B2", "C1", "C2"])
                if st.form_submit_button("Save Word"):
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    try:
                        c.execute("INSERT INTO vocab (word, pos, translation, example, level, next_review) VALUES (?,?,?,?,?,?)",
                                  (w, p, t, e, l, datetime.now().strftime('%Y-%m-%d')))
                        conn.commit()
                        st.success(f"'{w}' is now in your database!")
                    except: st.error("Word already exists!")
                    conn.close()

if __name__ == "__main__":
    main()
