import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import time
import random

# --- STREAMING_CHUNK:Configuring Global Constants... ---
DB_NAME = "vocab_vault_v6.db"

# คลังคำศัพท์ Oxford/Advanced (B2-C1) สำหรับการขยายคลัง
OXFORD_EXPANSION = [
    ('Ambiguous', 'adj.', '/æmˈbɪɡ.ju.əs/', 'กำกวม/ไม่ชัดเจน', 'His reply to my question was somewhat ambiguous.', 'B2'),
    ('Coherent', 'adj.', '/koʊˈhɪr.ənt/', 'สอดคล้องกัน/เชื่อมโยงกัน', 'The government lacks a coherent economic policy.', 'B2'),
    ('Deteriorate', 'v.', '/dɪˈtɪr.i.ə.reɪt/', 'เสื่อมโทรมลง/แย่ลง', 'The weather conditions are expected to deteriorate.', 'C1'),
    ('Exacerbate', 'v.', '/ɪɡˈzæs.ɚ.beɪt/', 'ทำให้แย่ลง/ซ้ำเติม', 'This attack will exacerbate the already tense relations.', 'C1'),
    ('Fluctuate', 'v.', '/ˈflʌk.tʃu.eɪt/', 'ผันผวน/ขึ้นๆ ลงๆ', 'Vegetable prices fluctuate according to the season.', 'B2'),
    ('Hypothesis', 'n.', '/haɪˈpɑː.θə.sɪs/', 'สมมติฐาน', 'The results confirm the initial hypothesis.', 'B2'),
    ('Inevitable', 'adj.', '/ɪˈnev.ə.t̬ə.bəl/', 'หลีกเลี่ยงไม่ได้', 'The accident was the inevitable outcome of carelessness.', 'B2'),
    ('Justify', 'v.', '/ˈdʒʌs.tə.faɪ/', 'ให้เหตุผลรองรับ/พิสูจน์ว่าถูก', 'I can\'t justify taking another day off work.', 'B2'),
    ('Legitimate', 'adj.', '/ləˈdʒɪt̬.ə.mət/', 'ชอบธรรม/ถูกต้องตามกฎหมาย', 'He has a legitimate claim to the property.', 'B2'),
    ('Mitigate', 'v.', '/ˈmɪt̬.ə.ɡeɪt/', 'บรรเทาลง/ทำให้เบาลง', 'It is unclear how to mitigate the effects of tourism.', 'C1'),
    ('Paradigm', 'n.', '/ˈper.ə.daɪm/', 'แบบอย่าง/กรอบแนวคิด', 'The bus project is a new paradigm for public transport.', 'C1'),
    ('Resilient', 'adj.', '/rɪˈzɪl.jənt/', 'ยืดหยุ่น/คืนสภาพได้เร็ว', 'The community is highly resilient to economic change.', 'B2'),
    ('Scrutinize', 'v.', '/ˈskruː.t̬ən.aɪz/', 'พินิจพิจารณาอย่างละเอียด', 'Her performance was scrutinized by the judges.', 'C1'),
    ('Substantial', 'adj.', '/səbˈstæn.ʃəl/', 'มากมาย/สำคัญ', 'The findings show a substantial difference between groups.', 'B2'),
    ('Unprecedented', 'adj.', '/ʌnˈpres.ə.den.t̬ɪd/', 'ไม่เคยเกิดขึ้นมาก่อน', 'The scale of the disaster is unprecedented.', 'C1'),
    ('Pragmatic', 'adj.', '/præɡˈmæt̬.ɪk/', 'เน้นผลจริง/ในทางปฏิบัติ', 'We need a pragmatic approach to this problem.', 'C1'),
    ('Elaborate', 'v.', '/iˈlæb.ə.reɪt/', 'ขยายความ/ทำอย่างละเอียด', 'Could you elaborate on your main point?', 'B2'),
    ('Conspicuous', 'adj.', '/kənˈspɪk.ju.əs/', 'เด่นชัด/สะดุดตา', 'He was conspicuous by his absence.', 'C1'),
    ('Advocate', 'v.', '/ˈæd.və.keɪt/', 'สนับสนุน/เป็นกระบอกเสียง', 'She advocates for higher taxes on the wealthy.', 'B2'),
    ('Ambivalent', 'adj.', '/amˈbɪv.ə.lənt/', 'มีความรู้สึกสองจิตสองใจ', 'I am ambivalent about my new job.', 'C1')
]

