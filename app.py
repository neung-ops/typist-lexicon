import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import time
import plotly.express as px

DB_NAME = "vocab_vault_v3.db"

# --- DATABASE LOGIC ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # ตารางหลักสำหรับเก็บคำศัพท์และสถิติการเรียนรู้
    c.execute('''CREATE TABLE IF NOT EXISTS vocab 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  word TEXT UNIQUE, 
                  pos TEXT,
                  translation TEXT, 
                  example TEXT,
                  level TEXT, 
                  interval INTEGER DEFAULT 0, 
                  easiness REAL DEFAULT 2.5, 
                  next_review TEXT,
                  mastery_score INTEGER DEFAULT 0)''')
    
    # ตรวจสอบการเพิ่มคอลัมน์ใหม่ (Migration)
    c.execute("PRAGMA table_info(vocab)")
    cols = [column[1] for column in c.fetchall()]
    if 'pos' not in cols: c.execute("ALTER TABLE vocab ADD COLUMN pos TEXT")
    if 'example' not in cols: c.execute("ALTER TABLE vocab ADD COLUMN example TEXT")

    # ใส่ข้อมูลเริ่มต้นถ้าฐานข้อมูลว่างเปล่า
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
    // ดักจับและสั่งปิด autocomplete ทุกๆ 1 วินาที เพื่อให้ครอบคลุมการ render ใหม่ของ Streamlit
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
        conn = sqlite3.connect(DB_NAME)
        today = datetime.now().strftime('%Y-%m-%d')
        # ดึงคำที่ถึงกำหนดทบทวน หรือคำใหม่
        df_due = pd.read_sql_query("SELECT * FROM vocab WHERE next_review <= ? OR interval = 0 ORDER BY interval DESC", conn, params=(today,))
        conn.close()

        if not df_due.empty:
            target = df_due.iloc[0]
            st.markdown(f"""
                <div class="vocab-card">
                    <div class="level-tag">CEFR LEVEL: {target['level']}</div>
                    <div class="pos-tag">{target['pos']}</div>
                    <h1 class="word-main">{target['word']}</h1>
                    <div class="trans-main">{target['translation']}</div>
                    <div class="example-box">“{target['example']}”</div>
                </div>
            """, unsafe_allow_html=True)
            
            # ใช้ dynamic key ร่วมกับ timestamp เพื่อกันบราว์เซอร์จำฟิลด์เดิม
            input_key = f"q_{target['id']}_{time.time()}"
            user_input = st.text_input("Type the word correctly to continue", key=input_key, placeholder="...")

            if user_input:
                if user_input.strip().lower() == target['word'].lower():
                    update_srs(target['id'], True)
                    st.toast(f"🎯 Perfect! Mastery: {target['word']}", icon="✅")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    if len(user_input) >= len(target['word']):
                        st.error("Keep trying! Focus on each letter.")
                        update_srs(target['id'], False)
        else:
            st.balloons()
            st.markdown("<div style='text-align:center; padding:50px;'><h1>🌈 All Done!</h1><p>You've cleared your list for today.</p></div>", unsafe_allow_html=True)

    with tabs[1]:
        st.header("Learning Analytics")
        conn = sqlite3.connect(DB_NAME)
        df_stats = pd.read_sql_query("SELECT * FROM vocab", conn)
        conn.close()
        
        if not df_stats.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Vocabulary", len(df_stats))
            m2.metric("Avg. Mastery", f"{int(df_stats['mastery_score'].mean())}%")
            m3.metric("Due for Review", len(df_due))
            
            fig = px.bar(df_stats, x="word", y="mastery_score", color="mastery_score", 
                         title="Mastery Level by Word", color_continuous_scale="Viridis")
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Start practicing to see your statistics!")

    with tabs[2]:
        st.header("Vault Management")
        with st.expander("➕ Add New Word"):
            with st.form("new_word_form", clear_on_submit=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                word = col1.text_input("English Word")
                pos = col2.selectbox("Type", ["n.", "v.", "adj.", "adv.", "phr."])
                level = col3.selectbox("Level", ["A1", "A2", "B1", "B2", "C1", "C2"])
                trans = st.text_input("Thai Translation")
                ex = st.text_area("Usage Example Sentence")
                if st.form_submit_button("Add to My Collection"):
                    if word and trans:
                        try:
                            conn = sqlite3.connect(DB_NAME)
                            c = conn.cursor()
                            c.execute("INSERT INTO vocab (word, pos, translation, example, level, next_review) VALUES (?,?,?,?,?,?)",
                                      (word, pos, trans, ex, level, datetime.now().strftime('%Y-%m-%d')))
                            conn.commit()
                            conn.close()
                            st.success(f"Added '{word}'!")
                            st.rerun()
                        except: st.error("This word already exists.")
        
        conn = sqlite3.connect(DB_NAME)
        df_vault = pd.read_sql_query("SELECT word, pos, translation, level, mastery_score, next_review FROM vocab", conn)
        conn.close()
        st.dataframe(df_vault, use_container_width=True)

if __name__ == "__main__":
    main()
