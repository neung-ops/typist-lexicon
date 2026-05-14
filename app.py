import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import time
import random
import plotly.express as px

# --- STREAMING_CHUNK:Configuring Database with Oxford Starter Kit... ---
DB_NAME = "vocab_pro_v5.db"

if 'session_queue' not in st.session_state:
    st.session_state.session_queue = [] 
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
                  word TEXT UNIQUE, pos TEXT, pronunciation TEXT, translation TEXT, 
                  example TEXT, level TEXT, interval INTEGER DEFAULT 0, 
                  easiness REAL DEFAULT 2.5, next_review TEXT, mastery_score INTEGER DEFAULT 0)''')
    
    c.execute("SELECT COUNT(*) FROM vocab")
    if c.fetchone()[0] < 5:
        now = datetime.now().strftime('%Y-%m-%d')
        # ชุดคำศัพท์เริ่มต้น (Starter Kit) ระดับ B1-C1
        starters = [
            ('Analyze', 'v.', '/ˈæn.əl.aɪz/', 'วิเคราะห์', 'We need to analyze the data carefully.', 'B1', 0, 2.5, now),
            ('Comprehensive', 'adj.', '/ˌkɒm.prɪˈhen.sɪv/', 'ครอบคลุม', 'A comprehensive list of words.', 'C1', 0, 2.5, now),
            ('Implement', 'v.', '/ˈɪm.plɪ.ment/', 'นำมาใช้', 'Let\'s implement the new plan.', 'B2', 0, 2.5, now),
            ('Consistent', 'adj.', '/kənˈsɪs.tənt/', 'สม่ำเสมอ', 'Her work is very consistent.', 'B2', 0, 2.5, now),
            ('Acquire', 'v.', '/əˈkwaɪər/', 'ได้รับมา', 'He managed to acquire new skills.', 'B2', 0, 2.5, now),
            ('Elaborate', 'adj.', '/iˈlæb.ər.ət/', 'ซับซ้อน/ละเอียด', 'They made elaborate preparations.', 'C1', 0, 2.5, now),
            ('Sufficient', 'adj.', '/səˈfɪʃ.ənt/', 'เพียงพอ', 'We have sufficient resources.', 'B1', 0, 2.5, now),
            ('Substantial', 'adj.', '/səbˈstæn.ʃəl/', 'มากมาย/สำคัญ', 'A substantial amount of money.', 'B2', 0, 2.5, now),
            ('Advocate', 'v.', '/ˈæd.və.keɪt/', 'สนับสนุน', 'She advocates for human rights.', 'C1', 0, 2.5, now),
            ('Constraint', 'n.', '/kənˈstreɪnt/', 'ข้อจำกัด', 'Financial constraints limited the project.', 'C1', 0, 2.5, now)
        ]
        c.executemany("INSERT OR IGNORE INTO vocab (word, pos, pronunciation, translation, example, level, interval, easiness, next_review) VALUES (?,?,?,?,?,?,?,?,?)", starters)
    conn.commit()
    conn.close()

# --- STREAMING_CHUNK:Defining Smart Distractors and SRS Logic... ---
def get_distractors(correct_answer):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT translation FROM vocab WHERE translation != ? ORDER BY RANDOM() LIMIT 3", (correct_answer,))
    others = [row[0] for row in c.fetchall()]
    conn.close()
    # ถ้าคำศัพท์ไม่พอ ให้ใช้คำหลอกแบบสุ่มที่เป็นคำทั่วไป
    fallbacks = ["ความพยายาม", "การเรียนรู้", "ความท้าทาย", "ความสำเร็จ", "การพัฒนา"]
    while len(others) < 3:
        f = random.choice(fallbacks)
        if f not in others: others.append(f)
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

# --- STREAMING_CHUNK:Injecting High-Performance Focus & Anti-Cheat Script... ---
st.set_page_config(page_title="Typist Lexicon Pro", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0B1117; color: white; }
    
    .vocab-card {
        background: linear-gradient(145deg, #1A1F2B, #12161F);
        padding: 40px; border-radius: 25px; text-align: center;
        border: 1px solid rgba(255,255,255,0.05); margin-bottom: 20px;
    }
    .word-main { font-size: 5rem; font-weight: 800; background: linear-gradient(to right, #60A5FA, #A855F7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0px; }
    .pronunciation { font-size: 1.5rem; color: #94A3B8; margin-bottom: 10px; font-family: serif; }
    .example-box { background: rgba(0,0,0,0.4); padding: 20px; border-radius: 15px; color: #CBD5E1; font-style: italic; text-align: left; border-left: 4px solid #A855F7; }
    
    .stTextInput input { 
        background-color: #0F172A !important; 
        color: #F8FAFC !important; 
        font-size: 2.5rem !important; 
        text-align: center !important; 
        height: 90px !important; 
        border-radius: 20px !important; 
        border: 2px solid #3B82F6 !important;
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.2);
    }
    
    /* Quiz Button Styling */
    div.stButton > button {
        background: #1E293B !important;
        color: #F8FAFC !important;
        border: 1px solid #334155 !important;
        padding: 25px !important;
        font-size: 1.4rem !important;
        width: 100%;
        border-radius: 15px;
        transition: all 0.2s ease;
        margin-top: 10px;
    }
    div.stButton > button:hover {
        background: #334155 !important;
        border-color: #60A5FA !important;
        transform: translateY(-2px);
    }
    </style>

    <script>
    function forceFocus() {
        // หา Input ทั้งหมดและเลือกตัวล่าสุดที่โผล่มา
        const inputs = window.parent.document.querySelectorAll('input');
        if (inputs.length > 0) {
            const currentInput = inputs[inputs.length - 1];
            currentInput.setAttribute('autocomplete', 'off');
            currentInput.setAttribute('autofocus', 'true');
            if (window.parent.document.activeElement !== currentInput) {
                currentInput.focus();
            }
        }
    }
    // สั่งรันทุกครึ่งวินาทีเพื่อให้แน่ใจว่าโฟกัสไม่หลุด
    setInterval(forceFocus, 500);
    </script>
""", unsafe_allow_html=True)

# --- STREAMING_CHUNK:App Main Logic (Typing -> Quiz)... ---
def main():
    init_db()
    st.title("⌨️ Typist Lexicon Pro v5")

    if st.session_state.quiz_phase:
        # --- PHASE 2: QUIZ ---
        current_word_data = st.session_state.session_queue[st.session_state.quiz_index]
        
        st.markdown(f"""
            <div style="text-align:center; padding:40px; background:rgba(168, 85, 247, 0.05); border-radius:30px; border:1px solid #A855F7;">
                <h2 style="color:#A855F7; text-transform:uppercase; letter-spacing:3px;">Final Checkpoint</h2>
                <h1 style="font-size:5rem; margin:10px 0; color:white;">{current_word_data['word']}</h1>
                <div class="pronunciation">{current_word_data['pronunciation']}</div>
                <p style="color:#94A3B8; font-size:1.2rem;">What is the correct Thai meaning?</p>
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
                if st.button(f"{opt}", key=f"quiz_opt_{i}"):
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
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.rerun()
                    else:
                        st.error("Wrong Meaning! Retrying the session...")
                        update_srs(current_word_data['id'], False)
                        st.session_state.quiz_phase = False
                        st.session_state.session_queue = []
                        st.session_state.quiz_index = 0
                        time.sleep(1.5)
                        st.rerun()
    else:
        # --- PHASE 1: TYPING ---
        tabs = st.tabs(["🚀 Training Ground", "📊 Analytics", "📂 Word Vault"])
        
        with tabs[0]:
            conn = sqlite3.connect(DB_NAME)
            today = datetime.now().strftime('%Y-%m-%d')
            finished_ids = [str(w['id']) for w in st.session_state.session_queue]
            
            # ดึงคำที่ถึงกำหนด (SRS)
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
                        <div class="pronunciation">{target['pronunciation']}</div>
                        <div style="font-size:1.8rem; color:#E2E8F0; margin-bottom:15px; border-bottom:1px solid #334155; padding-bottom:10px;">{target['translation']}</div>
                        <div class="example-box"><strong>Example:</strong> {target['example']}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Dynamic key to reset input and JavaScript will handle focus
                input_key = f"type_box_{target['id']}_{st.session_state.input_focus_trigger}"
                typed_word = st.text_input("Type the word correctly:", key=input_key, placeholder="Type and hit Enter...").strip()

                if typed_word:
                    if typed_word.lower() == target['word'].lower():
                        st.session_state.session_queue.append(target.to_dict())
                        st.session_state.input_focus_trigger += 1 
                        st.toast(f"✅ Correct: {target['word']}")
                        if len(st.session_state.session_queue) >= 3:
                            st.session_state.quiz_phase = True
                        time.sleep(0.3)
                        st.rerun()
                    else:
                        if len(typed_word) >= len(target['word']):
                            st.error("Typos detected! Focus on each letter.")
            else:
                # กรณีคำในคิวหมด
                if st.session_state.session_queue:
                    st.session_state.quiz_phase = True
                    st.rerun()
                else:
                    st.success("🎯 All daily tasks completed!")
                    if st.button("🔥 Start Infinite Review Mode"):
                        # สุ่มคำจาก DB ทั้งหมดมาฝึกใหม่
                        conn = sqlite3.connect(DB_NAME)
                        c = conn.cursor()
                        c.execute("UPDATE vocab SET next_review = ?", (datetime.now().strftime('%Y-%m-%d'),))
                        conn.commit()
                        conn.close()
                        st.rerun()

        with tabs[1]:
            # --- ANALYTICS TAB ---
            st.header("Learning Performance")
            conn = sqlite3.connect(DB_NAME)
            df_stats = pd.read_sql_query("SELECT level, mastery_score, word FROM vocab", conn)
            conn.close()
            
            if not df_stats.empty:
                c1, c2 = st.columns([1, 2])
                with c1:
                    fig_pie = px.pie(df_stats, names='level', title='Vocab Distribution', hole=0.4, color_discrete_sequence=px.colors.sequential.Agsunset)
                    st.plotly_chart(fig_pie, use_container_width=True)
                with c2:
                    st.subheader("Mastery Heatmap")
                    fig_bar = px.bar(df_stats, x='word', y='mastery_score', color='mastery_score', color_continuous_scale='Viridis')
                    st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("No data yet. Start training!")

        with tabs[2]:
            # --- WORD VAULT TAB ---
            st.header("Dictionary Management")
            with st.expander("➕ Add Custom Word to Vault"):
                with st.form("add_word", clear_on_submit=True):
                    c1, c2, c3 = st.columns(3)
                    w = c1.text_input("Word")
                    pos = c2.selectbox("POS", ["n.", "v.", "adj.", "adv.", "phr."])
                    phonetic = c3.text_input("IPA (e.g. /.../)")
                    t = st.text_input("Thai Translation")
                    e = st.text_area("Usage Example")
                    l = st.select_slider("CEFR", ["A1", "A2", "B1", "B2", "C1", "C2"], value="B1")
                    if st.form_submit_button("Save to Dictionary"):
                        if w and t:
                            conn = sqlite3.connect(DB_NAME)
                            c = conn.cursor()
                            try:
                                c.execute("INSERT INTO vocab (word, pos, pronunciation, translation, example, level, next_review) VALUES (?,?,?,?,?,?,?)",
                                          (w, pos, phonetic, t, e, l, datetime.now().strftime('%Y-%m-%d')))
                                conn.commit()
                                st.success(f"Added {w}!")
                                time.sleep(1)
                                st.rerun()
                            except: st.error("Word already exists in vault.")
                            conn.close()
            
            conn = sqlite3.connect(DB_NAME)
            df_v = pd.read_sql_query("SELECT id, word, pos, level, translation, mastery_score FROM vocab ORDER BY id DESC", conn)
            conn.close()
            st.dataframe(df_v, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
