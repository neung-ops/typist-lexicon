import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import random
import plotly.express as px
import time

# --- 1. DATABASE SETUP & MIGRATION ---
def init_db():
    conn = sqlite3.connect('vocab_vault.db')
    c = conn.cursor()
    
    # Create table with new structure
    c.execute('''CREATE TABLE IF NOT EXISTS vocabulary
                 (id INTEGER PRIMARY KEY, 
                  word TEXT UNIQUE, 
                  translation TEXT, 
                  level TEXT,
                  pos TEXT,
                  example TEXT,
                  interval INTEGER DEFAULT 0, 
                  easiness REAL DEFAULT 2.5,
                  next_review DATE,
                  status TEXT DEFAULT 'New')''')
    
    # Migration: Check if pos and example columns exist, if not add them
    c.execute("PRAGMA table_info(vocabulary)")
    columns = [column[1] for column in c.fetchall()]
    if 'pos' not in columns:
        c.execute("ALTER TABLE vocabulary ADD COLUMN pos TEXT")
    if 'example' not in columns:
        c.execute("ALTER TABLE vocabulary ADD COLUMN example TEXT")
        
    c.execute('''CREATE TABLE IF NOT EXISTS activity_log
                 (id INTEGER PRIMARY KEY, 
                  word_id INTEGER, 
                  timestamp DATETIME, 
                  is_correct INTEGER)''')
    
    # Pre-seed with more descriptive data
    c.execute("SELECT count(*) FROM vocabulary")
    if c.fetchone()[0] == 0:
        initial_words = [
            ("Analyze", "วิเคราะห์", "B1", "v.", "We need to analyze the data before making a decision."),
            ("Comprehensive", "ครอบคลุม", "C1", "adj.", "The training provided a comprehensive overview of the system."),
            ("Implement", "นำไปปฏิบัติ", "B2", "v.", "The company decided to implement a new policy."),
            ("Efficient", "ที่มีประสิทธิภาพ", "B1", "adj.", "The new process is much more efficient than the old one."),
            ("Perspective", "มุมมอง", "B2", "n.", "Traveling gives you a different perspective on life."),
            ("Consistent", "สม่ำเสมอ", "B2", "adj.", "Success comes from consistent effort over time.")
        ]
        for w, t, l, p, e in initial_words:
            c.execute("INSERT INTO vocabulary (word, translation, level, pos, example, next_review) VALUES (?, ?, ?, ?, ?, ?)",
                      (w, t, l, p, e, datetime.now().date()))
    conn.commit()
    return conn

# --- 2. SRS LOGIC ---
def update_srs(word_id, is_correct):
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
        if interval == 0: new_interval = 1
        elif interval == 1: new_interval = 3
        else: new_interval = int(interval * easiness)
        new_easiness = easiness + 0.1
        status = 'Mastering' if new_interval > 14 else 'Learning'
    else:
        new_interval = 0
        new_easiness = max(1.3, easiness - 0.2)
        status = 'Relearning'

    next_review = datetime.now().date() + timedelta(days=new_interval)
    c.execute("UPDATE vocabulary SET interval=?, easiness=?, next_review=?, status=? WHERE id=?",
              (new_interval, new_easiness, next_review, status, word_id))
    conn.commit()
    conn.close()

