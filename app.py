import streamlit as st
from openai import OpenAI

# 1. Define your Menu Dictionary
# In a real-world scenario, you might load this from a JSON or SQL database.
MENU_ITEMS = {
    "Truffle Fries": "Crispy golden fries tossed in white truffle oil and topped with shaved parmesan and fresh parsley. $12",
    "Spicy Tuna Roll": "Fresh ahi tuna, cucumber, and avocado topped with spicy mayo and toasted sesame seeds. $16",
    "Classic Smash Burger": "Two grass-fed beef patties, American cheese, caramelized onions, and secret sauce on a brioche bun. $15",
    "Garden Risotto": "Creamy Arborio rice with spring peas, asparagus, and a hint of lemon zest. $19 (Vegetarian)",
    "Matcha Cheesecake": "Velvety green tea cheesecake with a black sesame crust. $9"
}

# Format the menu as a string for the System Prompt
menu_context = "\n".join([f"- {name}: {desc}" for name, desc in MENU_ITEMS.items()])

st.title("🍴 The Bistro Assistant")

# Sidebar for model settings
with st.sidebar:
    st.header("Settings")
    model_choice = st.selectbox("Model", ["gpt-5.4-nano", "gpt-4o-mini"], index=0)
    if st.button("Reset Chat"):
        st.session_state.messages = []
        st.rerun()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

if "messages" not in st.session_state:
    # 2. Inject the System Prompt
    # This tells the bot exactly how to behave and what data to use.
    st.session_state.messages = [
        {"role": "system", "content": f"""
        You are a helpful and charismatic restaurant server. 
        Your goal is to answer questions ONLY about the following menu:
        {menu_context}
        
        If a customer asks about an item not on this list, politely let them know 
        it isn't available today and suggest a similar item from the menu.
        """}
    ]

# Display chat history (skipping the system prompt)
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# User Interaction
if prompt := st.chat_input("What's on the menu?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        # Calling the API with the menu context included in history
        for response in client.chat.completions.create(
            model=model_choice,
            messages=st.session_state.messages,
            stream=True,
        ):
            full_response += (response.choices[0].delta.content or "")
            response_placeholder.markdown(full_response + "▌")
        
        response_placeholder.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})
