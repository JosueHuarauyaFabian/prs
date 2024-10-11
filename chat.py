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

# Función para obtener el menú como texto
def get_menu_text():
    menu_text = "Nuestro Menú Completo:\n\n"
    for category, items in menu_df.groupby('Category'):
        menu_text += f"{category}:\n"
        for _, item in items.iterrows():
            menu_text += f"- {item['Item']} - {item['Serving Size']} - ${item['Price']:.2f}\n"
        menu_text += "\n"
    return menu_text

# Función para filtrar contenido inapropiado
def is_inappropriate(text):
    inappropriate_words = ['tonto', 'tonta']
    return any(word in text.lower() for word in inappropriate_words)

# Función para calcular el total del pedido
def calculate_total():
    return sum(menu_df.loc[menu_df['Item'].str.lower() == item.lower(), 'Price'].iloc[0] * quantity 
               for item, quantity in st.session_state.current_order.items())

# Función para manejar pedidos
def handle_order(query):
    items = re.findall(r'(\d+)\s*([\w\s]+)', query)
    if not items:
        items = [(1, query.strip())]  # Asume cantidad 1 si no se especifica
    
    response = ""
    for quantity, item in items:
        item = item.strip()
        if item.lower() in [i.lower() for i in menu_df['Item']]:
            quantity = int(quantity) if isinstance(quantity, str) else quantity
            st.session_state.current_order[item] = st.session_state.current_order.get(item, 0) + quantity
            price = menu_df.loc[menu_df['Item'].str.lower() == item.lower(), 'Price'].iloc[0]
            response += f"Añadido {quantity} {item}(s) a tu pedido. Precio unitario: ${price:.2f}\n"
        else:
            response += f"Lo siento, no encontré '{item}' en nuestro menú.\n"
    
    total = calculate_total()
    response += f"\nTotal actual del pedido: ${total:.2f}"
    return response

# Función para obtener el precio de un item
def get_item_price(item):
    price = menu_df.loc[menu_df['Item'].str.lower() == item.lower(), 'Price']
    if not price.empty:
        return f"El precio de {item} es ${price.iloc[0]:.2f}"
    else:
        return f"Lo siento, no encontré el precio de {item}."

# Función para cancelar el pedido
def cancel_order():
    st.session_state.current_order = {}
    st.session_state.order_state = OrderState.INITIAL
    return "Tu pedido ha sido cancelado. ¿Puedo ayudarte con algo más?"

# Función para guardar el pedido
def save_order(order):
    with open('orders.json', 'a') as f:
        json.dump(order, f)
        f.write('\n')

# Función para generar respuesta con GPT
def generate_gpt_response(prompt, context):
    try:
        messages = [
            {"role": "system", "content": f"Eres un asistente de restaurante amable y servicial. Aquí está el menú actual: {get_menu_text()}"},
            {"role": "system", "content": f"Contexto actual: {context}"},
            {"role": "user", "content": prompt}
        ]
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=150,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error generating response with OpenAI: {e}")
        return "Lo siento, hubo un problema al procesar tu solicitud. ¿Podrías intentarlo de nuevo?"

# Función principal de manejo de consultas
def handle_query(query):
    if is_inappropriate(query):
        return "Por favor, mantén un lenguaje respetuoso."

    context = f"Estado actual del pedido: {st.session_state.order_state.name}. Pedido actual: {st.session_state.current_order}"
    
    if "menú" in query.lower() or "menu" in query.lower():
        return get_menu_text()
    elif "precio de" in query.lower():
        item = query.lower().split("precio de")[-1].strip()
        return get_item_price(item)
    elif "cancelar pedido" in query.lower():
        return cancel_order()
    elif "descuento" in query.lower():
        return "Lo siento, no ofrecemos descuentos en este momento."
    elif st.session_state.order_state == OrderState.SELECTING_ITEMS or any(item.lower() in query.lower() for item in menu_df['Item']):
        st.session_state.order_state = OrderState.SELECTING_ITEMS
        return handle_order(query)
    elif "confirmar pedido" in query.lower():
        if st.session_state.current_order:
            st.session_state.order_state = OrderState.CONFIRMING_ORDER
            order = {
                'items': st.session_state.current_order,
                'total': calculate_total()
            }
            save_order(order)
            confirmed_order = st.session_state.current_order.copy()
            st.session_state.current_order = {}
            st.session_state.order_state = OrderState.INITIAL
            return f"¡Gracias! Tu pedido ha sido confirmado y guardado. Detalles del pedido: {confirmed_order}"
        else:
            return "No hay ningún pedido para confirmar. ¿Quieres hacer un pedido?"
    
    # Para cualquier otra consulta, usamos GPT
    return generate_gpt_response(query, context)

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
    st.sidebar.markdown("### Pedido Actual:")
    for item, quantity in st.session_state.current_order.items():
        st.sidebar.write(f"{item}: {quantity}")
    total = calculate_total()
    st.sidebar.markdown(f"**Total: ${total:.2f}**")