# --- 3. UI STYLING ---
st.set_page_config(page_title="Typist Lexicon Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #E0E0E0; }
    .stTextInput > div > div > input {
        font-size: 28px; text-align: center; border-radius: 15px;
        border: 2px solid #4F46E5; background-color: #1F2937; color: white;
        padding: 10px;
    }
    .vocab-card {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        padding: 40px; border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center; margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }
    .pos-tag {
        display: inline-block; background: #4F46E5; color: white;
        padding: 2px 12px; border-radius: 20px; font-size: 0.9rem;
        margin-left: 10px; vertical-align: middle;
    }
    .thai-translation { color: #A855F7; font-size: 1.8rem; font-weight: bold; margin-top: 10px; }
    .example-box {
        margin-top: 25px; padding-top: 20px;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        font-style: italic; color: #94A3B8; font-size: 1.2rem;
    }
    .example-box b { color: #E2E8F0; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. MAIN APP LOGIC ---
def main():
    conn = init_db()
    st.title("⌨️ Typist Lexicon Pro")
    st.markdown("Mastering Vocabulary in Context")

    tab1, tab2, tab3 = st.tabs(["🚀 Practice Session", "📊 Progress Tracker", "📚 Knowledge Vault"])

    with tab1:
        today = datetime.now().date()
        df_due = pd.read_sql_query(f"SELECT * FROM vocabulary WHERE next_review <= '{today}'", conn)
        
        if not df_due.empty:
            # Shuffle slightly so we don't always get the same order in one session
            target_word_row = df_due.iloc[0]
            target_word = target_word_row['word']
            
            st.markdown(f"""
                <div class="vocab-card">
                    <p style='color: #94A3B8; margin:0;'>Level: {target_word_row['level']}</p>
                    <h1 style='font-size: 4.5rem; margin: 10px 0;'>
                        {target_word} <span class="pos-tag">{target_word_row['pos'] or ''}</span>
                    </h1>
                    <p class="thai-translation">{target_word_row['translation']}</p>
                    <div class="example-box">
                        " {target_word_row['example'] or 'No example provided.'} "
                    </div>
                </div>
            """, unsafe_allow_html=True)

            input_container = st.empty()
            input_key = f"typing_input_{target_word_row['id']}"
            user_input = input_container.text_input("Type the word correctly to master it", key=input_key)

            if user_input:
                if user_input.strip().lower() == target_word.lower():
                    update_srs(target_word_row['id'], True)
                    
                    # Log activity
                    c = conn.cursor()
                    c.execute("INSERT INTO activity_log (word_id, timestamp, is_correct) VALUES (?, ?, ?)",
                              (int(target_word_row['id']), datetime.now(), 1))
                    conn.commit()
                    
                    st.toast(f"🎯 Perfect: {target_word}!")
                    time.sleep(0.6)
                    st.rerun() 
                else:
                    if len(user_input) >= len(target_word):
                        st.error("❌ Almost there! Check your spelling.")
                        update_srs(target_word_row['id'], False)
        else:
            st.info("🌈 Your brain is full for today! All words are reviewed. Add more in the Vault.")

    with tab2:
        st.header("Your Learning Analytics")
        df_stats = pd.read_sql_query("SELECT status, count(*) as count FROM vocabulary GROUP BY status", conn)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            if not df_stats.empty:
                fig = px.pie(df_stats, values='count', names='status', 
                            title='Knowledge Mastery Level',
                            color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write("No data yet.")
            
        with col2:
            total_words = pd.read_sql_query("SELECT count(*) as total FROM vocabulary", conn).iloc[0]['total']
            st.metric("Total Words Mastered", total_words)
            st.write("Keep the streak alive to move words from 'New' to 'Mastering'!")

    with tab3:
        st.header("Vocabulary Management")
        with st.expander("➕ Add New English Word"):
            c1, c2, c3 = st.columns([3, 2, 1])
            new_word = c1.text_input("Word (English)")
            new_pos = c2.selectbox("Type", ["n.", "v.", "adj.", "adv.", "phr."])
            new_level = c3.selectbox("Level", ["A1", "A2", "B1", "B2", "C1", "C2"])
            
            new_trans = st.text_input("Thai Translation")
            new_ex = st.text_area("Example Sentence", placeholder="How is this word used in a sentence?")
            
            if st.button("Save to My Vault"):
                if new_word and new_trans:
                    try:
                        c = conn.cursor()
                        c.execute("""INSERT INTO vocabulary 
                                   (word, translation, level, pos, example, next_review) 
                                   VALUES (?, ?, ?, ?, ?, ?)""",
                                  (new_word, new_trans, new_level, new_pos, new_ex, datetime.now().date()))
                        conn.commit()
                        st.success(f"Successfully added '{new_word}'")
                        st.rerun()
                    except:
                        st.warning("This word already exists in your vault.")
        
        df_vault = pd.read_sql_query("SELECT word, pos, translation, level, status, next_review FROM vocabulary", conn)
        st.dataframe(df_vault, use_container_width=True)

if __name__ == "__main__":
    main()
```
eof

### มีอะไรใหม่ในเวอร์ชันนี้?
1.  **Part of Speech (POS):** เวลาพิมพ์คุณจะเห็นเลยว่าคำนี้ทำหน้าที่อะไร (n., v., adj.) ช่วยให้คุณไม่สับสนเวลาเอาไปใช้จริง
2.  **Example Sentences:** เพิ่มกล่อง "Example Box" ด้านล่างของคำศัพท์ เพื่อให้คุณได้อ่านประโยคไปพร้อมๆ กับตอนฝึกพิมพ์
3.  **Better Layout:** ขยายขนาดตัวอักษรของคำศัพท์หลักให้ใหญ่ขึ้น (4.5rem) เพื่อให้โฟกัสที่ตัวสะกดได้ชัดเจน
4.  **Database Auto-update:** คุณไม่ต้องลบไฟล์ `.db` เดิมทิ้งครับ ผมเขียนโค้ด `Migration` ไว้ให้แล้ว มันจะเพิ่มคอลัมน์ `pos` และ `example` ให้เองโดยอัตโนมัติ

**คำแนะนำ:** เวลาคุณเพิ่มคำศัพท์เองในหน้า "Knowledge Vault" พยายามหาประโยคตัวอย่างที่คุณ "อิน" หรือต้องใช้บ่อยๆ ในงานมาใส่ครับ Muscle Memory จะทำงานได้ดีขึ้น 2 เท่าถ้ามีความหมายที่เชื่อมโยงกับชีวิตจริงครับ! ลองใช้งานดูนะครับ!
