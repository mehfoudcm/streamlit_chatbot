import streamlit as st
from openai import OpenAI

# 1. Menu Data
MENU_ITEMS = {
    "Truffle Fries": "Crispy golden fries with truffle oil and parmesan. $12",
    "Spicy Tuna Roll": "Fresh ahi tuna and avocado. $16",
    "Classic Smash Burger": "Two beef patties and secret sauce. $15",
    "Garden Risotto": "Creamy rice with spring peas and lemon. $19",
    "Matcha Cheesecake": "Green tea cheesecake with sesame crust. $9"
}

menu_context = "\n".join([f"- {name}: {desc}" for name, desc in MENU_ITEMS.items()])

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