# --- STREAMING_CHUNK:Initializing Session States... ---
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

# --- STREAMING_CHUNK:Handling Database Logic... ---
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
        starters = [
            ('Analyze', 'v.', '/ˈæn.əl.aɪz/', 'วิเคราะห์', 'We need to analyze the data carefully.', 'B1', 0, 2.5, now),
            ('Comprehensive', 'adj.', '/ˌkɒm.prɪˈhen.sɪv/', 'ครอบคลุม', 'A comprehensive list of words.', 'C1', 0, 2.5, now),
            ('Implement', 'v.', '/ˈɪm.plɪ.ment/', 'นำมาใช้', 'Let\'s implement the new plan.', 'B2', 0, 2.5, now),
            ('Consistent', 'adj.', '/kənˈsɪs.tənt/', 'สม่ำเสมอ', 'Her work is very consistent.', 'B2', 0, 2.5, now),
            ('Acquire', 'v.', '/əˈkwaɪər/', 'ได้รับมา', 'He managed to acquire new skills.', 'B2', 0, 2.5, now)
        ]
        c.executemany("INSERT OR IGNORE INTO vocab (word, pos, pronunciation, translation, example, level, interval, easiness, next_review) VALUES (?,?,?,?,?,?,?,?,?)", starters)
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

def get_distractors(correct_answer):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT translation FROM vocab WHERE translation != ? ORDER BY RANDOM() LIMIT 3", (correct_answer,))
    others = [row[0] for row in c.fetchall()]
    conn.close()
    fallbacks = ["ความพยายาม", "การเรียนรู้", "ความท้าทาย", "ความสำเร็จ", "การพัฒนา"]
    while len(others) < 3:
        f = random.choice(fallbacks)
        if f not in others: others.append(f)
    return others

# --- STREAMING_CHUNK:Injecting High-Performance Focus & Modern Styles... ---
st.set_page_config(page_title="Typist Lexicon Pro v6", layout="wide")

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
    }
    div.stButton > button:hover {
        background: #3B82F6 !important;
        border-color: #60A5FA !important;
        transform: translateY(-2px);
    }
    </style>

    <script>
    function forceFocus() {
        // ค้นหา input ล่าสุดในหน้าเว็บ (Streamlit มักจะเอา input ไว้ท้ายๆ)
        const inputs = window.parent.document.querySelectorAll('input');
        if (inputs.length > 0) {
            const currentInput = inputs[inputs.length - 1];
            // ปิด autocomplete บราวเซอร์
            currentInput.setAttribute('autocomplete', 'off');
            // ถ้า focus หลุด ให้ดึงกลับมา
            if (window.parent.document.activeElement !== currentInput) {
                currentInput.focus();
            }
        }
    }
    // สั่งให้ทำงานทุก 500ms (0.5 วินาที)
    setInterval(forceFocus, 500);
    </script>
