import streamlit as st
from openai import OpenAI
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

# --- Main App Logic ---
st.title("What's for dinner?")

# Fetch the data
response = run_query()
menu_items = response.data # This returns a list of dictionaries

# --- UI Logic ---



# Format menu for the AI System Prompt
menu_context = "\n".join([f"""- {item['item']}: {item['description']},
                            {'as a hot meal,' if item['hot'] else ''} 
                            takes {item['time_in_min']} minutes to get ready to eat, 
                            {'is homemade not takeout with ' if item['homemade'] else ''}
                            {item['ingredients'] if item['homemade'] else ''} 
                            {'allows us to sit in if not homemade' if item['sit_in'] and ~item['homemade'] else 'is a takeout meal'}""" for item in menu_items])


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

# --- Sidebar Form ---
with st.sidebar:
    st.header("Add Menu Item")
    with st.form("menu_form", clear_on_submit=True):
        name = st.text_input("Item Name")
        desc = st.text_area("Description")
        
        # Adding the 'hot' functionality
        is_hot = st.checkbox("Is this item typically hot? 🔥")

        time = st.text_input("How long in minutes does this dish take?")
        
        homemade = st.checkbox("Are we making this dish at home?")
        sit_in = st.checkbox("Are we typically sitting in if this isn't at home?")

        ing = st.text_area("What ingredients are needed for this dish to be made, including sides?")

        whothis = st.text_input("Who is adding this menu item?")
        if st.form_submit_button("Add to Menu"):
            if name and desc:
                add_to_menu(name, desc, is_hot, time, sit_in, homemade, ing, whothis)
            else:
                st.warning("Please fill out the details!")

# (The rest of your OpenAI chat logic goes here, using 'menu_context' as before)
# st.write("### Current Live Menu")
# st.dataframe(menu_items)

# st.title("🍴 The Bistro Assistant")

# Sidebar
with st.sidebar:
    st.header("Settings")
    # FIX: Ensure you are using model names your API key has access to
    model_choice = st.selectbox("Model", ["gpt-4o-mini", "gpt-3.5-turbo"], index=0)
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
            {"role": "system", "content": f"You are a helpful server. Only talk about this menu:\n{menu_context}"}
        ] + st.session_state.chat_history

        try:
            for response in client.chat.completions.create(
                model=model_choice,
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
