import streamlit as st
from openai import OpenAI
import pandas as pd
from datetime import datetime, timedelta
# from st_supabase_connection import SupabaseConnection
from supabase import create_client, Client

# 1. Initialize the Supabase Client
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# 2. Function to Query Data
# We use st.cache_data to prevent hitting the DB on every user chat toggle
@st.cache_data(ttl=600) # Cache for 10 minutes
def run_query():
    # .select("*") fetches all columns; .execute() returns the response object
    return supabase.table("menu").select("*").execute()

def run_query_eaten(t=3):
    t_weeks_ago = datetime.now() - timedelta(weeks=t)
    date_str = t_weeks_ago.strftime("%Y-%m-%d")
    return supabase.table("eaten").select("*").gte("date_eaten", date_str).execute()



# --- Main App Logic ---
st.title("What's for dinner?")

# Fetch the data for menu
response = run_query()
menu_items = response.data # bringing in the options we have to eat

# fetch data for food eaten
response_eaten = run_query_eaten()
eaten_food = response_eaten.data # bringing in the last few meals 

df_eaten = pd.DataFrame(eaten_food)

if not df_eaten.empty:
    # Convert to datetime objects (Crucial Step)
    df_eaten['date_eaten'] = pd.to_datetime(df_eaten['date_eaten'])
    
    # 3. Apply Date Logic
    # Example: Calculate days since eaten
    today = datetime.now()
    df_eaten['days_ago'] = (today - df_eaten['date_eaten']).dt.days
    
    # 4. Create a Category Column (The "Logic")
    def categorize_freshness(days):
        if days <= 5: return "are fresh"
        return "are bad"

    df_eaten['freshness'] = df_eaten['days_ago'].apply(categorize_freshness)

# st.dataframe(df_eaten)

# Alphabetize by the 'name' key
sorted_menu = sorted(menu_items, key=lambda x: x['item'].lower())

display_df = pd.DataFrame(sorted_menu)[['item', 'homemade']]

# --- UI Logic ---



# Format menu for the AI System Prompt
menu_context = "\n".join([f"""- {item['item']}: {item['description']},
                            {'as a hot meal,' if item['hot'] else ''} 
                            takes {item['time_in_min']} minutes to get ready to eat, 
                            {'is homemade not takeout with ' if item['homemade'] else ''}
                            {item['ingredients'] if item['homemade'] else ''} 
                            {'allows us to sit in if not homemade' if item['sit_in'] and not item['homemade'] else 'is a takeout meal'}""" for item in menu_items])

meal_context = "\n".join([
                            f"- {meal_eaten} was eaten on {date_eaten} "
                            f"{f'and leftovers {freshness}' if leftovers else ''}" 
                            for meal_eaten, date_eaten, leftovers, freshness in zip(
                                df_eaten['meal_eaten'], 
                                df_eaten['date_eaten'], 
                                df_eaten['leftovers'], 
                                df_eaten['freshness']
                            )
                        ])
# st.write(meal_context)

def add_to_menu(name, desc, is_hot, time, sit_in, homemade, ing, whothis):

    new_row = {
        "item": name,
        "description": desc,
        "hot": is_hot,
        "time_in_min": time,
        "sit_in": sit_in,
        "homemade": homemade,
        "ingredients": ing,
        "added_by": whothis
    }
    
    try:
        # Perform the Insert
        result = supabase.table("menu").insert(new_row).execute()
        
        if result.data:
            st.success(f"Successfully added {name}!")
            # Clear cache so the chatbot sees the new menu immediately
            st.cache_data.clear() 
        else:
            st.error("Insert failed. Check your RLS policies.")
    except Exception as e:
        st.error(f"Error connecting to database: {e}")

def add_to_eaten(meal, d, left, who):

    new_row = {
        "meal_eaten": meal,
        "date_eaten": d,
        "leftovers": left,
        "who_ate_it": who
    }
    
    try:
        # Perform the Insert
        result = supabase.table("eaten").insert(new_row).execute()
        
        if result.data:
            st.success(f"Successfully added {name}!")
            # Clear cache so the chatbot sees the new menu immediately
            st.cache_data.clear() 
        else:
            st.error("Insert failed. Check your RLS policies.")
    except Exception as e:
        st.error(f"Error connecting to database: {e}")

# --- Sidebar Form ---
with st.sidebar:
    st.header("Add Menu Item")
    with st.form("menu_form", clear_on_submit=True):
        name = st.text_input("Item Name")
        desc = st.text_area("Description")
        
        # Adding the 'hot' functionality
        is_hot = st.checkbox("Is this item typically hot? 🔥")

        time = st.text_input("How long does this dish take? 🕒 (in minutes)")
        
        homemade = st.checkbox("Are we making this dish at home? 🏠 ")
        sit_in = st.checkbox("Are we typically sitting in if this isn't at home? 🪑")

        ing = st.text_area("What ingredients are needed for this dish to be made, including sides?")

        whothis = st.text_input("Who is adding this menu item?")
        if st.form_submit_button("Add to Menu"):
            if name and desc:
                add_to_menu(name, desc, is_hot, time, sit_in, homemade, ing, whothis)
            else:
                st.warning("Please fill out the details!")

    st.divider()

    # --- Section B: Simple Alphabetical List ---
    st.subheader("Current Menu")
    
    # This creates a scrollable area if the list gets long
    # height=300 keeps it from taking over the whole sidebar
    # use_container_width=True ensures it fits the sidebar width
    st.dataframe(
        display_df, 
        height=300, 
        use_container_width=True,
        hide_index=True, # Saves horizontal space
        column_config={
            "item": "Item"
        }
    )
    
    st.caption("Scroll ↕ to see all items")
        
    # (The rest of your OpenAI chat logic goes here, using 'menu_context' as before)
    st.header("Add Meal Eaten")
    with st.form("meal_form", clear_on_submit=True):
        meal = st.text_input("What did you eat?")
        d = st.text_area("When did you eat it?")
        
        # Adding the 'hot' functionality
        left = st.checkbox("Is there any left?")
        
        who = st.text_input("Who ate it?")
        if st.form_submit_button("Add to Eaten"):
            if name and desc:
                add_to_eaten(meal, d, left, who)
            else:
                st.warning("Please fill out the details!")
    
    st.divider()

# Sidebar
with st.sidebar:
    st.header("Settings")
    # FIX: Ensure you are using model names your API key has access to
    # model_choice = st.selectbox("Model", ["gpt-4o-mini", "gpt-3.5-turbo"], index=0)
    if st.button("Reset Chat"):
        st.session_state.chat_history = [] # Use a different key for clarity
        st.rerun()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 2. Initialize ONLY the conversation history (not the system prompt)
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display history
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 3. Handle Input
if prompt := st.chat_input("What's on the menu?"):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        # FIX: Prepend the System Message HERE, every time.
        # This ensures the model NEVER forgets the menu.
        messages_to_send = [
            {"role": "system", "content": f"""You are a helpful server. Only talk about this menu:\n{menu_context}. 
                                            Do not recommend meals that have been eaten recently based on:\n{meal_context}
                                            Inform user if leftovers are good or bad only if asked."""}
        ] + st.session_state.chat_history

        try:
            for response in client.chat.completions.create(
                model="gpt-4o-mini",
                # model = model_choice
                messages=messages_to_send,
                stream=True,
            ):
                content = response.choices[0].delta.content or ""
                full_response += content
                response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            st.session_state.chat_history.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"OpenAI Error: {e}")
