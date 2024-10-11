import streamlit as st
import pandas as pd
import re
from openai import OpenAI
import json
import logging
from enum import Enum

# Configuración de logging
logging.basicConfig(level=logging.DEBUG)

# Configuración de la página
st.set_page_config(page_title="Chatbot de Restaurante", page_icon="🍽️")

# Inicialización del cliente OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Definir estados del pedido
class OrderState(Enum):
    INITIAL = 0
    SELECTING_ITEMS = 1
    CONFIRMING_ORDER = 2

# Cargar datos
@st.cache_data
def load_data():
    try:
        menu_df = pd.read_csv('menu.csv')
        return menu_df
    except Exception as e:
        logging.error(f"Error al cargar los datos: {e}")
        return pd.DataFrame()

menu_df = load_data()

# Función de filtrado de contenido
def is_inappropriate(text):
    inappropriate_words = ['tonto', 'tonta', 'estúpido', 'estúpida', 'idiota']
    return any(word in text.lower() for word in inappropriate_words)

# Funciones de manejo del menú
def get_menu():
    menu_text = "🍽️ Nuestro Menú:\n\n"
    for category, items in menu_df.groupby('Category'):
        menu_text += f"**{category}**\n"
        for _, item in items.iterrows():
            menu_text += f"• {item['Item']} - {item['Serving Size']} - ${item['Price']:.2f}\n"
        menu_text += "\n"
    return menu_text

# Funciones de manejo de pedidos
def add_to_order(item, quantity):
    if item.lower() in [i.lower() for i in menu_df['Item']]:
        st.session_state.current_order[item] = st.session_state.current_order.get(item, 0) + quantity
        total = calculate_total()
        return f"Se ha añadido {quantity} {item}(s) a tu pedido. El total actual es ${total:.2f}"
    return f"Lo siento, {item} no está en nuestro menú. Por favor, verifica el menú e intenta de nuevo."

def calculate_total():
    return sum(menu_df.loc[menu_df['Item'].str.lower() == item.lower(), 'Price'].iloc[0] * quantity 
               for item, quantity in st.session_state.current_order.items())

def confirm_order():
    if not st.session_state.current_order:
        return "No hay ningún pedido para confirmar. ¿Quieres empezar uno nuevo?"
    
    order_details = {
        'items': st.session_state.current_order,
        'total': calculate_total()
    }
    
    # Guardar el pedido localmente
    with open('orders.json', 'a') as f:
        json.dump(order_details, f)
        f.write('\n')
    
    st.session_state.current_order = {}
    st.session_state.order_state = OrderState.INITIAL
    return f"¡Gracias por tu pedido! Ha sido confirmado y guardado. El total es ${order_details['total']:.2f}"

# Función de manejo de consultas
def handle_query(query):
    if is_inappropriate(query):
        return "Por favor, mantén un lenguaje respetuoso."

    query_lower = query.lower()
    
    if st.session_state.order_state == OrderState.INITIAL:
        if "menú" in query_lower or "carta" in query_lower:
            return get_menu()
        elif "pedir" in query_lower or "ordenar" in query_lower:
            st.session_state.order_state = OrderState.SELECTING_ITEMS
            return "¡Genial! ¿Qué te gustaría ordenar? Puedes decirme los platos y las cantidades."

    elif st.session_state.order_state == OrderState.SELECTING_ITEMS:
        items = extract_order_items(query)
        if items:
            response = ""
            for item, quantity in items:
                response += add_to_order(item, quantity) + "\n"
            return response + "¿Quieres algo más o estás listo para confirmar tu pedido?"
        elif "listo" in query_lower or "confirmar" in query_lower:
            st.session_state.order_state = OrderState.CONFIRMING_ORDER
            return f"Tu pedido actual es:\n{show_current_order()}\n¿Quieres confirmar este pedido?"

    elif st.session_state.order_state == OrderState.CONFIRMING_ORDER:
        if "sí" in query_lower or "confirmar" in query_lower:
            return confirm_order()
        elif "no" in query_lower or "cancelar" in query_lower:
            st.session_state.order_state = OrderState.INITIAL
            st.session_state.current_order = {}
            return "Tu pedido ha sido cancelado. ¿Puedo ayudarte con algo más?"

    # Si no se reconoce la consulta, usar OpenAI
    return generate_ai_response(query)

# Funciones auxiliares
def extract_order_items(query):
    items = re.findall(r'(\d+)\s*([\w\s]+)', query)
    return [(item.strip(), int(quantity)) for quantity, item in items]

def show_current_order():
    if not st.session_state.current_order:
        return "No tienes ningún pedido en curso."
    order_summary = "Tu pedido actual:\n"
    for item, quantity in st.session_state.current_order.items():
        price = menu_df.loc[menu_df['Item'].str.lower() == item.lower(), 'Price'].iloc[0]
        item_total = price * quantity
        order_summary += f"• {quantity} x {item} - ${item_total:.2f}\n"
    order_summary += f"\nTotal: ${calculate_total():.2f}"
    return order_summary

def generate_ai_response(query):
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente de restaurante amable y servicial."},
                {"role": "user", "content": query}
            ],
            max_tokens=150,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error generating response with OpenAI: {e}")
        return "Lo siento, no pude entender tu consulta. ¿Podrías reformularla?"

# Inicialización del estado de la sesión
if 'order_state' not in st.session_state:
    st.session_state.order_state = OrderState.INITIAL
if 'current_order' not in st.session_state:
    st.session_state.current_order = {}

# Interfaz de usuario de Streamlit
st.title("🍽️ Chatbot de Restaurante")

# Mostrar mensajes existentes
for message in st.session_state.get('messages', []):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Campo de entrada para el usuario
if prompt := st.chat_input("¿En qué puedo ayudarte hoy?"):
    st.session_state.messages = st.session_state.get('messages', []) + [{"role": "user", "content": prompt}]
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generar respuesta del chatbot
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = handle_query(prompt)
        message_placeholder.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# Mostrar el estado actual del pedido en la barra lateral
st.sidebar.markdown("## Estado del Pedido")
st.sidebar.write(f"Estado: {st.session_state.order_state.name}")
if st.session_state.current_order:
    st.sidebar.markdown(show_current_order())
