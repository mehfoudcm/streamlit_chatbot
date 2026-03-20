import streamlit as st
from openai import OpenAI

st.title("AI Assistant")

# 1. Initialize the client using Streamlit Secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 2. Set the model to use
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-4o"

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display existing chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 3. The Logic Replacement
if prompt := st.chat_input("How can I help with your data?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Create a placeholder for the streaming response
        response_placeholder = st.empty()
        full_response = ""
        
        # Call the OpenAI API
        for response in client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        ):
            full_response += (response.choices[0].delta.content or "")
            response_placeholder.markdown(full_response + "▌")
        
        response_placeholder.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})
