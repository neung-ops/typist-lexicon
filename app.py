import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import time
import random
import plotly.express as px

# --- 1. CONFIGURATION & DATABASE ---
DB_NAME = "lexicon_pro.db"
TARGET_BATCH_SIZE = 3  # จำนวนคำที่ต้องพิมพ์ก่อนเข้า Quiz

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # สร้างตารางหลัก
    c.execute('''CREATE TABLE IF NOT EXISTS vocab 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  word TEXT UNIQUE, pos TEXT, pronunciation TEXT, translation TEXT, 
                  example TEXT, level TEXT, interval INTEGER DEFAULT 0, 
                  easiness REAL DEFAULT 2.5, next_review TEXT, mastery_score INTEGER DEFAULT 0)''')
    
    # ตรวจสอบและเพิ่มคอลัมน์ที่อาจขาดหายจากการอัปเดตเวอร์ชัน
    c.execute("PRAGMA table_info(vocab)")
    existing_cols = [col[1] for col in c.fetchall()]
    for col_name, col_type in [('pronunciation', 'TEXT'), ('mastery_score', 'INTEGER DEFAULT 0')]:
        if col_name not in existing_cols:
            c.execute(f"ALTER TABLE vocab ADD COLUMN {col_name} {col_type}")
    
    # เติมคำศัพท์เริ่มต้น (ถ้าว่างเปล่า)
    c.execute("SELECT COUNT(*) FROM vocab")
    if c.fetchone()[0] == 0:
        starter_words = [
            ('Analyze', 'v.', '/ˈæn.əl.aɪz/', 'วิเคราะห์', 'We need to analyze the data.', 'B1'),
            ('Implement', 'v.', '/ˈimpliˌment/', 'นำมาใช้/ทำให้เกิดผล', 'The plan was difficult to implement.', 'B2'),
            ('Ambiguous', 'adj.', '/æmˈbɪɡ.ju.əs/', 'กำกวม', 'His reply was ambiguous.', 'C1'),
            ('Pragmatic', 'adj.', '/præɡˈmæt.ɪk/', 'เน้นผลจริง/เชิงปฏิบัติ', 'A pragmatic approach to politics.', 'C1'),
            ('Scrutinize', 'v.', '/ˈskruː.tɪ.naɪz/', 'พินิจพิจารณาอย่างถี่ถ้วน', 'Customers were warned to scrutinize the small print.', 'C1'),
            ('Inherent', 'adj.', '/ɪnˈher.ənt/', 'ที่มีอยู่เป็นปกติวิสัย/โดยเนื้อแท้', 'There are risks inherent in almost every sport.', 'B2'),
            ('Substantial', 'adj.', '/səbˈstæn.ʃəl/', 'มากมาย/สำคัญ', 'A substantial change in government policy.', 'B2'),
            ('Mitigate', 'v.', '/ˈmɪt.ɪ.ɡeɪt/', 'บรรเทา/ทำให้เบาบางลง', 'It is unclear how to mitigate the effects of tourism.', 'C1')
        ]
        for w, p, pr, t, e, l in starter_words:
            c.execute("INSERT OR IGNORE INTO vocab (word, pos, pronunciation, translation, example, level, next_review) VALUES (?,?,?,?,?,?,?)",
                      (w, p, pr, t, e, l, datetime.now().strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()

# --- 2. LOGIC FUNCTIONS ---
def update_srs(word_id, success):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT interval, easiness, mastery_score FROM vocab WHERE id = ?", (int(word_id),))
    res = c.fetchone()
    if not res: return
    interval, easiness, mastery = res
    
    if success:
        if interval == 0: interval = 1
        elif interval == 1: interval = 3
        else: interval = int(interval * easiness)
        easiness = min(3.0, easiness + 0.1)
        mastery = min(100, mastery + 20)
    else:
        interval = 0
        easiness = max(1.3, easiness - 0.2)
        mastery = max(0, mastery - 15)
        
    next_review = (datetime.now() + timedelta(days=interval)).strftime('%Y-%m-%d')
    c.execute("UPDATE vocab SET interval=?, easiness=?, next_review=?, mastery_score=? WHERE id=?", 
              (interval, easiness, next_review, mastery, word_id))
    conn.commit()
    conn.close()

# --- 3. UI SETUP ---
st.set_page_config(page_title="Typist Lexicon Pro", layout="wide")

# JavaScript สำหรับบังคับ Focus (Aggressive Focus)
st.markdown("""
    <script>
    function forceFocus() {
        const inputs = window.parent.document.querySelectorAll('input');
        for (let input of inputs) {
            // ค้นหาเฉพาะ input ที่มี aria-label ของการพิมพ์
            if (input.getAttribute('aria-label') && input.getAttribute('aria-label').includes('Type correctly:')) {
                input.setAttribute('autocomplete', 'off');
                if (window.parent.document.activeElement !== input) {
                    input.focus();
                }
            }
        }
    }
    // รันทุก 500ms เพื่อป้องกันการหลุด Focus
    setInterval(forceFocus, 500);
    </script>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    .stApp { background-color: #0F172A; color: #F1F5F9; }
    .vocab-card { background: #1E293B; border-radius: 20px; padding: 40px; border: 1px solid #334155; text-align: center; }
    .word-title { font-size: 4.5rem; font-weight: 800; color: #38BDF8; margin-bottom: 0px; }
    .phonetic { color: #94A3B8; font-family: monospace; font-size: 1.2rem; }
    .translation { font-size: 2rem; color: #F1F5F9; margin: 15px 0; }
    .example { background: #0F172A; padding: 15px; border-radius: 10px; border-left: 4px solid #38BDF8; text-align: left; color: #CBD5E1; }
    .quiz-option { margin: 10px 0; }
    </style>
""", unsafe_allow_html=True)

# --- 4. APP STATE ---
if 'session_words' not in st.session_state: st.session_state.session_words = []
if 'current_word_idx' not in st.session_state: st.session_state.current_word_idx = 0
if 'phase' not in st.session_state: st.session_state.phase = "typing" # typing | quiz
if 'quiz_idx' not in st.session_state: st.session_state.quiz_idx = 0

def start_session(words):
    st.session_state.session_words = words
    st.session_state.current_word_idx = 0
    st.session_state.phase = "typing"
    st.session_state.quiz_idx = 0

# --- 5. MAIN RENDER ---
init_db()

tabs = st.tabs(["🎯 Practice", "📊 Analytics", "🛡️ Vault"])

with tabs[0]:
    conn = sqlite3.connect(DB_NAME)
    today = datetime.now().strftime('%Y-%m-%d')
    df_due = pd.read_sql_query("SELECT * FROM vocab WHERE next_review <= ?", conn, params=(today,))
    
    if st.session_state.session_words == [] and not df_due.empty:
        start_session(df_due.head(TARGET_BATCH_SIZE).to_dict('records'))
    
    if st.session_state.session_words:
        # --- TYPING PHASE ---
        if st.session_state.phase == "typing":
            current_word = st.session_state.session_words[st.session_state.current_word_idx]
            
            st.markdown(f"""
                <div class="vocab-card">
                    <p class="phonetic">Level {current_word['level']} | {current_word['pos']} | {current_word['pronunciation']}</p>
                    <h1 class="word-title">{current_word['word']}</h1>
                    <p class="translation">{current_word['translation']}</p>
                    <div class="example"><strong>Example:</strong><br>{current_word['example']}</div>
                </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            # ใช้ Key ที่ผูกกับ word id เพื่อให้ช่องว่างเมื่อเปลี่ยนคำ
            t_input = st.text_input(f"Type correctly: ({st.session_state.current_word_idx + 1}/{len(st.session_state.session_words)})", 
                                    key=f"type_{current_word['id']}")
            
            if t_input:
                if t_input.strip().lower() == current_word['word'].lower():
                    st.session_state.current_word_idx += 1
                    if st.session_state.current_word_idx >= len(st.session_state.session_words):
                        st.session_state.phase = "quiz"
                    st.rerun()
                elif len(t_input) >= len(current_word['word']):
                    st.error("Typo detected! Try again.")

        # --- QUIZ PHASE ---
        elif st.session_state.phase == "quiz":
            quiz_word = st.session_state.session_words[st.session_state.quiz_idx]
            st.subheader(f"⚡ Final Challenge: What does '{quiz_word['word']}' mean?")
            
            # ดึงคำแปลอื่นๆ มาเป็นตัวหลอก (ตัวแก้ปัญหา "สุ่ม 2")
            c = conn.cursor()
            c.execute("SELECT translation FROM vocab WHERE word != ?", (quiz_word['word'],))
            all_others = [r[0] for r in c.fetchall()]
            distractors = random.sample(all_others, min(3, len(all_others))) if all_others else ["สุ่ม 1", "สุ่ม 2", "สุ่ม 3"]
            options = distractors + [quiz_word['translation']]
            random.shuffle(options)
            
            cols = st.columns(2)
            for i, opt in enumerate(options):
                if cols[i%2].button(opt, key=f"opt_{i}_{quiz_word['id']}", use_container_width=True):
                    if opt == quiz_word['translation']:
                        update_srs(quiz_word['id'], True)
                        st.session_state.quiz_idx += 1
                        if st.session_state.quiz_idx >= len(st.session_state.session_words):
                            st.balloons()
                            st.session_state.session_words = []
                            st.success("Session Complete! Mastery Increased.")
                            time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Incorrect! This batch will repeat soon.")
                        update_srs(quiz_word['id'], False)
                        time.sleep(1)
                        st.session_state.phase = "typing"
                        st.session_state.current_word_idx = 0
                        st.session_state.quiz_idx = 0
                        st.rerun()
    else:
        st.success("🎉 All caught up for today!")
        if st.button("Unlock 5 New Advanced Words"):
            # ตัวอย่างคลังศัพท์เพิ่มเติม
            advanced = [
                ('Pragmatic', 'adj.', '/præɡˈmæt.ɪk/', 'เน้นผลจริง/เชิงปฏิบัติ', 'A pragmatic approach to politics.', 'C1'),
                ('Scrutinize', 'v.', '/ˈskruː.tɪ.naɪz/', 'พินิจพิจารณาอย่างถี่ถ้วน', 'Customers were warned to scrutinize the small print.', 'C1'),
                ('Inherent', 'adj.', '/ɪnˈher.ənt/', 'ที่มีอยู่เป็นปกติวิสัย/โดยเนื้อแท้', 'There are risks inherent in almost every sport.', 'B2'),
                ('Substantial', 'adj.', '/səbˈstæn.ʃəl/', 'มากมาย/สำคัญ', 'A substantial change in government policy.', 'B2'),
                ('Mitigate', 'v.', '/ˈmɪt.ɪ.ɡeɪt/', 'บรรเทา/ทำให้เบาบางลง', 'It is unclear how to mitigate the effects of tourism.', 'C1')
            ]
            c = conn.cursor()
            for w in advanced:
                c.execute("INSERT OR IGNORE INTO vocab (word, pos, pronunciation, translation, example, level, next_review) VALUES (?,?,?,?,?,?,?)",
                          (w[0], w[1], w[2], w[3], w[4], w[5], today))
            conn.commit()
            st.rerun()
    conn.close()

with tabs[1]:
    st.subheader("📊 Performance Analytics")
    conn = sqlite3.connect(DB_NAME)
    df_v = pd.read_sql_query("SELECT * FROM vocab", conn)
    conn.close()
    
    if not df_v.empty:
        df_v['mastery_score'] = df_v['mastery_score'].fillna(0)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Vocabulary", f"{len(df_v)} words")
        c2.metric("Knowledge Level", f"{int(df_v['mastery_score'].mean())}%")
        c3.metric("Due Today", len(df_due))
        
        fig = px.histogram(df_v, x="mastery_score", nbins=10, title="Mastery Distribution",
                           color_discrete_sequence=['#38BDF8'])
        st.plotly_chart(fig, use_container_width=True)
        
        st.write("### Knowledge Retention Status")
        st.dataframe(df_v[['word', 'translation', 'mastery_score', 'next_review']].sort_values('mastery_score', ascending=False), use_container_width=True)
    else:
        st.info("Start training to see your stats!")

with tabs[2]:
    st.subheader("🛡️ Vocabulary Vault")
    with st.expander("➕ Add New Word Manually"):
        with st.form("manual_add", clear_on_submit=True):
            f_word = st.text_input("Word")
            f_pos = st.text_input("POS (e.g. v., adj.)")
            f_pron = st.text_input("Pronunciation")
            f_trans = st.text_input("Thai Translation")
            f_ex = st.text_area("Example Sentence")
            f_lv = st.selectbox("Level", ["A1", "A2", "B1", "B2", "C1", "C2"], index=3)
            if st.form_submit_button("Save"):
                if f_word and f_trans:
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("INSERT OR IGNORE INTO vocab (word, pos, pronunciation, translation, example, level, next_review) VALUES (?,?,?,?,?,?,?)",
                              (f_word, f_pos, f_pron, f_trans, f_ex, f_lv, datetime.now().strftime('%Y-%m-%d')))
                    conn.commit()
                    conn.close()
                    st.success("Added!")
                    st.rerun()

    conn = sqlite3.connect(DB_NAME)
    df_all = pd.read_sql_query("SELECT id, word, pos, translation, level, next_review FROM vocab", conn)
    conn.close()
    st.dataframe(df_all, use_container_width=True)
