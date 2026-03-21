import streamlit as st
from openai import OpenAI
# from st_supabase_connection import SupabaseConnection
from supabase import create_client, Client

# 1. Initialize the Supabase Client
# @st.cache_resource
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
st.title("🍴 Live Menu Chatbot")

# Fetch the data
response = run_query()
menu_items = response.data # This returns a list of dictionaries
# # 1. Initialize Connection
# conn = st.connection("supabase", type=SupabaseConnection)

# # 2. Function to Fetch Menu
# def get_menu():
#     # Query the 'menu' table we created in Step 1
#     rows = conn.table("menu").select("*").execute()
#     st.write(rows)
#     return rows.data

# 3. Function to Add Menu Item
# def add_menu_item(name, desc, price):
#     conn.table("menu").insert({"name": name, "description": desc, "price": price}).execute()
#     st.cache_data.clear() # Clear cache so the UI updates

# --- UI Logic ---
st.title("🍴 Supabase-Powered Bistro")

#menu_data = get_menu()
st.write(menu_items)

# Format menu for the AI System Prompt
menu_context = "\n".join([f"- {item['item']}: {item['description']} ${item['hot']}" for item in menu_data])

# Sidebar Management
# with st.sidebar:
#     st.header("Add New Item")
#     with st.form("menu_form"):
#         name = st.text_input("Item Name")
#         desc = st.text_area("Description")
#         price = st.number_input("Price", min_value=0.0)
#         if st.form_submit_button("Add to Database"):
#             add_menu_item(name, desc, price)
#             st.success("Added!")
#             st.rerun()

# (The rest of your OpenAI chat logic goes here, using 'menu_context' as before)
st.write("### Current Live Menu")
st.dataframe(menu_data)

st.title("🍴 The Bistro Assistant")

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
