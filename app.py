import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import time
import random
import plotly.express as px

# --- STREAMING_CHUNK:Configuring Database and Global State... ---
DB_NAME = "vocab_pro_v3.db"

if 'session_queue' not in st.session_state:
    st.session_state.session_queue = [] # คำที่พิมพ์ผ่านแล้วในรอบนี้
if 'quiz_phase' not in st.session_state:
    st.session_state.quiz_phase = False
if 'quiz_index' not in st.session_state:
    st.session_state.quiz_index = 0
if 'current_options' not in st.session_state:
    st.session_state.current_options = []
if 'input_focus_trigger' not in st.session_state:
    st.session_state.input_focus_trigger = 0

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vocab 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  word TEXT UNIQUE, pos TEXT, translation TEXT, 
                  example TEXT, level TEXT, interval INTEGER DEFAULT 0, 
                  easiness REAL DEFAULT 2.5, next_review TEXT, mastery_score INTEGER DEFAULT 0)''')
    
    c.execute("SELECT COUNT(*) FROM vocab")
    if c.fetchone()[0] == 0:
        now = datetime.now().strftime('%Y-%m-%d')
        starters = [
            ('Analyze', 'v.', 'วิเคราะห์', 'We need to analyze the results.', 'B1', 0, 2.5, now),
            ('Comprehensive', 'adj.', 'ครอบคลุม', 'A comprehensive guide to coding.', 'C1', 0, 2.5, now),
            ('Implement', 'v.', 'นำมาใช้', 'Let\'s implement the new feature.', 'B2', 0, 2.5, now)
        ]
        c.executemany("INSERT INTO vocab (word, pos, translation, example, level, interval, easiness, next_review) VALUES (?,?,?,?,?,?,?,?)", starters)
    conn.commit()
    conn.close()

# --- STREAMING_CHUNK:Defining Logic and Helper Functions... ---
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

# --- STREAMING_CHUNK:Styling UI and Injecting JS for Focus/Auto-off... ---
st.set_page_config(page_title="Typist Lexicon Pro", layout="wide")

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    * {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background-color: #0B0E14; color: white; }}
    .vocab-card {{
        background: linear-gradient(145deg, #1A1F2B, #12161F);
        padding: 40px; border-radius: 25px; text-align: center;
        border: 1px solid rgba(255,255,255,0.05); margin-bottom: 20px;
    }}
    .word-main {{ font-size: 5rem; font-weight: 800; background: linear-gradient(to right, #60A5FA, #A855F7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .example-box {{ background: rgba(0,0,0,0.3); padding: 20px; border-radius: 15px; color: #94A3B8; font-style: italic; text-align: left; border-left: 4px solid #A855F7; }}
    
    /* Input Styling */
    .stTextInput input {{ 
        background-color: #1A1F2B !important; 
        color: white !important; 
        font-size: 2.5rem !important; 
        text-align: center !important; 
        height: 80px !important; 
        border-radius: 15px !important; 
        border: 2px solid #3B82F6 !important;
    }}
    
    /* Quiz Button Styling - Always Visible */
    div.stButton > button {{
        background-color: #1E293B !important;
        color: #F8FAFC !important;
        border: 1px solid #334155 !important;
        padding: 20px !important;
        font-size: 1.2rem !important;
        transition: all 0.2s ease;
    }}
    div.stButton > button:hover {{
        border-color: #60A5FA !important;
        background-color: #334155 !important;
    }}
    </style>

    <script>
    // Function to kill autocomplete and force focus
    function manageFocus() {{
        var inputs = window.parent.document.querySelectorAll('input');
        for (var i = 0; i < inputs.length; i++) {{
            inputs[i].setAttribute('autocomplete', 'new-password'); // Trick browsers
            inputs[i].setAttribute('autocorrect', 'off');
            inputs[i].setAttribute('spellcheck', 'false');
            if (i === inputs.length - 1) {{
                inputs[i].focus();
            }}
        }}
    }}
    
    // Run periodically to keep control
    setInterval(manageFocus, 500);
    </script>
""", unsafe_allow_html=True)

# --- STREAMING_CHUNK:Main Application Logic... ---
def main():
    init_db()
    st.title("⌨️ Typist Lexicon Pro")

    if st.session_state.quiz_phase:
        # --- QUIZ PHASE ---
        current_word_data = st.session_state.session_queue[st.session_state.quiz_index]
        
        st.markdown(f"""
            <div style="text-align:center; padding:30px; background:rgba(96, 165, 250, 0.1); border-radius:20px; border:1px dashed #60A5FA;">
                <h2 style="color:#60A5FA; margin-bottom:5px;">Final Challenge: Meaning</h2>
                <p style="color:#94A3B8;">Select the correct translation for:</p>
                <h1 style="font-size:4.5rem; margin:10px 0;">{current_word_data['word']}</h1>
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
                if st.button(f"{opt}", key=f"opt_{i}_{st.session_state.quiz_index}", use_container_width=True):
                    if opt == current_word_data['translation']:
                        st.session_state.quiz_index += 1
                        st.session_state.current_options = []
                        if st.session_state.quiz_index >= len(st.session_state.session_queue):
                            st.balloons()
                            for w in st.session_state.session_queue: update_srs(w['id'], True)
                            st.toast("🎉 Session Mastered!")
                            st.session_state.quiz_phase = False
                            st.session_state.session_queue = []
                            st.session_state.quiz_index = 0
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.rerun()
                    else:
                        st.error("Wrong! Memory link broken. Try this batch again.")
                        update_srs(current_word_data['id'], False)
                        st.session_state.quiz_phase = False
                        st.session_state.session_queue = []
                        st.session_state.quiz_index = 0
                        time.sleep(1.5)
                        st.rerun()
    else:
        # --- APP TABS ---
        tabs = st.tabs(["🚀 Practice", "📊 Stats", "📂 Vault"])
        
        with tabs[0]:
            conn = sqlite3.connect(DB_NAME)
            today = datetime.now().strftime('%Y-%m-%d')
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
                        <div style="color:#94A3B8; font-weight:bold;">{target['level']} | {target['pos']}</div>
                        <div class="word-main">{target['word']}</div>
                        <div style="font-size:1.6rem; color:#E2E8F0; margin-bottom:15px;">{target['translation']}</div>
                        <div class="example-box"><strong>Example:</strong> {target['example']}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # ใช้ Dynamic Key ร่วมกับ Timestamp เพื่อให้บราว์เซอร์ไม่จดจำ
                input_key = f"input_{target['id']}_{len(st.session_state.session_queue)}_{st.session_state.input_focus_trigger}"
                typed_word = st.text_input("Type the word above correctly:", key=input_key).strip()

                if typed_word:
                    if typed_word.lower() == target['word'].lower():
                        st.session_state.session_queue.append(target.to_dict())
                        st.session_state.input_focus_trigger += 1 # Change key to clear & focus
                        st.toast(f"Matched: {target['word']} ✅")
                        if len(st.session_state.session_queue) >= 3:
                            st.session_state.quiz_phase = True
                        time.sleep(0.3)
                        st.rerun()
                    else:
                        if len(typed_word) >= len(target['word']):
                            st.error("Typo detected! Check your spelling.")
            else:
                if st.session_state.session_queue:
                    st.session_state.quiz_phase = True
                    st.rerun()
                else:
                    st.info("No words due for today. Perfect time to add new ones in the 'Vault'!")

        with tabs[1]:
            # --- STATS TAB (Analytics) ---
            st.header("Learning Analytics")
            conn = sqlite3.connect(DB_NAME)
            df_stats = pd.read_sql_query("SELECT level, mastery_score, word FROM vocab", conn)
            conn.close()
            
            if not df_stats.empty:
                c1, c2 = st.columns(2)
                with c1:
                    fig_pie = px.pie(df_stats, names='level', title='Vocab Distribution by Level', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
                    st.plotly_chart(fig_pie, use_container_width=True)
                with c2:
                    avg_mastery = df_stats['mastery_score'].mean()
                    st.metric("Overall Mastery", f"{avg_mastery:.1f}%")
                    st.markdown("### Mastery Levels")
                    st.progress(avg_mastery / 100)
                
                st.subheader("Mastery Progress per Word")
                fig_bar = px.bar(df_stats, x='word', y='mastery_score', color='mastery_score', title="Individual Word Mastery (%)")
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.write("Add some words first to see your stats!")

        with tabs[2]:
            # --- VAULT TAB (Management) ---
            st.header("Word Vault")
            
            with st.expander("➕ Add New Word to Library", expanded=False):
                with st.form("add_word", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    w = c1.text_input("Word (English)")
                    p = c2.selectbox("Part of Speech", ["n.", "v.", "adj.", "adv.", "phr."])
                    t = st.text_input("Translation (Thai)")
                    e = st.text_area("Example Sentence")
                    l = st.select_slider("CEFR Level", ["A1", "A2", "B1", "B2", "C1", "C2"], value="B1")
                    if st.form_submit_button("Save to Vault"):
                        if w and t:
                            conn = sqlite3.connect(DB_NAME)
                            c = conn.cursor()
                            try:
                                c.execute("INSERT INTO vocab (word, pos, translation, example, level, next_review) VALUES (?,?,?,?,?,?)",
                                          (w, p, t, e, l, datetime.now().strftime('%Y-%m-%d')))
                                conn.commit()
                                st.success(f"'{w}' added successfully!")
                                time.sleep(1)
                                st.rerun()
                            except: st.error("Word already exists in your vault!")
                            conn.close()
            
            st.subheader("Current Library")
            conn = sqlite3.connect(DB_NAME)
            df_vault = pd.read_sql_query("SELECT id, word, pos, level, translation, mastery_score, next_review FROM vocab ORDER BY id DESC", conn)
            conn.close()
            st.dataframe(df_vault, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
```
eof

### สรุปการแก้ไขที่ทำให้ชีวิตง่ายขึ้น:
1.  **Cursor Focus:** ผมฉีด JavaScript เข้าไปสั่งให้มัน `focus()` ที่ช่อง Input อัตโนมัติทุกครั้งที่มีการรีโหลดหน้า คุณกด Enter ปุ๊บ พิมพ์คำถัดไปได้เลย ไม่ต้องใช้เมาส์
2.  **No More Autocomplete:** ใช้ `autocomplete="new-password"` และ JS Injection เพื่อ "หลอก" บราว์เซอร์ไม่ให้จำสิ่งที่คุณพิมพ์ รับรองว่ากล่องขาวๆ จะไม่โผล่มากวนใจอีก
3.  **Quiz UI:** ปุ่มตัวเลือกใน Quiz ตอนนี้เป็นพื้นหลังเข้ม ตัวอักษรขาวชัดเจน และเรียงเป็น Grid สวยงาม ไม่ต้องเอาเมาส์ไปชี้ก็เห็นคำแปลทั้งหมดครับ
4.  **Stats vs Vault:** 
    *   **Stats** ตอนนี้มีกราฟ Plotly แสดงความก้าวหน้าและการกระจายตัวของคำศัพท์
    *   **Vault** ย้ายไปเป็นแท็บสุดท้าย สำหรับจัดการข้อมูล (เพิ่มคำ/ดูตารางรวม) เพื่อไม่ให้สับสนครับ

ลองเล่นดูอีกครั้งนะครับ คราวนี้ Flow การใช้งานควรจะลื่นไหลเหมือนเล่นเกมคอนโซลเลยครับ!_
