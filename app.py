import streamlit as st
if 'session_queue' not in st.session_state:
    st.session_state.session_queue = []
if 'completed_typing' not in st.session_state:
    st.session_state.completed_typing = []
if 'quiz_phase' not in st.session_state:
    st.session_state.quiz_phase = False
if 'quiz_index' not in st.session_state:
    st.session_state.quiz_index = 0

def get_distractors(correct_answer, limit=3):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT translation FROM vocab WHERE translation != ? ORDER BY RANDOM() LIMIT ?", (correct_answer, limit))
    distractors = [row[0] for row in c.fetchall()]
    conn.close()
    # ถ้าคำใน DB ไม่พอ ให้ใส่ตัวหลอกกากๆ ไปก่อน
    while len(distractors) < limit:
        distractors.append("ตัวหลอกสุ่ม")
    return distractors

def main():
    init_db()
    st.title("⌨️ Typist Lexicon Pro")
    
    c.execute("PRAGMA table_info(vocab)")
    cols = [column[1] for column in c.fetchall()]
    if 'pos' not in cols: c.execute("ALTER TABLE vocab ADD COLUMN pos TEXT")
    if 'example' not in cols: c.execute("ALTER TABLE vocab ADD COLUMN example TEXT")

    c.execute("SELECT COUNT(*) FROM vocab")
    if c.fetchone()[0] == 0:
        initial_words = [
            ('Analyze', 'v.', 'วิเคราะห์', 'We need to analyze the results of the experiment.', 'B1', 0, 2.5, datetime.now().strftime('%Y-%m-%d')),
            ('Implement', 'v.', 'ทำให้เกิดผล, นำมาใช้', 'The company decided to implement a new policy.', 'B2', 0, 2.5, datetime.now().strftime('%Y-%m-%d')),
            ('Comprehensive', 'adj.', 'ครอบคลุม', 'This is a comprehensive study of the market.', 'C1', 0, 2.5, datetime.now().strftime('%Y-%m-%d')),
            ('Ambiguous', 'adj.', 'กวม, ไม่ชัดเจน', 'His reply to my question was somewhat ambiguous.', 'C1', 0, 2.5, datetime.now().strftime('%Y-%m-%d')),
            ('Facilitate', 'v.', 'อำนวยความสะดวก', 'The new software will facilitate faster data entry.', 'B2', 0, 2.5, datetime.now().strftime('%Y-%m-%d'))
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
        if interval == 0: new_interval = 1
        elif interval == 1: new_interval = 3
        else: new_interval = int(interval * easiness)
        new_easiness = easiness + 0.1
        new_mastery = min(100, mastery + 15)
    else:
        new_interval = 0 
        new_easiness = max(1.3, easiness - 0.2)
        new_mastery = max(0, mastery - 20)
        
    next_review = (datetime.now() + timedelta(days=new_interval)).strftime('%Y-%m-%d')
    c.execute("UPDATE vocab SET interval = ?, easiness = ?, next_review = ?, mastery_score = ? WHERE id = ?", 
              (new_interval, new_easiness, next_review, new_mastery, int(word_id)))
    conn.commit()
    conn.close()

# --- UI STYLING ---
st.set_page_config(page_title="Typist Lexicon Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0B0E14; }
    
    .vocab-card {
        background: linear-gradient(145deg, #1A1F2B, #12161F);
        padding: 50px;
        border-radius: 30px;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.05);
        box-shadow: 0 20px 40px rgba(0,0,0,0.4);
        margin-bottom: 30px;
    }
    
    .word-main {
        font-size: 5.5rem;
        font-weight: 800;
        letter-spacing: -2px;
        background: linear-gradient(to right, #60A5FA, #A855F7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    
    .pos-tag {
        display: inline-block;
        background: rgba(96, 165, 250, 0.1);
        color: #60A5FA;
        padding: 4px 15px;
        border-radius: 10px;
        font-weight: 600;
        margin-bottom: 15px;
        font-size: 0.9rem;
    }

    .level-tag { color: #94A3B8; font-size: 0.9rem; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }
    .trans-main { font-size: 1.8rem; color: #E2E8F0; margin-bottom: 30px; }
    
    .example-box {
        background: rgba(0,0,0,0.2);
        padding: 25px;
        border-radius: 20px;
        color: #94A3B8;
        font-style: italic;
        font-size: 1.2rem;
        border-left: 4px solid #A855F7;
        text-align: left;
        line-height: 1.6;
    }
    
    .stTextInput input {
        background-color: #1A1F2B !important;
        color: white !important;
        font-size: 2.5rem !important;
        height: 80px !important;
        text-align: center !important;
        border-radius: 20px !important;
        border: 2px solid #2D3748 !important;
        transition: all 0.3s;
    }
    
    .stTextInput input:focus {
        border-color: #60A5FA !important;
        box-shadow: 0 0 20px rgba(96, 165, 250, 0.2) !important;
    }
    </style>

    <script>
    setInterval(function() {
        var inputs = window.parent.document.querySelectorAll('input');
        for (var i = 0; i < inputs.length; i++) {
            inputs[i].setAttribute('autocomplete', 'off');
            inputs[i].setAttribute('autocorrect', 'off');
            inputs[i].setAttribute('spellcheck', 'false');
        }
    }, 1000);
    </script>
""", unsafe_allow_html=True)

def main():
    init_db()
    st.title("⌨️ Typist Lexicon Pro")
    tabs = st.tabs(["🚀 Practice", "📈 Progress", "📂 Vault"])
    
    with tabs[0]:
        if st.session_state.quiz_phase:
            # --- QUIZ PHASE UI ---
            current_quiz_word = st.session_state.completed_typing[st.session_state.quiz_index]
            
            st.markdown(f"""
                <div style="text-align:center; padding:30px; background:rgba(96, 165, 250, 0.05); border-radius:20px; border:1px dashed #60A5FA;">
                    <h2 style="color:#60A5FA; margin:0;">Final Challenge: Meanings</h2>
                    <p style="color:#94A3B8;">Select the correct Thai translation for:</p>
                    <h1 style="font-size:4rem; margin:10px 0;">{current_quiz_word['word']}</h1>
                </div>
            """, unsafe_allow_html=True)
            
            if 'current_options' not in st.session_state:
                opts = get_distractors(current_quiz_word['translation'])
                opts.append(current_quiz_word['translation'])
                import random
                random.shuffle(opts)
                st.session_state.current_options = opts
            
            cols = st.columns(2)
            for i, opt in enumerate(st.session_state.current_options):
                with cols[i % 2]:
                    if st.button(opt, use_container_width=True, key=f"opt_{i}"):
                        if opt == current_quiz_word['translation']:
                            st.toast("🎯 Correct!", icon="✅")
                            st.session_state.quiz_index += 1
                            if 'current_options' in st.session_state: del st.session_state.current_options
                            
                            if st.session_state.quiz_index >= len(st.session_state.completed_typing):
                                # จบเซสชั่นจริงๆ
                                st.balloons()
                                st.success("Session Complete! You've mastered these words.")
                                # อัปเดต SRS ทั้งหมดที่นี่
                                for w in st.session_state.completed_typing:
                                    update_srs(w['id'], True)
                                
                                # Reset Session
                                st.session_state.quiz_phase = False
                                st.session_state.completed_typing = []
                                st.session_state.quiz_index = 0
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.rerun()
                        else:
                            st.error("Wrong! This word will stay in your practice loop.")
                            update_srs(current_quiz_word['id'], False)
                            st.session_state.quiz_phase = False
                            st.session_state.completed_typing = []
                            st.session_state.quiz_index = 0
                            time.sleep(1)
                            st.rerun()

        else:
            # --- TYPING PHASE UI ---
            conn = sqlite3.connect(DB_NAME)
            today = datetime.now().strftime('%Y-%m-%d')
            df_due = pd.read_sql_query("SELECT * FROM vocab WHERE next_review <= ? OR interval = 0 ORDER BY interval DESC", conn, params=(today,))
            conn.close()

            if not df_due.empty:
                target = df_due.iloc[0]
                # ... existing Card UI ...
                
                input_key = f"q_{target['id']}_{time.time()}"
                user_input = st.text_input("Type correctly to advance", key=input_key)

                if user_input:
                    if user_input.strip().lower() == target['word'].lower():
                        st.session_state.completed_typing.append(target)
                        st.toast(f"Keyboard matched: {target['word']}")
                        
                        # กำหนดขนาดเซสชั่น เช่น พิมพ์ครบ 3 คำแล้วไปควิซ
                        if len(st.session_state.completed_typing) >= 3 or len(df_due) <= 1:
                            st.session_state.quiz_phase = True
                            st.session_state.quiz_index = 0
                        
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        if len(user_input) >= len(target['word']):
                            st.error("Typos detected!")
                            update_srs(target['id'], False)
            # ... existing empty state ...