""", unsafe_allow_html=True)

# --- STREAMING_CHUNK:App Main Logic (Typing -> Quiz)... ---
def main():
    init_db()
    st.title("⌨️ Typist Lexicon Pro v6")

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
                            # บันทึกคะแนนลง DB จริงๆ เมื่อจบเซสชั่น
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
                        st.error("Wrong Meaning! Retrying...")
                        update_srs(current_word_data['id'], False) # พลาดในควิซก็นับว่าพลาด
                        st.session_state.quiz_phase = False
                        st.session_state.session_queue = []
                        st.session_state.quiz_index = 0
                        time.sleep(1.5)
                        st.rerun()
    else:
        # --- PHASE 1: TRAINING ---
        tabs = st.tabs(["🚀 Training Ground", "📊 Analytics", "📂 Word Vault"])
        
        with tabs[0]:
            conn = sqlite3.connect(DB_NAME)
            today = datetime.now().strftime('%Y-%m-%d')
            # ดึงคำที่ต้องทบทวนแต่ไม่อยู่ในคิวที่พิมพ์เสร็จแล้ว
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
                        <div class="pronunciation">{target['pronunciation']}</div>
                        <div style="font-size:1.8rem; color:#E2E8F0; margin-bottom:15px; border-bottom:1px solid #334155; padding-bottom:10px;">{target['translation']}</div>
                        <div class="example-box"><strong>Example:</strong> {target['example']}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # ใช้ trigger เพื่อเปลี่ยน key ให้ช่องว่างเสมอหลังจากกด Enter
                input_key = f"type_box_{target['id']}_{st.session_state.input_focus_trigger}"
                typed_word = st.text_input("Type correctly:", key=input_key, placeholder="Type and hit Enter...").strip()

                if typed_word:
                    if typed_word.lower() == target['word'].lower():
                        st.session_state.session_queue.append(target.to_dict())
                        st.session_state.input_focus_trigger += 1 
                        st.toast(f"✅ Correct: {target['word']}")
                        # ครบ 3 คำตัดเข้าควิซ
                        if len(st.session_state.session_queue) >= 3:
                            st.session_state.quiz_phase = True
                        time.sleep(0.3)
                        st.rerun()
                    else:
                        if len(typed_word) >= len(target['word']):
                            st.error("Typos! Concentrate on each letter.")
            else:
                # ถ้าไม่มีคำค้างในตาราง แต่มีในคิวรอควิซ
                if st.session_state.session_queue:
                    st.session_state.quiz_phase = True
                    st.rerun()
                else:
                    st.success("🎯 All daily tasks completed!")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("🔥 Start Infinite Review"):
                            conn = sqlite3.connect(DB_NAME)
                            c = conn.cursor()
                            c.execute("UPDATE vocab SET next_review = ?", (datetime.now().strftime('%Y-%m-%d'),))
                            conn.commit(); conn.close(); st.rerun()
                    with c2:
                        if st.button("📦 Unlock More Oxford Words (B2-C1)"):
                            conn = sqlite3.connect(DB_NAME)
                            c = conn.cursor()
                            now = datetime.now().strftime('%Y-%m-%d')
                            added_count = 0
                            # กรองคำที่ยังไม่มีใน DB
                            c.execute("SELECT word FROM vocab")
                            existing_words = [row[0] for row in c.fetchall()]
                            
                            for w in OXFORD_EXPANSION:
                                if w[0] not in existing_words:
                                    c.execute("INSERT INTO vocab (word, pos, pronunciation, translation, example, level, next_review) VALUES (?,?,?,?,?,?,?)",
                                              (w[0], w[1], w[2], w[3], w[4], w[5], now))
                                    added_count += 1
                                    if added_count >= 10: break # เพิ่มทีละ 10 คำเพื่อไม่ให้เยอะเกินไป
                            
                            conn.commit()
                            conn.close()
                            if added_count > 0:
                                st.success(f"Unlocked {added_count} new advanced words! Ready for training.")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.info("You've unlocked all current words in the library!")
        
        with tabs[1]:
            # --- ANALYTICS TAB ---
            conn = sqlite3.connect(DB_NAME)
            df_v = pd.read_sql_query("SELECT * FROM vocab", conn)
            conn.close()
            st.subheader("Your Mastery Level")
            if not df_v.empty:
                st.progress(int(df_v['mastery_score'].mean()))
                st.write(f"Average Knowledge: {int(df_v['mastery_score'].mean())}%")
                st.dataframe(df_v[['word', 'level', 'mastery_score', 'next_review']].sort_values('mastery_score', ascending=False), use_container_width=True)

        with tabs[2]:
            # --- WORD VAULT TAB ---
            with st.expander("➕ Add Custom Word"):
                with st.form("add_word", clear_on_submit=True):
                    c1, c2, c3 = st.columns(3)
                    w = c1.text_input("Word"); pos = c2.selectbox("POS", ["n.", "v.", "adj.", "adv.", "phr."]); phonetic = c3.text_input("IPA /.../")
                    t = st.text_input("Thai"); e = st.text_area("Example Sentence"); l = st.select_slider("CEFR", ["A1", "A2", "B1", "B2", "C1", "C2"], value="B2")
                    if st.form_submit_button("Save"):
                        conn = sqlite3.connect(DB_NAME); c = conn.cursor()
                        try:
                            c.execute("INSERT INTO vocab (word, pos, pronunciation, translation, example, level, next_review) VALUES (?,?,?,?,?,?,?)",
                                      (w, pos, phonetic, t, e, l, datetime.now().strftime('%Y-%m-%d')))
                            conn.commit(); st.success(f"Added {w}!"); time.sleep(1); st.rerun()
                        except: st.error("Exists!")
                        conn.close()
            conn = sqlite3.connect(DB_NAME); df_v = pd.read_sql_query("SELECT word, pos, level, translation, mastery_score FROM vocab", conn); conn.close()
            st.dataframe(df_v, use_container_width=True)

if __name__ == "__main__":
    main()
